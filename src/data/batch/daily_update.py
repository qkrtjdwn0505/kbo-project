"""매일 실행: 새 경기 수집 → 상황 컬럼 보강 → 시즌 재집계 → 도루 재적용

실행 흐름:
  1. 지정 날짜(기본: 어제) 경기 목록 조회
  2. DB에 없는 종료 경기만 박스스코어 수집 + 저장
  3. is_home, 선발투수 ID, 상대투수 투구손 보강 (NULL → UPDATE)
  4. 시즌 누적 재집계 (타자/투수, 스플릿 포함)
  5. KBO 기록실 도루 재적용 (COALESCE로 기존값 보존)

사용:
    python -m src.data.batch.daily_update
    python -m src.data.batch.daily_update --date 20260322
    python -m src.data.batch.daily_update --from 20260320 --to 20260325
    python -m src.data.batch.daily_update --season 2026
    python -m src.data.batch.daily_update --skip-scraper
"""

import argparse
import logging
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.loaders.db_loader import DBLoader
from src.data.processors.season_aggregator import SeasonAggregator
from src.data.batch.collect_season import (
    game_id_to_int,
    transform_game,
    transform_batters,
    transform_pitchers,
    load_existing_player_ids,
)
from src.data.collectors.kbo_season_stats_scraper import (
    scrape_runner_stats,
    update_batter_season,
    build_team_name_to_id,
)

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


# ─── 로깅 설정 ───────────────────────────────────────────

def setup_logging(date_str: str) -> None:
    """날짜별 로그 파일 + 콘솔 출력"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(
                LOG_DIR / f"daily_update_{date_str}.log", encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )


# ─── 날짜 유틸 ───────────────────────────────────────────

def iter_dates(start_str: str, end_str: str):
    """YYYYMMDD 형식 날짜 순회"""
    def parse(s: str) -> date:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    d, end_d = parse(start_str), parse(end_str)
    while d <= end_d:
        yield d.strftime("%Y%m%d")
        d += timedelta(days=1)


# ─── 수집 ────────────────────────────────────────────────

def game_exists(
    conn: sqlite3.Connection,
    game_int_id: int,
    formatted_date: str,
    home_team_id: int,
    away_team_id: int,
    home_score: int,
    away_score: int,
) -> bool:
    """경기가 이미 DB에 있는지 확인.

    두 가지 방법으로 확인:
      1) 결정론적 ID — collect_missing / daily_update로 수집된 경기
      2) (날짜, 팀, 스코어) — 기존 hash-based ID로 수집된 경기
    """
    if conn.execute("SELECT 1 FROM games WHERE id = ?", (game_int_id,)).fetchone():
        return True
    return conn.execute(
        """
        SELECT 1 FROM games
        WHERE date = ? AND home_team_id = ? AND away_team_id = ?
          AND home_score = ? AND away_score = ? AND status = 'final'
        """,
        (formatted_date, home_team_id, away_team_id, home_score, away_score),
    ).fetchone() is not None


def collect_new_games(
    collector: KBODataCollector,
    loader: DBLoader,
    conn: sqlite3.Connection,
    date_str: str,
) -> dict:
    """단일 날짜의 신규 종료 경기만 수집 + DB 저장.

    이미 DB에 있는 경기는 skip. 개별 경기 실패 시 로그 후 계속 진행.

    Returns:
        {"new": int, "skipped": int, "failed": int,
         "batter_stats": int, "pitcher_stats": int}
    """
    result = {
        "new": 0, "skipped": 0, "failed": 0,
        "batter_stats": 0, "pitcher_stats": 0,
    }

    game_list = collector.get_game_list(date_str)
    final_games = [
        g for g in game_list
        if g.get("status_code") == "3"
        and g["home_team_id"] > 0
        and g["away_team_id"] > 0
    ]

    if not final_games:
        return result

    for game_info in final_games:
        game_int_id = game_id_to_int(game_info["game_id"])
        formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        h_score = game_info.get("home_score") or 0
        a_score = game_info.get("away_score") or 0

        if game_exists(
            conn, game_int_id, formatted,
            game_info["home_team_id"], game_info["away_team_id"],
            h_score, a_score,
        ):
            result["skipped"] += 1
            continue

        try:
            game = transform_game(game_info)

            boxscore = collector.get_boxscore(
                game_id=game_info["game_id"],
                sr_id=game_info.get("sr_id", 0),
                season=game_info.get("season", int(date_str[:4])),
            )
            if not boxscore:
                logger.warning("박스스코어 없음: %s", game_info["game_id"])
                result["failed"] += 1
                continue

            all_batter_stats: list[dict] = []
            all_pitcher_stats: list[dict] = []
            all_players: list[dict] = []

            for batters, team_id, is_home in [
                (boxscore["away_batters"], game_info["away_team_id"], False),
                (boxscore["home_batters"], game_info["home_team_id"], True),
            ]:
                b_stats, b_players = transform_batters(
                    batters, game["id"], team_id, is_home
                )
                all_batter_stats.extend(b_stats)
                all_players.extend(b_players)

            for pitchers, team_id, is_home in [
                (boxscore["away_pitchers"], game_info["away_team_id"], False),
                (boxscore["home_pitchers"], game_info["home_team_id"], True),
            ]:
                p_stats, p_players = transform_pitchers(
                    pitchers, game["id"], team_id, is_home
                )
                all_pitcher_stats.extend(p_stats)
                all_players.extend(p_players)

            seen: set[int] = set()
            unique_players = [
                p for p in all_players
                if not (p["id"] in seen or seen.add(p["id"]))
            ]

            if unique_players:
                loader.load_players(unique_players)
            loader.load_games([game])
            if all_batter_stats:
                loader.load_batter_stats(all_batter_stats)
            if all_pitcher_stats:
                loader.load_pitcher_stats(all_pitcher_stats)

            away = game_info.get("away_team", "?")
            home = game_info.get("home_team", "?")
            logger.info(
                "  [OK] %s  %s %s-%s %s  타자=%d건, 투수=%d건",
                game_info["game_id"], away,
                game_info.get("away_score", 0), game_info.get("home_score", 0),
                home, len(all_batter_stats), len(all_pitcher_stats),
            )
            result["new"] += 1
            result["batter_stats"] += len(all_batter_stats)
            result["pitcher_stats"] += len(all_pitcher_stats)

        except Exception as exc:
            logger.error("  [FAIL] %s: %s", game_info["game_id"], exc)
            result["failed"] += 1

    return result


# ─── 보강 ────────────────────────────────────────────────

def enrich_situation_columns(conn: sqlite3.Connection) -> int:
    """신규 경기의 상황 컬럼 보강 (NULL인 행만 UPDATE).

    Steps:
      1. batter_stats.is_home
      2. pitcher_stats.is_home
      3. games.home_starter_id / away_starter_id
      4. batter_stats.opponent_pitcher_hand

    Returns:
        총 UPDATE 건수
    """
    c = conn.cursor()
    total = 0

    c.execute("""
        UPDATE batter_stats SET is_home = (
            SELECT CASE WHEN batter_stats.team_id = g.home_team_id THEN 1 ELSE 0 END
            FROM games g WHERE g.id = batter_stats.game_id
        ) WHERE is_home IS NULL
    """)
    total += c.rowcount

    c.execute("""
        UPDATE pitcher_stats SET is_home = (
            SELECT CASE WHEN pitcher_stats.team_id = g.home_team_id THEN 1 ELSE 0 END
            FROM games g WHERE g.id = pitcher_stats.game_id
        ) WHERE is_home IS NULL
    """)
    total += c.rowcount

    c.execute("""
        UPDATE games SET home_starter_id = (
            SELECT ps.player_id FROM pitcher_stats ps
            WHERE ps.game_id = games.id
              AND ps.team_id = games.home_team_id
              AND ps.is_starter = 1
            LIMIT 1
        ) WHERE home_starter_id IS NULL
    """)

    c.execute("""
        UPDATE games SET away_starter_id = (
            SELECT ps.player_id FROM pitcher_stats ps
            WHERE ps.game_id = games.id
              AND ps.team_id = games.away_team_id
              AND ps.is_starter = 1
            LIMIT 1
        ) WHERE away_starter_id IS NULL
    """)

    c.execute("""
        UPDATE batter_stats SET opponent_pitcher_hand = (
            SELECT p.throw_hand FROM games g
            JOIN players p ON p.id = CASE
                WHEN batter_stats.team_id = g.home_team_id THEN g.away_starter_id
                ELSE g.home_starter_id
            END
            WHERE g.id = batter_stats.game_id
        ) WHERE opponent_pitcher_hand IS NULL
    """)
    total += c.rowcount

    conn.commit()
    return total


# ─── 메인 ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="KBO 일일 업데이트")
    parser.add_argument("--date", type=str, help="특정 날짜 (YYYYMMDD)")
    parser.add_argument("--from", dest="date_from", type=str, help="시작 날짜 (YYYYMMDD)")
    parser.add_argument("--to", dest="date_to", type=str, help="종료 날짜 (YYYYMMDD)")
    parser.add_argument(
        "--season", type=int, default=date.today().year,
        help="시즌 연도 (기본: 올해)",
    )
    parser.add_argument(
        "--skip-scraper", action="store_true",
        help="도루 크롤링(Selenium) 건너뜀",
    )
    args = parser.parse_args()

    # 날짜 범위 결정
    if args.date:
        start_str = end_str = args.date
    elif args.date_from:
        start_str = args.date_from
        end_str = args.date_to or args.date_from
    else:
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
        start_str = end_str = yesterday

    setup_logging(start_str)

    logger.info("=" * 50)
    logger.info("=== 일일 업데이트: %s ~ %s (시즌: %d) ===",
                start_str, end_str, args.season)
    logger.info("=" * 50)

    loader = DBLoader()
    load_existing_player_ids(loader.db_path)
    collector = KBODataCollector(delay=0.5)
    conn = sqlite3.connect(loader.db_path)

    totals = {
        "new": 0, "skipped": 0, "failed": 0,
        "batter_stats": 0, "pitcher_stats": 0,
    }

    # ── Step 1: 경기 수집 ────────────────────────────────
    for date_str in iter_dates(start_str, end_str):
        formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        logger.info("\n[수집] %s", formatted)
        result = collect_new_games(collector, loader, conn, date_str)
        for k in totals:
            totals[k] += result.get(k, 0)

    logger.info(
        "\n경기 목록: 신규 %d경기, skip %d경기, 실패 %d경기",
        totals["new"], totals["skipped"], totals["failed"],
    )

    if totals["new"] == 0:
        logger.info("신규 경기 없음 — 집계/보강 건너뜀")
        conn.close()
        logger.info("\n=== 완료 ===")
        return

    # ── Step 2: 상황 컬럼 보강 ──────────────────────────
    logger.info("\n[보강] 상황 컬럼 (is_home, 선발투수, 상대투수 투구손)")
    enriched = enrich_situation_columns(conn)
    logger.info("상황 컬럼 보강: %d건 UPDATE", enriched)

    conn.close()

    # ── Step 3: 시즌 재집계 ──────────────────────────────
    logger.info("\n[집계] 시즌 재집계 (시즌: %d)", args.season)
    aggregator = SeasonAggregator(loader.db_path)
    batter_count = aggregator.aggregate_batters(args.season)
    pitcher_count = aggregator.aggregate_pitchers(args.season)
    logger.info("시즌 재집계: 타자 %d명, 투수 %d명", batter_count, pitcher_count)

    # ── Step 4: 도루 재적용 ──────────────────────────────
    if not args.skip_scraper:
        logger.info("\n[도루] KBO 기록실 도루 크롤링 (시즌: %d)", args.season)
        try:
            team_map = build_team_name_to_id(loader.db_path)
            records = scrape_runner_stats(args.season)
            sb_updated, sb_failed = update_batter_season(
                loader.db_path, records, args.season, team_map
            )
            logger.info("도루 재적용: %d명 업데이트, %d명 실패", sb_updated, sb_failed)
        except Exception as exc:
            logger.error("도루 크롤링 실패 (건너뜀): %s", exc)
    else:
        logger.info("\n[도루] --skip-scraper 옵션으로 건너뜀")

    # ── 결과 요약 ────────────────────────────────────────
    logger.info("\n" + "=" * 50)
    logger.info("=== 완료 ===")
    logger.info(
        "  경기: 신규 %d경기, skip %d경기, 실패 %d경기",
        totals["new"], totals["skipped"], totals["failed"],
    )
    logger.info(
        "  기록: 타자 %d건, 투수 %d건",
        totals["batter_stats"], totals["pitcher_stats"],
    )
    logger.info("  보강: %d건", enriched)
    logger.info("  집계: 타자 %d명, 투수 %d명", batter_count, pitcher_count)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
