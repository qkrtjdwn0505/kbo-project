"""KBO 시즌 일정 수집기 — 예정/진행/종료 경기 포함

GetKboGameList API가 미래 날짜도 반환하므로, 날짜별 순회로
전체 시즌 일정을 수집한다. 기존 DB의 final 경기는 status를 유지하고
신규 scheduled 경기만 INSERT한다.

사용법:
    python -m src.data.collectors.kbo_schedule_collector --season 2026
    python -m src.data.collectors.kbo_schedule_collector --season 2026 --start 2026-03-28 --end 2026-09-30
"""

import argparse
import logging
import sqlite3
from datetime import date, timedelta

from src.data.batch.collect_season import game_id_to_int, SR_ID_MAP
from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.loaders.db_loader import DBLoader

logger = logging.getLogger(__name__)

# KBO API status_code → DB status 문자열
STATUS_MAP = {
    "1": "scheduled",
    "2": "in_progress",
    "3": "final",
    "4": "cancelled",
}

# 시즌별 기본 날짜 범위
SEASON_DATES = {
    2026: ("2026-03-12", "2026-10-05"),
    2025: ("2025-03-22", "2025-10-05"),
}


def _existing_final_ids(db_path: str) -> set[int]:
    """DB에 이미 final로 저장된 경기 ID 집합 반환 (skip 용도)"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id FROM games WHERE status = 'final'").fetchall()
    conn.close()
    return {r[0] for r in rows}


def collect_schedule(
    season: int = 2026,
    start_date: str | None = None,
    end_date: str | None = None,
    db_path: str | None = None,
) -> int:
    """시즌 전체 일정 수집.

    이미 final인 경기는 status를 유지하고,
    scheduled/in_progress는 INSERT OR UPDATE (status만 갱신).
    """
    loader = DBLoader(db_path)
    actual_db = loader.db_path

    default_start, default_end = SEASON_DATES.get(season, (f"{season}-03-22", f"{season}-10-05"))
    start = date.fromisoformat(start_date or default_start)
    end = date.fromisoformat(end_date or default_end)

    final_ids = _existing_final_ids(actual_db)
    collector = KBODataCollector(delay=1.0)

    total = 0
    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        raw_games = collector.get_game_list(date_str)

        records = []
        for g in raw_games:
            gid = game_id_to_int(g["game_id"])

            # 이미 종료된 경기면 status 변경 없이 skip
            if gid in final_ids:
                continue

            status_code = str(g.get("status_code", "1"))
            status = STATUS_MAP.get(status_code, "scheduled")

            # 취소 경기는 건너뜀
            if status == "cancelled":
                continue

            records.append({
                "id": gid,
                "date": g["date"],
                "time": g.get("time") or None,
                "stadium": g.get("stadium") or None,
                "home_team_id": g["home_team_id"],
                "away_team_id": g["away_team_id"],
                "home_score": g.get("home_score"),
                "away_score": g.get("away_score"),
                "status": status,
                "day_of_week": None,
                "is_night_game": None,
                "game_type": SR_ID_MAP.get(g.get("sr_id", 0), "regular"),
            })

        if records:
            loader.load_games(records)
            total += len(records)
            print(f"  {current}: {len(records)}경기 저장 (누적 {total})")

        current += timedelta(days=1)

    print(f"\n완료: 총 {total}경기 저장")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KBO 시즌 일정 수집기")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--start", type=str, help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--db", type=str, help="DB 경로 (기본: kbo.db)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    collect_schedule(
        season=args.season,
        start_date=args.start,
        end_date=args.end,
        db_path=args.db,
    )
