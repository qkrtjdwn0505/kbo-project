"""KBO 기록실 시즌 통계 스크래퍼 — 도루(SB/CS) 보강

KBO 기록실 주루 기록 페이지(Runner/Basic.aspx)를 Selenium으로 크롤링하여
선수별 SB(도루), CS(도루실패)를 batter_season 테이블에 UPDATE합니다.

KBO 박스스코어 API(GetBoxScoreScroll)의 타자 table3에 SB 컬럼이 없어서
경기별(batter_stats.sb)은 채울 수 없지만,
시즌 누적 순위 표시에는 충분합니다.

사용:
    python -m src.data.collectors.kbo_season_stats_scraper
    python -m src.data.collectors.kbo_season_stats_scraper --season 2025
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

RUNNER_URL = "https://www.koreabaseball.com/Record/Player/Runner/Basic.aspx"
SEASON_SELECT_ID = "cphContents_cphContents_cphContents_ddlSeason_ddlSeason"
PAGE_DELAY = 1.5  # 페이지 이동 간격 (초)
MAX_PAGES = 30   # 무한루프 방지

# KBO 기록실 팀명 약칭 → DB teams.name 접두어 매핑
TEAM_SHORT_TO_DB_PREFIX: dict[str, str] = {
    "KIA":  "KIA",
    "삼성":  "삼성",
    "LG":   "LG",
    "두산":  "두산",
    "KT":   "KT",
    "SSG":  "SSG",
    "롯데":  "롯데",
    "한화":  "한화",
    "NC":   "NC",
    "키움":  "키움",
}


def build_team_name_to_id(db_path: str) -> dict[str, int]:
    """DB teams 테이블에서 팀명 약칭 → team_id 매핑 생성."""
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


def scrape_runner_stats(season: int) -> list[dict]:
    """KBO 기록실 주루 기록 페이지에서 시즌 전체 선수 데이터 수집.

    Returns:
        list[dict]: 각 dict는 {name, team_short, sb, cs} 포함
    """
    driver = make_driver()
    wait = WebDriverWait(driver, 10)
    records: list[dict] = []

    try:
        logger.info(f"KBO 기록실 주루 기록 페이지 접근: {RUNNER_URL}")
        driver.get(RUNNER_URL)
        time.sleep(PAGE_DELAY)

        # 시즌 선택
        season_sel = wait.until(EC.presence_of_element_located((By.ID, SEASON_SELECT_ID)))
        Select(season_sel).select_by_value(str(season))
        logger.info(f"{season} 시즌 선택 완료")
        time.sleep(PAGE_DELAY)

        page = 1
        while page <= MAX_PAGES:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            tbl = soup.find("table", class_="tData01")

            if not tbl:
                logger.warning(f"페이지 {page}: 테이블 없음")
                break

            rows_found = 0
            for row in tbl.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                # 컬럼: 순위, 선수명, 팀명, G, SBA, SB, CS, SB%, OOB, PKO
                if len(cells) < 7:
                    continue
                _, name, team_short, _, _, sb_str, cs_str, *_ = cells
                if not name or name in ("합계", "TOTALS"):
                    continue

                try:
                    sb = int(sb_str) if sb_str.isdigit() else 0
                    cs = int(cs_str) if cs_str.isdigit() else 0
                except ValueError:
                    sb = cs = 0

                records.append({
                    "name": name.strip(),
                    "team_short": team_short.strip(),
                    "sb": sb,
                    "cs": cs,
                })
                rows_found += 1

            logger.info(f"페이지 {page}: {rows_found}명 수집")

            # 다음 페이지 버튼
            try:
                next_btn = driver.find_element(By.LINK_TEXT, str(page + 1))
                next_btn.click()
                time.sleep(PAGE_DELAY)
                page += 1
            except NoSuchElementException:
                logger.info("마지막 페이지 도달")
                break

    finally:
        driver.quit()

    logger.info(f"총 {len(records)}명 수집 완료")
    return records


def update_batter_season(
    db_path: str,
    records: list[dict],
    season: int,
    team_map: dict[str, int],
) -> tuple[int, int]:
    """수집 데이터를 batter_season 테이블에 업데이트.

    Returns:
        (updated_count, failed_count)
    """
    conn = sqlite3.connect(db_path)
    updated = 0
    failed = 0

    for rec in records:
        name = rec["name"]
        team_short = rec["team_short"]
        sb = rec["sb"]
        cs = rec["cs"]

        team_id = team_map.get(team_short)
        if team_id is None:
            logger.warning(f"팀 매핑 실패: {team_short!r} ({name})")
            failed += 1
            continue

        # 선수 조회 (이름 + 팀)
        player_rows = conn.execute(
            "SELECT id FROM players WHERE name = ? AND team_id = ?",
            (name, team_id),
        ).fetchall()

        if not player_rows:
            # 동명이인이 없으면 팀 무관 이름만으로 시도
            player_rows = conn.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                (name,),
            ).fetchall()
            if len(player_rows) == 1:
                player_id = player_rows[0][0]
                logger.debug(f"팀 무관 매칭: {name} (team_short={team_short!r})")
            else:
                logger.warning(
                    f"선수 미매칭: {name} / {team_short} "
                    f"(후보={len(player_rows)}명)"
                )
                failed += 1
                continue
        else:
            player_id = player_rows[0][0]

        # batter_season UPDATE
        result = conn.execute(
            """
            UPDATE batter_season SET sb = ?, cs = ?
            WHERE player_id = ? AND season = ?
            """,
            (sb, cs, player_id, season),
        )
        if result.rowcount > 0:
            updated += 1
            if sb > 0:
                logger.debug(f"  [OK] {name} ({team_short}) sb={sb} cs={cs}")
        else:
            logger.debug(f"  [SKIP] batter_season 없음: {name} season={season}")

    conn.commit()
    conn.close()
    return updated, failed


def verify(db_path: str, season: int) -> None:
    """업데이트 후 검증."""
    conn = sqlite3.connect(db_path)

    print("\n=== 도루 TOP10 (batter_season) ===")
    rows = conn.execute("""
        SELECT p.name, t.name, bs.sb, bs.cs
        FROM batter_season bs
        JOIN players p ON bs.player_id = p.id
        JOIN teams t ON bs.team_id = t.id
        WHERE bs.season = ?
        ORDER BY bs.sb DESC
        LIMIT 10
    """, (season,)).fetchall()
    for r in rows:
        print(f"  {r[0]:<10} {r[1]:<12} SB={r[2]:>3}  CS={r[3]:>2}")

    total_nonzero = conn.execute(
        "SELECT COUNT(*) FROM batter_season WHERE season=? AND sb > 0",
        (season,),
    ).fetchone()[0]
    print(f"\nSB > 0 선수 수: {total_nonzero}명")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="KBO 기록실 도루 기록 스크래핑")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    args = parser.parse_args()

    logger.info(f"=== KBO 도루 기록 보강 시작 (season={args.season}) ===")

    team_map = build_team_name_to_id(args.db)
    logger.info(f"팀 매핑: {team_map}")

    records = scrape_runner_stats(args.season)

    updated, failed = update_batter_season(args.db, records, args.season, team_map)

    print(f"\n{'='*50}")
    print(f"수집: {len(records)}명")
    print(f"업데이트: {updated}명")
    if failed:
        print(f"실패: {failed}명")

    verify(args.db, args.season)


if __name__ == "__main__":
    main()
