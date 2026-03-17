"""KBO 기록실 상황별 스플릿 크롤러

다음 스플릿 지표를 KBO 기록실에서 크롤링하여 DB에 저장:
  - batter_season.ops_risp   : 득점권(2·3루) OPS
  - pitcher_season.avg_vs_lhb: vs 좌타자 피안타율(AVG against)
  - pitcher_season.avg_vs_rhb: vs 우타자 피안타율(AVG against)

크롤링 대상:
  - 타자 득점권 : /Record/Player/HitterBasic/Basic2.aspx
    (ddlSituation=43, ddlSituationDetail="2,3,12,13,23,123")
  - 투수 타자유형: /Record/Player/PitcherBasic/Basic1.aspx
    (ddlSituation=42, ddlSituationDetail="L"/"R")

사용:
    python -m src.data.collectors.kbo_situation_scraper --season 2025
    python -m src.data.collectors.kbo_situation_scraper --season 2025 --skip-risp
    python -m src.data.collectors.kbo_situation_scraper --season 2025 --skip-era
"""

import argparse
import logging
import sqlite3
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"

HITTER_URL = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic2.aspx"
PITCHER_URL = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"

# Selenium element IDs
SEASON_ID = "cphContents_cphContents_cphContents_ddlSeason_ddlSeason"
SERIES_ID = "cphContents_cphContents_cphContents_ddlSeries_ddlSeries"
SITUATION_ID = "cphContents_cphContents_cphContents_ddlSituation_ddlSituation"
SITUATION_DETAIL_ID = "cphContents_cphContents_cphContents_ddlSituationDetail_ddlSituationDetail"

# 정규시즌 value (ddlSeries 선택 시 ddlSituation AJAX 로드됨)
SERIES_REGULAR = "0"

# 득점권 = 2루 또는 3루에 주자 있는 모든 경우
RISP_VALUE = "2,3,12,13,23,123"

PAGE_DELAY = 1.5
MAX_PAGES = 20

TEAM_SHORT_TO_DB_PREFIX: dict[str, str] = {
    "KIA": "KIA", "삼성": "삼성", "LG": "LG", "두산": "두산", "KT": "KT",
    "SSG": "SSG", "롯데": "롯데", "한화": "한화", "NC": "NC", "키움": "키움",
}


# ─── DB 유틸 ─────────────────────────────────────────────

def build_team_name_to_id(db_path: str) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, name FROM teams").fetchall()
    conn.close()
    mapping: dict[str, int] = {}
    for team_id, full_name in rows:
        for short, prefix in TEAM_SHORT_TO_DB_PREFIX.items():
            if full_name.startswith(prefix):
                mapping[short] = team_id
                break
    return mapping


def _match_player(
    conn: sqlite3.Connection,
    name: str,
    team_short: str,
    team_map: dict[str, int],
) -> int | None:
    """선수명 + 팀으로 player_id 조회.

    1) 이름 + 팀 정확 매칭
    2) 팀 무관 이름 매칭 (동명이인 없는 경우만)
    """
    team_id = team_map.get(team_short)
    if team_id:
        rows = conn.execute(
            "SELECT id FROM players WHERE name = ? AND team_id = ?",
            (name, team_id),
        ).fetchall()
        if rows:
            return rows[0][0]

    # 팀 무관 — 유일한 경우만 허용
    rows = conn.execute(
        "SELECT id FROM players WHERE name = ?", (name,)
    ).fetchall()
    if len(rows) == 1:
        return rows[0][0]

    return None


# ─── Selenium 드라이버 + 공통 조작 ──────────────────────

def make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


def _select_and_wait(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    element_id: str,
    value: str | None = None,
    visible_text: str | None = None,
) -> None:
    """select 요소 선택 후 AJAX 완료 대기."""
    el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    sel = Select(el)
    if visible_text is not None:
        sel.select_by_visible_text(visible_text)
    elif value is not None:
        sel.select_by_value(value)
    time.sleep(PAGE_DELAY)


def _scrape_all_pages(driver: webdriver.Chrome) -> list[dict]:
    """현재 필터 상태에서 전체 페이지의 tData01 테이블을 스크래핑.

    Returns:
        [{"name": str, "team_short": str, "cols": list[str]}]
    """
    records: list[dict] = []
    page = 1

    while page <= MAX_PAGES:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tbl = soup.find("table", class_="tData01")
        if not tbl:
            logger.warning("페이지 %d: 테이블 없음", page)
            break

        rows_found = 0
        for row in tbl.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 4:
                continue
            name = cells[1].strip()
            team = cells[2].strip()
            if not name or name in ("합계", "TOTALS", "계"):
                continue
            records.append({"name": name, "team_short": team, "cols": cells})
            rows_found += 1

        logger.info("  페이지 %d: %d명", page, rows_found)

        try:
            next_btn = driver.find_element(By.LINK_TEXT, str(page + 1))
            next_btn.click()
            time.sleep(PAGE_DELAY)
            page += 1
        except NoSuchElementException:
            logger.info("  마지막 페이지 도달")
            break

    return records


# ─── 크롤링 함수 ─────────────────────────────────────────

def scrape_risp_ops(season: int) -> list[dict]:
    """타자 득점권 OPS 크롤링.

    득점권 상황 필터 시 Basic2 테이블 컬럼:
      [0]순위 [1]선수명 [2]팀명 [3]AVG [4]AB [5]H [6]2B
      [7]3B  [8]HR    [9]RBI [10]BB [11]HBP [12]SO [13]GDP

    OPS = OBP + SLG 를 직접 계산:
      TB  = H + 2B + 2*3B + 3*HR
      SLG = TB / AB
      OBP = (H + BB + HBP) / (AB + BB + HBP)   ← SF 무시

    Returns:
        [{"name": str, "team_short": str, "ops": float}]
    """
    driver = make_driver()
    wait = WebDriverWait(driver, 15)
    results: list[dict] = []

    try:
        logger.info("타자 득점권 OPS 크롤링 시작")
        driver.get(HITTER_URL)
        time.sleep(PAGE_DELAY)

        # 1) 정규시즌 선택 → AJAX로 ddlSituation 로드됨
        _select_and_wait(driver, wait, SERIES_ID, value=SERIES_REGULAR)
        # 2) 시즌 선택 (ddlSituation 리셋될 수 있으므로 ddlSeries 뒤에 수행)
        _select_and_wait(driver, wait, SEASON_ID, value=str(season))
        # 3) ddlSituation이 다시 사라질 수 있으므로 재확인 후 선택
        _select_and_wait(driver, wait, SITUATION_ID, value="43")       # 주자상황별
        _select_and_wait(driver, wait, SITUATION_DETAIL_ID, value=RISP_VALUE)  # 득점권

        raw = _scrape_all_pages(driver)
        for r in raw:
            cols = r["cols"]
            if len(cols) < 13:
                continue
            try:
                ab  = int(cols[4])
                h   = int(cols[5])
                d   = int(cols[6])   # 2B
                t   = int(cols[7])   # 3B
                hr  = int(cols[8])
                bb  = int(cols[10])
                hbp = int(cols[11])
            except (ValueError, IndexError):
                continue

            if ab == 0:
                continue  # 타석 없으면 스킵

            tb  = h + d + 2 * t + 3 * hr
            slg = tb / ab
            denom = ab + bb + hbp
            obp = (h + bb + hbp) / denom if denom > 0 else 0.0
            ops = round(obp + slg, 4)

            results.append({
                "name": r["name"],
                "team_short": r["team_short"],
                "ops": ops,
            })

    finally:
        driver.quit()

    logger.info("득점권 OPS 수집 완료: %d명", len(results))
    return results


def scrape_avg_vs_hand(season: int, hand_value: str) -> list[dict]:
    """투수 vs 좌타자/우타자 피안타율(AVG against) 크롤링.

    Basic1 타자유형별 필터 테이블 컬럼:
      [0]순위 [1]선수명 [2]팀명 [3]H [4]2B [5]3B [6]HR
      [7]BB  [8]HBP   [9]SO  [10]WP [11]BK [12]AVG

    Args:
        hand_value: "L" (좌타자) 또는 "R" (우타자) — ddlSituationDetail value

    Returns:
        [{"name": str, "team_short": str, "avg": float}]
    """
    label = "좌타자" if hand_value == "L" else "우타자"
    driver = make_driver()
    wait = WebDriverWait(driver, 15)
    results: list[dict] = []

    try:
        logger.info("투수 vs %s 피안타율 크롤링 시작", label)
        driver.get(PITCHER_URL)
        time.sleep(PAGE_DELAY)

        # 1) 정규시즌 선택 → AJAX로 ddlSituation 로드됨
        _select_and_wait(driver, wait, SERIES_ID, value=SERIES_REGULAR)
        # 2) 시즌 선택
        _select_and_wait(driver, wait, SEASON_ID, value=str(season))
        # 3) 타자유형별 선택
        _select_and_wait(driver, wait, SITUATION_ID, value="42")              # 타자유형별
        _select_and_wait(driver, wait, SITUATION_DETAIL_ID, value=hand_value)

        raw = _scrape_all_pages(driver)
        for r in raw:
            cols = r["cols"]
            if len(cols) < 13:
                continue
            raw_avg = cols[12].strip()
            if not raw_avg or raw_avg in ("-", "&nbsp;"):
                continue
            try:
                avg = float(raw_avg)
            except ValueError:
                continue
            results.append({
                "name": r["name"],
                "team_short": r["team_short"],
                "avg": avg,
            })

    finally:
        driver.quit()

    logger.info("vs %s 피안타율 수집 완료: %d명", label, len(results))
    return results


# ─── DB 업데이트 ─────────────────────────────────────────

def update_batter_risp(
    db_path: str,
    records: list[dict],
    season: int,
    team_map: dict[str, int],
) -> tuple[int, int]:
    """batter_season.ops_risp 업데이트."""
    conn = sqlite3.connect(db_path)
    updated = failed = 0

    for rec in records:
        player_id = _match_player(conn, rec["name"], rec["team_short"], team_map)
        if player_id is None:
            logger.warning("선수 미매칭: %s / %s", rec["name"], rec["team_short"])
            failed += 1
            continue

        result = conn.execute(
            "UPDATE batter_season SET ops_risp = ? WHERE player_id = ? AND season = ?",
            (rec["ops"], player_id, season),
        )
        if result.rowcount > 0:
            updated += 1
            logger.debug("  [OK] %s (%s) ops_risp=%.3f", rec["name"], rec["team_short"], rec["ops"])
        else:
            logger.debug("  [SKIP] batter_season 없음: %s", rec["name"])

    conn.commit()
    conn.close()
    return updated, failed


def update_pitcher_era_vs_hand(
    db_path: str,
    records: list[dict],
    season: int,
    col_name: str,
    team_map: dict[str, int],
) -> tuple[int, int]:
    """pitcher_season.avg_vs_lhb 또는 avg_vs_rhb 업데이트."""
    conn = sqlite3.connect(db_path)
    updated = failed = 0

    for rec in records:
        player_id = _match_player(conn, rec["name"], rec["team_short"], team_map)
        if player_id is None:
            logger.warning("선수 미매칭: %s / %s", rec["name"], rec["team_short"])
            failed += 1
            continue

        result = conn.execute(
            "UPDATE pitcher_season SET " + col_name + " = ? WHERE player_id = ? AND season = ?",
            (rec["avg"], player_id, season),
        )
        if result.rowcount > 0:
            updated += 1
            logger.debug("  [OK] %s (%s) %s=%.3f", rec["name"], rec["team_short"], col_name, rec["avg"])
        else:
            logger.debug("  [SKIP] pitcher_season 없음: %s", rec["name"])

    conn.commit()
    conn.close()
    return updated, failed


# ─── 검증 ────────────────────────────────────────────────

def verify(db_path: str, season: int) -> None:
    conn = sqlite3.connect(db_path)

    print("\n=== 득점권 OPS TOP5 (pa >= 50) ===")
    rows = conn.execute("""
        SELECT p.name, t.short_name, bs.ops_risp
        FROM batter_season bs
        JOIN players p ON bs.player_id = p.id
        JOIN teams t ON bs.team_id = t.id
        WHERE bs.season = ? AND bs.ops_risp IS NOT NULL AND bs.pa >= 50
        ORDER BY bs.ops_risp DESC LIMIT 5
    """, (season,)).fetchall()
    for r in rows:
        print(f"  {r[0]:<10} {r[1]:<8} {r[2]:.3f}")

    print("\n=== vs 좌타자 피안타율 최저 TOP5 (ip >= 30아웃) ===")
    rows = conn.execute("""
        SELECT p.name, t.short_name, ps.avg_vs_lhb
        FROM pitcher_season ps
        JOIN players p ON ps.player_id = p.id
        JOIN teams t ON ps.team_id = t.id
        WHERE ps.season = ? AND ps.avg_vs_lhb IS NOT NULL AND ps.ip_outs >= 30
        ORDER BY ps.avg_vs_lhb ASC LIMIT 5
    """, (season,)).fetchall()
    for r in rows:
        print(f"  {r[0]:<10} {r[1]:<8} {r[2]:.3f}")

    print("\n=== vs 우타자 피안타율 최저 TOP5 (ip >= 30아웃) ===")
    rows = conn.execute("""
        SELECT p.name, t.short_name, ps.avg_vs_rhb
        FROM pitcher_season ps
        JOIN players p ON ps.player_id = p.id
        JOIN teams t ON ps.team_id = t.id
        WHERE ps.season = ? AND ps.avg_vs_rhb IS NOT NULL AND ps.ip_outs >= 30
        ORDER BY ps.avg_vs_rhb ASC LIMIT 5
    """, (season,)).fetchall()
    for r in rows:
        print(f"  {r[0]:<10} {r[1]:<8} {r[2]:.3f}")

    total_b = conn.execute(
        "SELECT COUNT(*) FROM batter_season WHERE season=?", (season,)
    ).fetchone()[0]
    null_risp = conn.execute(
        "SELECT COUNT(*) FROM batter_season WHERE season=? AND ops_risp IS NULL", (season,)
    ).fetchone()[0]
    total_p = conn.execute(
        "SELECT COUNT(*) FROM pitcher_season WHERE season=?", (season,)
    ).fetchone()[0]
    null_lhb = conn.execute(
        "SELECT COUNT(*) FROM pitcher_season WHERE season=? AND avg_vs_lhb IS NULL", (season,)
    ).fetchone()[0]
    null_rhb = conn.execute(
        "SELECT COUNT(*) FROM pitcher_season WHERE season=? AND avg_vs_rhb IS NULL", (season,)
    ).fetchone()[0]

    print(f"\n=== NULL 잔여 ===")
    print(f"ops_risp    NULL: {null_risp}/{total_b}명")
    print(f"avg_vs_lhb  NULL: {null_lhb}/{total_p}명")
    print(f"avg_vs_rhb  NULL: {null_rhb}/{total_p}명")
    conn.close()


# ─── 메인 ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="KBO 기록실 상황별 스플릿 크롤링")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    parser.add_argument("--skip-risp", action="store_true", help="득점권 OPS 건너뜀")
    parser.add_argument("--skip-era", action="store_true", help="vs 좌타/우타 ERA 건너뜀")
    args = parser.parse_args()

    logger.info("=== KBO 상황별 스플릿 크롤링 시작 (season=%d) ===", args.season)

    team_map = build_team_name_to_id(args.db)
    logger.info("팀 매핑: %s", team_map)

    print(f"\n{'='*50}")
    print(f"시즌: {args.season}")

    # ── 1. 타자 득점권 OPS ──────────────────────────────
    if not args.skip_risp:
        risp_records = scrape_risp_ops(args.season)
        if risp_records:
            updated, failed = update_batter_risp(args.db, risp_records, args.season, team_map)
            print(f"득점권 OPS : 수집 {len(risp_records)}명 → 업데이트 {updated}명 (실패 {failed}명)")
        else:
            print("득점권 OPS : 수집 실패")

    # ── 2. 투수 vs 좌타 피안타율 ─────────────────────────
    if not args.skip_era:
        lhb_records = scrape_avg_vs_hand(args.season, "L")
        if lhb_records:
            updated, failed = update_pitcher_era_vs_hand(
                args.db, lhb_records, args.season, "avg_vs_lhb", team_map
            )
            print(f"vs 좌타 AVG: 수집 {len(lhb_records)}명 → 업데이트 {updated}명 (실패 {failed}명)")
        else:
            print("vs 좌타 AVG: 수집 실패")

        # ── 3. 투수 vs 우타 피안타율 ─────────────────────
        rhb_records = scrape_avg_vs_hand(args.season, "R")
        if rhb_records:
            updated, failed = update_pitcher_era_vs_hand(
                args.db, rhb_records, args.season, "avg_vs_rhb", team_map
            )
            print(f"vs 우타 AVG: 수집 {len(rhb_records)}명 → 업데이트 {updated}명 (실패 {failed}명)")
        else:
            print("vs 우타 AVG: 수집 실패")

    print(f"{'='*50}")

    verify(args.db, args.season)


if __name__ == "__main__":
    main()
