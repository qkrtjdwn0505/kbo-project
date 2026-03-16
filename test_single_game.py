"""T-1.5b 검증: 한 경기 테스트 수집 + table2 파싱 결과 확인

1경기만 수집하여 batter_stats에 상세 기록이 정상 저장되는지 확인.
확인 항목: 2B, 3B, HR, BB, HBP, SO, SF, GDP, IBB가 0이 아닌 정상 값인지.
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.loaders.db_loader import DBLoader
from src.data.batch.collect_season import (
    collect_date,
    load_existing_player_ids,
)

DB_PATH = PROJECT_ROOT / "kbo.db"


def test_single_game():
    # 1. 테스트용 날짜 (3/22 — 5경기 있는 날)
    test_date = "20250322"

    print(f"=== T-1.5b 검증: {test_date} 수집 테스트 ===\n")

    collector = KBODataCollector(delay=1.0)
    loader = DBLoader()
    load_existing_player_ids(loader.db_path)

    # 2. 수집 실행
    result = collect_date(collector, loader, test_date)
    print(f"수집 결과: {result}\n")

    # 3. DB에서 해당 날짜 타자 기록 확인
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 해당 날짜 경기 ID 조회
    games = conn.execute(
        "SELECT id, date, home_team_id, away_team_id FROM games WHERE date = '2025-03-22'"
    ).fetchall()
    print(f"DB 경기 수: {len(games)}\n")

    if not games:
        print("❌ 경기가 저장되지 않았습니다.")
        conn.close()
        return

    game_id = games[0]["id"]

    # 4. 핵심 검증: 상세 기록이 채워졌는가?
    batters = conn.execute("""
        SELECT
            p.name, bs.pa, bs.ab, bs.hits,
            bs.doubles, bs.triples, bs.hr,
            bs.bb, bs.ibb, bs.hbp, bs.so,
            bs.sf, bs.gdp, bs.rbi, bs.runs
        FROM batter_stats bs
        JOIN players p ON bs.player_id = p.id
        WHERE bs.game_id = ?
        ORDER BY bs.id
        LIMIT 20
    """, (game_id,)).fetchall()

    print(f"--- 첫 경기 타자 기록 (game_id={game_id}) ---")
    print(f"{'선수':8s} PA  AB   H  2B  3B  HR  BB IBB HBP  SO  SF GDP RBI   R")
    print("-" * 75)

    has_detail = False
    for b in batters:
        print(
            f"{b['name']:8s} "
            f"{b['pa']:2d}  {b['ab']:2d}  {b['hits']:2d}  "
            f"{b['doubles']:2d}  {b['triples']:2d}  {b['hr']:2d}  "
            f"{b['bb']:2d}  {b['ibb']:2d}  {b['hbp']:2d}  "
            f"{b['so']:2d}  {b['sf']:2d}  {b['gdp']:2d}  "
            f"{b['rbi']:2d}  {b['runs']:2d}"
        )
        # 2B/3B/HR/BB/SO 중 하나라도 0이 아니면 상세 기록 있음
        if any([b['doubles'], b['triples'], b['hr'], b['bb'], b['so']]):
            has_detail = True

    # 5. 전체 통계
    totals = conn.execute("""
        SELECT
            COUNT(*) as cnt,
            SUM(doubles) as sum_2b,
            SUM(triples) as sum_3b,
            SUM(hr) as sum_hr,
            SUM(bb) as sum_bb,
            SUM(hbp) as sum_hbp,
            SUM(so) as sum_so,
            SUM(sf) as sum_sf,
            SUM(gdp) as sum_gdp,
            SUM(ibb) as sum_ibb
        FROM batter_stats bs
        JOIN games g ON bs.game_id = g.id
        WHERE g.date = '2025-03-22'
    """).fetchone()

    print(f"\n--- 3/22 전체 합산 ---")
    print(f"타자 기록 수: {totals['cnt']}")
    print(f"2B: {totals['sum_2b']}, 3B: {totals['sum_3b']}, HR: {totals['sum_hr']}")
    print(f"BB: {totals['sum_bb']}, HBP: {totals['sum_hbp']}, IBB: {totals['sum_ibb']}")
    print(f"SO: {totals['sum_so']}, SF: {totals['sum_sf']}, GDP: {totals['sum_gdp']}")

    # 6. 판정
    print(f"\n{'='*50}")
    if has_detail and totals['sum_bb'] > 0 and totals['sum_so'] > 0:
        print("✅ 검증 통과: table2 파싱이 정상 동작합니다.")
        print("   전체 재수집을 진행해도 됩니다.")
    else:
        print("❌ 검증 실패: 상세 기록이 여전히 0입니다.")
        print("   kbo_data_collector.py와 collect_season.py를 다시 확인하세요.")

    conn.close()


if __name__ == "__main__":
    test_single_game()
