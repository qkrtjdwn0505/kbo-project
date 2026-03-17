"""누락 경기 선별 수집 — 더블헤더 보완

정규시즌 전 날짜의 KBO API 경기 목록과 DB를 비교하여
DB에 없는 경기(주로 수집 당시 미완료였던 더블헤더 경기)를 찾아 보완 수집.

매칭 전략:
  - (날짜, 홈팀, 원정팀, 홈스코어, 원정스코어) 조합으로 기존 레코드 식별
  - 새 결정론적 ID(game_id_to_int)로도 확인
  - 두 방법 모두 미일치 → 누락 경기로 판단, 수집

사용:
    python -m src.data.batch.collect_missing
"""

import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.loaders.db_loader import DBLoader
from src.data.batch.collect_season import (
    game_id_to_int,
    transform_game,
    transform_batters,
    transform_pitchers,
    load_existing_player_ids,
)

REGULAR_SEASON_START = "20250322"
REGULAR_SEASON_END   = "20251005"
DELAY = 0.5  # 요청 간 간격 (초)


def iter_dates(start_str: str, end_str: str):
    """YYYYMMDD 형식 날짜 순회"""
    def parse(s):
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    d, end_d = parse(start_str), parse(end_str)
    while d <= end_d:
        yield d.strftime("%Y%m%d")
        d += timedelta(days=1)


def game_already_in_db(
    conn,
    formatted_date: str,
    home_team_id: int,
    away_team_id: int,
    home_score: int,
    away_score: int,
    new_id: int,
) -> bool:
    """경기가 이미 DB에 있는지 확인.

    두 가지 방법으로 확인:
      1) 새 결정론적 ID — 이전에 collect_missing으로 수집한 경기
      2) (날짜, 팀, 스코어) 조합 — 기존 hash-based ID로 수집된 경기
    """
    if conn.execute("SELECT 1 FROM games WHERE id=?", (new_id,)).fetchone():
        return True
    row = conn.execute(
        """
        SELECT 1 FROM games
        WHERE date=? AND home_team_id=? AND away_team_id=?
          AND home_score=? AND away_score=? AND status='final'
        """,
        (formatted_date, home_team_id, away_team_id, home_score, away_score),
    ).fetchone()
    return row is not None


def collect_and_save(
    collector: KBODataCollector,
    loader: DBLoader,
    game_info: dict,
) -> bool:
    """단일 경기 수집 + DB 저장. 성공 여부 반환."""
    game = transform_game(game_info)

    boxscore = collector.get_boxscore(
        game_id=game_info["game_id"],
        sr_id=game_info.get("sr_id", 0),
        season=game_info.get("season", 2025),
    )
    if not boxscore:
        print(f"    [FAIL] 박스스코어 없음: {game_info['game_id']}")
        return False

    all_batter_stats: list[dict] = []
    all_pitcher_stats: list[dict] = []
    all_players: list[dict] = []

    for batters, team_id, is_home in [
        (boxscore["away_batters"], game_info["away_team_id"], False),
        (boxscore["home_batters"], game_info["home_team_id"], True),
    ]:
        b_stats, b_players = transform_batters(batters, game["id"], team_id, is_home)
        all_batter_stats.extend(b_stats)
        all_players.extend(b_players)

    for pitchers, team_id, is_home in [
        (boxscore["away_pitchers"], game_info["away_team_id"], False),
        (boxscore["home_pitchers"], game_info["home_team_id"], True),
    ]:
        p_stats, p_players = transform_pitchers(pitchers, game["id"], team_id, is_home)
        all_pitcher_stats.extend(p_stats)
        all_players.extend(p_players)

    seen: set[int] = set()
    unique_players = [p for p in all_players if not (p["id"] in seen or seen.add(p["id"]))]

    if unique_players:
        loader.load_players(unique_players)
    loader.load_games([game])
    if all_batter_stats:
        loader.load_batter_stats(all_batter_stats)
    if all_pitcher_stats:
        loader.load_pitcher_stats(all_pitcher_stats)

    away = game_info.get("away_team", "")
    home = game_info.get("home_team", "")
    print(
        f"    [OK] {game_info['game_id']}  DB id={game['id']}"
        f"  {away} {game_info.get('away_score')}-{game_info.get('home_score')} {home}"
        f"  타자={len(all_batter_stats)}건, 투수={len(all_pitcher_stats)}건"
    )
    return True


def main() -> None:
    collector = KBODataCollector(delay=DELAY)
    loader = DBLoader()
    conn = sqlite3.connect(loader.db_path)

    load_existing_player_ids(loader.db_path)

    missing_found = 0
    missing_saved = 0

    print(f"정규시즌 누락 경기 탐색: {REGULAR_SEASON_START} ~ {REGULAR_SEASON_END}")
    print(f"날짜당 API 1회 호출, ~198일 × {DELAY}초 ≈ {198*DELAY:.0f}초 소요 예상\n")

    for date_str in iter_dates(REGULAR_SEASON_START, REGULAR_SEASON_END):
        formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # 해당 날짜 API 경기 목록
        api_games = collector.get_game_list(date_str)
        final_games = [
            g for g in api_games
            if g.get("status_code") == "3"
            and g["home_team_id"] > 0
            and g["away_team_id"] > 0
        ]

        for game_info in final_games:
            new_id   = game_id_to_int(game_info["game_id"])
            h_score  = game_info.get("home_score") or 0
            a_score  = game_info.get("away_score") or 0

            if not game_already_in_db(
                conn, formatted,
                game_info["home_team_id"], game_info["away_team_id"],
                h_score, a_score, new_id,
            ):
                missing_found += 1
                away = game_info.get("away_team", "?")
                home = game_info.get("home_team", "?")
                print(f"\n누락 발견: {formatted}  {game_info['game_id']}  {away} vs {home}")
                ok = collect_and_save(collector, loader, game_info)
                if ok:
                    missing_saved += 1
                time.sleep(DELAY)

        time.sleep(DELAY)  # 날짜 간 간격

    conn.close()

    print(f"\n{'='*50}")
    print(f"탐색 완료")
    print(f"  누락 발견: {missing_found}경기")
    print(f"  수집 완료: {missing_saved}경기")
    if missing_found != missing_saved:
        print(f"  수집 실패: {missing_found - missing_saved}경기")


if __name__ == "__main__":
    main()
