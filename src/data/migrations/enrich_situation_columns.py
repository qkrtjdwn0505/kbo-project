"""상황 컬럼 보강 — is_home, opponent_pitcher_hand, games 선발투수 ID

기존 DB 데이터(768경기)에서 SQL UPDATE로 NULL 컬럼을 채운다.

1) batter_stats.is_home   — games.home_team_id 조인
2) pitcher_stats.is_home  — games.home_team_id 조인
3) players.throw_hand/bat_hand — KBO 홈페이지 선수등록 페이지 스크래핑
4) games.home_starter_id/away_starter_id — pitcher_stats.is_starter 역추적
5) batter_stats.opponent_pitcher_hand — games 선발투수 → players.throw_hand

실행: python -m src.data.migrations.enrich_situation_columns
"""

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "kbo.db"
HAND_DATA_PATH = PROJECT_ROOT / "player_hand_data.json"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    print("=" * 60)
    print("  상황 컬럼 보강 시작")
    print("=" * 60)

    # ── 사전 확인 ──────────────────────────────────
    print("\n[사전 확인]")

    c.execute("SELECT COUNT(*) FROM batter_stats WHERE is_home IS NULL")
    print(f"  batter_stats.is_home NULL: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM pitcher_stats WHERE is_home IS NULL")
    print(f"  pitcher_stats.is_home NULL: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM batter_stats WHERE opponent_pitcher_hand IS NULL")
    print(f"  batter_stats.opponent_pitcher_hand NULL: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM players WHERE throw_hand IS NOT NULL")
    print(f"  players.throw_hand NOT NULL: {c.fetchone()[0]}명")

    c.execute("SELECT COUNT(*) FROM players WHERE bat_hand IS NOT NULL")
    print(f"  players.bat_hand NOT NULL: {c.fetchone()[0]}명")

    c.execute("""
        SELECT COUNT(*) FROM games
        WHERE home_starter_id IS NOT NULL AND away_starter_id IS NOT NULL
    """)
    print(f"  선발투수 ID 있는 경기: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM games WHERE status = 'final'")
    total_games = c.fetchone()[0]
    print(f"  종료된 경기 총: {total_games}건")

    # ── Step 1: batter_stats.is_home ──────────────
    print("\n[Step 1] batter_stats.is_home 채우기")
    c.execute("""
        UPDATE batter_stats
        SET is_home = (
            SELECT CASE
                WHEN batter_stats.team_id = g.home_team_id THEN 1
                ELSE 0
            END
            FROM games g
            WHERE g.id = batter_stats.game_id
        )
        WHERE is_home IS NULL
    """)
    print(f"  → {c.rowcount}건 업데이트")

    # ── Step 2: pitcher_stats.is_home ─────────────
    print("\n[Step 2] pitcher_stats.is_home 채우기")
    c.execute("""
        UPDATE pitcher_stats
        SET is_home = (
            SELECT CASE
                WHEN pitcher_stats.team_id = g.home_team_id THEN 1
                ELSE 0
            END
            FROM games g
            WHERE g.id = pitcher_stats.game_id
        )
        WHERE is_home IS NULL
    """)
    print(f"  → {c.rowcount}건 업데이트")

    # ── Step 3: players.throw_hand / bat_hand ─────
    print("\n[Step 3] players.throw_hand / bat_hand 채우기")
    if HAND_DATA_PATH.exists():
        with open(HAND_DATA_PATH, "r", encoding="utf-8") as f:
            scraped = json.load(f)
        _update_player_hands(c, scraped)
    else:
        print("  player_hand_data.json 없음 → 스크래핑 시도")
        scraped = _scrape_player_hands()
        if scraped:
            with open(HAND_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(scraped, f, ensure_ascii=False, indent=2)
            _update_player_hands(c, scraped)
        else:
            print("  ⚠ 스크래핑 실패 — throw_hand/bat_hand 보강 건너뜀")

    # ── Step 4: games.home_starter_id / away_starter_id ──
    print("\n[Step 4] games 선발투수 ID 채우기 (pitcher_stats.is_starter 역추적)")
    c.execute("""
        UPDATE games
        SET home_starter_id = (
            SELECT ps.player_id
            FROM pitcher_stats ps
            WHERE ps.game_id = games.id
              AND ps.team_id = games.home_team_id
              AND ps.is_starter = 1
            LIMIT 1
        )
        WHERE home_starter_id IS NULL
    """)
    print(f"  home_starter_id → {c.rowcount}건 업데이트")

    c.execute("""
        UPDATE games
        SET away_starter_id = (
            SELECT ps.player_id
            FROM pitcher_stats ps
            WHERE ps.game_id = games.id
              AND ps.team_id = games.away_team_id
              AND ps.is_starter = 1
            LIMIT 1
        )
        WHERE away_starter_id IS NULL
    """)
    print(f"  away_starter_id → {c.rowcount}건 업데이트")

    # ── Step 5: batter_stats.opponent_pitcher_hand ─
    print("\n[Step 5] batter_stats.opponent_pitcher_hand 채우기")
    c.execute("""
        UPDATE batter_stats
        SET opponent_pitcher_hand = (
            SELECT p.throw_hand
            FROM games g
            JOIN players p ON p.id = CASE
                WHEN batter_stats.team_id = g.home_team_id THEN g.away_starter_id
                ELSE g.home_starter_id
            END
            WHERE g.id = batter_stats.game_id
        )
        WHERE opponent_pitcher_hand IS NULL
    """)
    print(f"  → {c.rowcount}건 업데이트")

    conn.commit()

    # ── 검증 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  보강 후 검증")
    print("=" * 60)

    # NULL 잔여
    c.execute("SELECT COUNT(*) FROM batter_stats WHERE is_home IS NULL")
    print(f"\n  batter_stats.is_home NULL 잔여: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM pitcher_stats WHERE is_home IS NULL")
    print(f"  pitcher_stats.is_home NULL 잔여: {c.fetchone()[0]}건")

    c.execute("SELECT COUNT(*) FROM batter_stats WHERE opponent_pitcher_hand IS NULL")
    remaining_oph = c.fetchone()[0]
    print(f"  opponent_pitcher_hand NULL 잔여: {remaining_oph}건")

    c.execute("SELECT COUNT(*) FROM players WHERE throw_hand IS NULL")
    print(f"  players.throw_hand NULL 잔여: {c.fetchone()[0]}명")

    c.execute("""
        SELECT COUNT(*) FROM games
        WHERE home_starter_id IS NOT NULL AND away_starter_id IS NOT NULL
    """)
    print(f"  선발투수 ID 있는 경기: {c.fetchone()[0]}건 / {total_games}건")

    # 홈/원정 분포
    print("\n  [batter_stats 홈/원정 분포]")
    c.execute("""
        SELECT is_home, COUNT(*) FROM batter_stats
        WHERE is_home IS NOT NULL GROUP BY is_home
    """)
    for row in c.fetchall():
        label = "홈" if row[0] == 1 else "원정"
        print(f"    {label}: {row[1]:,}건")

    print("\n  [pitcher_stats 홈/원정 분포]")
    c.execute("""
        SELECT is_home, COUNT(*) FROM pitcher_stats
        WHERE is_home IS NOT NULL GROUP BY is_home
    """)
    for row in c.fetchall():
        label = "홈" if row[0] == 1 else "원정"
        print(f"    {label}: {row[1]:,}건")

    # 상대투수 투구손 분포
    print("\n  [opponent_pitcher_hand 분포]")
    c.execute("""
        SELECT opponent_pitcher_hand, COUNT(*) FROM batter_stats
        WHERE opponent_pitcher_hand IS NOT NULL
        GROUP BY opponent_pitcher_hand
    """)
    for row in c.fetchall():
        print(f"    상대투수 {row[0]}: {row[1]:,}건")

    # throw_hand 분포
    print("\n  [players.throw_hand 분포]")
    c.execute("""
        SELECT throw_hand, COUNT(*) FROM players
        WHERE throw_hand IS NOT NULL GROUP BY throw_hand
    """)
    for row in c.fetchall():
        print(f"    {row[0]}: {row[1]}명")

    print("\n  [players.bat_hand 분포]")
    c.execute("""
        SELECT bat_hand, COUNT(*) FROM players
        WHERE bat_hand IS NOT NULL GROUP BY bat_hand
    """)
    for row in c.fetchall():
        print(f"    {row[0]}: {row[1]}명")

    # 상식 검증
    print("\n  [상식 검증]")
    c.execute("SELECT SUM(CASE WHEN is_home=1 THEN 1 ELSE 0 END), SUM(CASE WHEN is_home=0 THEN 1 ELSE 0 END) FROM batter_stats WHERE is_home IS NOT NULL")
    home, away = c.fetchone()
    if home and away:
        ratio = home / (home + away) * 100
        print(f"    홈/원정 비율: {ratio:.1f}% / {100-ratio:.1f}% {'✓ ~50:50' if 45 < ratio < 55 else '⚠ 비대칭'}")

    c.execute("SELECT SUM(CASE WHEN opponent_pitcher_hand='우투' THEN 1 ELSE 0 END), SUM(CASE WHEN opponent_pitcher_hand='좌투' THEN 1 ELSE 0 END) FROM batter_stats WHERE opponent_pitcher_hand IS NOT NULL")
    rhp, lhp = c.fetchone()
    if rhp and lhp:
        print(f"    우투/좌투 비율: {rhp:,} / {lhp:,} {'✓ 우투 > 좌투' if rhp > lhp else '⚠ 좌투가 더 많음'}")

    conn.close()
    print("\n✅ 보강 완료")


def _update_player_hands(cursor, scraped: list[dict]):
    """스크래핑된 데이터로 players.throw_hand / bat_hand 업데이트"""
    by_name_team = {}
    by_name = {}
    for p in scraped:
        key = (p["name"], p["team_id"])
        by_name_team[key] = p
        if p["name"] not in by_name:
            by_name[p["name"]] = p

    cursor.execute("SELECT id, name, team_id FROM players WHERE throw_hand IS NULL")
    db_players = cursor.fetchall()

    exact = name_only = 0
    for pid, name, team_id in db_players:
        key = (name, team_id)
        if key in by_name_team:
            p = by_name_team[key]
            cursor.execute(
                "UPDATE players SET throw_hand = ?, bat_hand = ? WHERE id = ?",
                (p["throw_hand"], p["bat_hand"], pid),
            )
            exact += 1
        elif name in by_name:
            p = by_name[name]
            cursor.execute(
                "UPDATE players SET throw_hand = ?, bat_hand = ? WHERE id = ?",
                (p["throw_hand"], p["bat_hand"], pid),
            )
            name_only += 1

    print(f"  정확 매칭(이름+팀): {exact}건")
    print(f"  이름 매칭: {name_only}건")
    print(f"  총 업데이트: {exact + name_only}건")

    cursor.execute("SELECT COUNT(*) FROM players WHERE throw_hand IS NULL")
    print(f"  여전히 NULL: {cursor.fetchone()[0]}명")


def _scrape_player_hands() -> list[dict]:
    """KBO 선수등록 페이지에서 투타 정보 스크래핑 (Selenium)"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("  ⚠ selenium 미설치 — pip install selenium")
        return []

    TEAM_MAP = {
        "OB": 4, "HT": 1, "SS": 2, "LG": 3, "KT": 5,
        "SK": 6, "LT": 7, "HH": 8, "NC": 9, "WO": 10,
    }

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    all_players = []

    try:
        driver.get("https://www.koreabaseball.com/Player/Register.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="playerId"]'))
        )

        for team_code, team_id in TEAM_MAP.items():
            if team_code != "OB":
                tab = driver.find_element(
                    By.CSS_SELECTOR, f'li[data-id="{team_code}"] a'
                )
                tab.click()
                time.sleep(2.5)

            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            count = 0
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    try:
                        link = cells[1].find_element(By.TAG_NAME, "a")
                        name = link.text.strip()
                        hand_info = cells[2].text.strip()
                        m = re.match(
                            r"(좌투|우투|좌언|우언|양투)(좌타|우타|양타)", hand_info
                        )
                        if m and name:
                            all_players.append({
                                "name": name,
                                "team_id": team_id,
                                "throw_hand": m.group(1).replace("언", "투"),
                                "bat_hand": m.group(2),
                            })
                            count += 1
                    except Exception:
                        pass

            print(f"  {team_code}: {count}명")
            if team_code == "OB":
                time.sleep(1)
    finally:
        driver.quit()

    print(f"  총 스크래핑: {len(all_players)}명")
    return all_players


if __name__ == "__main__":
    main()
