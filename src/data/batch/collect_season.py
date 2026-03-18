"""KBO 정규시즌 데이터 벌크 수집 스크립트

수집 범위: 지정 연도 4월 ~ 10월 정규시즌
수집 대상: 경기 목록 + 박스스코어 (타자/투수 기록)
저장: SQLite DB (db_loader 사용)
Rate limiting: 요청 간 1초 간격

2025 KBO 홈페이지 개편 대응:
  - GetKboGameList → 날짜별 경기 목록 (JSON, 팀/스코어/선발투수 포함)
  - GetBoxScoreScroll → 박스스코어 (arrHitter/arrPitcher JSON)
  - 파라미터: leId, srId, seasonId, gameId

사용법:
    python -m src.data.batch.collect_season --year 2025
    python -m src.data.batch.collect_season --year 2025 --month 4
    python -m src.data.batch.collect_season --year 2025 --resume
    python -m src.data.batch.collect_season --year 2025 --retry-failed
"""

import argparse
import calendar
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.loaders.db_loader import DBLoader
from src.data.processors.at_bat_parser import parse_player_innings

# --- 로깅 설정 ---
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# --- 상수 ---
DEFAULT_YEAR = 2025
START_MONTH = 1
END_MONTH = 12

# KBO 팀 영문코드 → team_id (KBODataCollector.TEAM_CODE_TO_ID와 동일)
_TEAM_CODE_TO_INT: dict[str, int] = {
    "HT": 1, "SS": 2, "LG": 3, "OB": 4, "KT": 5,
    "SK": 6, "LT": 7, "HH": 8, "NC": 9, "WO": 10,
}

# KBO API sr_id → game_type 매핑
SR_ID_MAP: dict[int, str] = {
    0: "regular",
    1: "preseason",
    3: "postseason",   # 와일드카드
    4: "postseason",   # 준플레이오프
    5: "postseason",   # 플레이오프
    7: "postseason",   # 한국시리즈
    9: "postseason",   # 기타 포스트시즌
}


def game_id_to_int(game_id: str) -> int:
    """KBO API 경기 ID → 충돌 없는 결정론적 정수 변환.

    기존 abs(hash(game_id)) % 10^9 방식의 두 가지 문제를 해결:
      1) PYTHONHASHSEED 비결정성 — 실행마다 다른 ID 생성
      2) 더블헤더 충돌 — 같은 날 같은 팀의 두 경기가 같은 ID로 매핑될 가능성

    인코딩: date(8자리) × 10000 + away_id × 100 + home_id × 10 + seq
    예: "20250510LGSS1" → 20250510 × 10000 + 3×100 + 2×10 + 1 = 202505100321
        "20250510LGSS2" → 202505100322  ← 다른 ID 보장

    새 ID 범위(~2×10^11)는 기존 hash-기반 ID 범위(~10^9)와 완전히 분리되어
    기존 DB 레코드를 건드리지 않음.
    """
    if len(game_id) >= 13:
        try:
            date_part = int(game_id[:8])    # 20250510
            away_code = game_id[8:10]       # "LG"
            home_code = game_id[10:12]      # "SS"
            seq = int(game_id[12])          # 1
            away_id = _TEAM_CODE_TO_INT.get(away_code, 0)
            home_id = _TEAM_CODE_TO_INT.get(home_code, 0)
            if away_id > 0 and home_id > 0:
                return date_part * 10000 + away_id * 100 + home_id * 10 + seq
        except (ValueError, IndexError):
            pass
    # 폴백: SHA-1 기반 (팀 코드 매핑 실패 시) — 기존/신규 범위와 겹치지 않는 큰 수
    import hashlib
    return int(hashlib.sha1(game_id.encode()).hexdigest()[:16], 16)

# 선수 ID 자동 생성용 캐시 (이름+팀 기반)
_player_id_cache: dict[str, int] = {}
_next_player_id = 1000

# 모듈 레벨 logger
logger = logging.getLogger("collect_season")


def setup_logging(year: int) -> None:
    """연도별 로그 파일 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(
                LOG_DIR / f"collect_{year}.log", encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )


def progress_file(year: int) -> Path:
    """연도별 진행 상황 파일 경로"""
    return LOG_DIR / f"collect_{year}_progress.json"


def get_or_create_player_id(name: str, team_id: int) -> int:
    """선수 이름+팀으로 고유 ID 생성 (동명이인은 팀으로 구분)"""
    global _next_player_id
    key = f"{name}_{team_id}"
    if key not in _player_id_cache:
        _player_id_cache[key] = _next_player_id
        _next_player_id += 1
    return _player_id_cache[key]


def load_existing_player_ids(db_path: str) -> None:
    """DB에 이미 있는 선수 ID를 캐시에 로드"""
    global _next_player_id
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, team_id FROM players")
    for pid, name, tid in cursor.fetchall():
        key = f"{name}_{tid}"
        _player_id_cache[key] = pid
    if _player_id_cache:
        _next_player_id = max(_player_id_cache.values()) + 1
    conn.close()
    logger.info("기존 선수 %d명 캐시 로드 완료", len(_player_id_cache))


def get_day_of_week(date_str: str) -> str:
    """날짜 → 요일 (한글)"""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return days[d.weekday()]
    except ValueError:
        return ""


def is_night_game(time_str: str) -> bool:
    """야간 경기 여부 (17시 이후)"""
    if not time_str:
        return True
    try:
        hour = int(time_str.split(":")[0])
        return hour >= 17
    except (ValueError, IndexError):
        return True


def load_progress(year: int) -> dict:
    """이전 수집 진행 상황 로드"""
    path = progress_file(year)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"year": year, "completed_dates": [], "failed_dates": [], "stats": {}}


def save_progress(year: int, progress: dict) -> None:
    """수집 진행 상황 저장"""
    with open(progress_file(year), "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ─── 데이터 변환 ────────────────────────────────────────


def transform_game(game_info: dict) -> dict:
    """GetKboGameList 정규화 데이터 → DB games 형식"""
    game_id = game_info["game_id"]
    # 결정론적 인코딩 — hash() 비결정성 및 더블헤더 충돌 문제 해결
    numeric_id = game_id_to_int(game_id)

    return {
        "id": numeric_id,
        "date": game_info["date"],
        "time": game_info.get("time", ""),
        "stadium": game_info.get("stadium", ""),
        "home_team_id": game_info["home_team_id"],
        "away_team_id": game_info["away_team_id"],
        "home_score": game_info.get("home_score", 0),
        "away_score": game_info.get("away_score", 0),
        "status": "final" if game_info.get("status_code") == "3" else "scheduled",
        "day_of_week": get_day_of_week(game_info["date"]),
        "is_night_game": is_night_game(game_info.get("time", "")),
        "game_type": SR_ID_MAP.get(game_info.get("sr_id", 0), "regular"),
    }


def transform_batters(
    batters: list[dict], game_id: int, team_id: int, is_home: bool
) -> tuple[list[dict], list[dict]]:
    """박스스코어 타자 데이터 → DB batter_stats + players 형식

    table2(이닝별 타석 결과)를 at_bat_parser로 파싱하여
    2B/3B/HR/BB/HBP/SO/SF/GDP/IBB 상세 기록을 추출한다.
    rbi, runs는 table3에서 가져온다 (table2에 없는 정보).

    Args:
        batters: collector.get_boxscore()["away_batters"] 또는 ["home_batters"]
                 각 항목에 "inning_codes" 필드가 추가됨.
    """
    stats_list: list[dict] = []
    players_list: list[dict] = []

    for batter in batters:
        name = batter.get("name", "").strip()
        if not name:
            continue

        player_id = get_or_create_player_id(name, team_id)

        players_list.append({
            "id": player_id,
            "name": name,
            "team_id": team_id,
            "position": batter.get("position", "타자"),
            "position_detail": batter.get("position", ""),
            "is_active": True,
        })

        # table2 파싱으로 상세 기록 추출
        inning_codes = batter.get("inning_codes", [])
        if inning_codes:
            parsed = parse_player_innings(inning_codes)
            pa = parsed.pa
            ab = parsed.ab
            hits = parsed.hits
            doubles = parsed.doubles
            triples = parsed.triples
            hr = parsed.hr
            bb = parsed.bb
            ibb = parsed.ibb
            hbp = parsed.hbp
            so = parsed.so
            sf = parsed.sf
            gdp = parsed.gdp
            sb = parsed.sb
            cs = parsed.cs
        else:
            # table2 없는 경우 (예외) — table3 폴백
            ab = batter.get("ab", 0)
            hits = batter.get("hits", 0)
            pa = ab  # 근사값
            doubles = 0
            triples = 0
            hr = 0
            bb = 0
            ibb = 0
            hbp = 0
            so = 0
            sf = 0
            gdp = 0
            sb = 0
            cs = 0

        # rbi, runs는 table3에서 (table2에 없는 정보)
        rbi = batter.get("rbi", 0)
        runs = batter.get("runs", 0)

        stats_list.append({
            "game_id": game_id,
            "player_id": player_id,
            "team_id": team_id,
            "pa": pa,
            "ab": ab,
            "hits": hits,
            "doubles": doubles,
            "triples": triples,
            "hr": hr,
            "rbi": rbi,
            "runs": runs,
            "sb": sb,
            "cs": cs,
            "bb": bb,
            "ibb": ibb,
            "hbp": hbp,
            "so": so,
            "gdp": gdp,
            "sf": sf,
            "is_home": is_home,
        })

    return stats_list, players_list


def transform_pitchers(
    pitchers: list[dict], game_id: int, team_id: int, is_home: bool
) -> tuple[list[dict], list[dict]]:
    """박스스코어 투수 데이터 → DB pitcher_stats + players 형식

    Args:
        pitchers: collector.get_boxscore()["away_pitchers"] 또는 ["home_pitchers"]
                  각 항목: {name, entry, decision, wins, losses, saves, ip, bf, np,
                           ab, hits_allowed, hr_allowed, bb_allowed, so_count,
                           runs_allowed, er, era}
    """
    stats_list: list[dict] = []
    players_list: list[dict] = []

    for i, pitcher in enumerate(pitchers):
        name = pitcher.get("name", "").strip()
        if not name:
            continue

        player_id = get_or_create_player_id(name, team_id)
        is_starter = pitcher.get("entry") == "선발"

        players_list.append({
            "id": player_id,
            "name": name,
            "team_id": team_id,
            "position": "투수",
            "position_detail": "선발" if is_starter else "불펜",
            "is_active": True,
        })

        stats_list.append({
            "game_id": game_id,
            "player_id": player_id,
            "team_id": team_id,
            "ip_outs": KBODataCollector.parse_ip_to_outs(pitcher.get("ip", "0")),
            "hits_allowed": pitcher.get("hits_allowed", 0),
            "hr_allowed": pitcher.get("hr_allowed", 0),
            "bb_allowed": pitcher.get("bb_allowed", 0),
            "hbp_allowed": 0,
            "so_count": pitcher.get("so_count", 0),
            "runs_allowed": pitcher.get("runs_allowed", 0),
            "er": pitcher.get("er", 0),
            "is_starter": is_starter,
            "decision": pitcher.get("decision") or None,
            "is_home": is_home,
        })

    return stats_list, players_list


# ─── 수집 로직 ──────────────────────────────────────────


def collect_date(
    collector: KBODataCollector,
    loader: DBLoader,
    date_str: str,
) -> dict:
    """단일 날짜 수집 + DB 저장

    Args:
        date_str: "YYYYMMDD" 형식

    Returns:
        {"games": int, "batters": int, "pitchers": int, "players": int}
    """
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    result = {"games": 0, "batters": 0, "pitchers": 0, "players": 0}

    # 1. 경기 목록 수집 (새 API: GetKboGameList)
    game_list = collector.get_game_list(date_str)
    if not game_list:
        return result

    all_games: list[dict] = []
    all_players: list[dict] = []
    all_batter_stats: list[dict] = []
    all_pitcher_stats: list[dict] = []

    for game_info in game_list:
        # 팀 매핑 확인
        if game_info["home_team_id"] == 0 or game_info["away_team_id"] == 0:
            logger.warning(
                "팀 매핑 실패로 건너뜀: %s home=%s away=%s",
                formatted_date, game_info.get("home_code"), game_info.get("away_code"),
            )
            continue

        # 취소 경기 건너뛰기
        if game_info.get("status_code") == "4":
            logger.debug("취소 경기: %s %s", formatted_date, game_info["game_id"])
            continue

        game = transform_game(game_info)
        all_games.append(game)

        # 종료된 경기만 박스스코어 수집 (status_code "3" = 경기 종료)
        if game_info.get("status_code") != "3":
            continue

        # 2. 박스스코어 수집 (새 API: GetBoxScoreScroll)
        boxscore = collector.get_boxscore(
            game_id=game_info["game_id"],
            sr_id=game_info.get("sr_id", 0),
            season=game_info.get("season", int(date_str[:4])),
        )
        if not boxscore:
            logger.warning("박스스코어 수집 실패: %s", game_info["game_id"])
            continue

        # 원정팀 타자/투수
        b_stats, b_players = transform_batters(
            boxscore["away_batters"], game["id"],
            game_info["away_team_id"], is_home=False,
        )
        all_batter_stats.extend(b_stats)
        all_players.extend(b_players)

        p_stats, p_players = transform_pitchers(
            boxscore["away_pitchers"], game["id"],
            game_info["away_team_id"], is_home=False,
        )
        all_pitcher_stats.extend(p_stats)
        all_players.extend(p_players)

        # 홈팀 타자/투수
        b_stats, b_players = transform_batters(
            boxscore["home_batters"], game["id"],
            game_info["home_team_id"], is_home=True,
        )
        all_batter_stats.extend(b_stats)
        all_players.extend(b_players)

        p_stats, p_players = transform_pitchers(
            boxscore["home_pitchers"], game["id"],
            game_info["home_team_id"], is_home=True,
        )
        all_pitcher_stats.extend(p_stats)
        all_players.extend(p_players)

    # 3. DB 저장
    if all_players:
        seen: set[int] = set()
        unique: list[dict] = []
        for p in all_players:
            if p["id"] not in seen:
                seen.add(p["id"])
                unique.append(p)
        result["players"] = loader.load_players(unique)

    if all_games:
        result["games"] = loader.load_games(all_games)

    if all_batter_stats:
        result["batters"] = loader.load_batter_stats(all_batter_stats)

    if all_pitcher_stats:
        result["pitchers"] = loader.load_pitcher_stats(all_pitcher_stats)

    return result


def collect_season(
    year: int = DEFAULT_YEAR,
    start_month: int = START_MONTH,
    end_month: int = END_MONTH,
    start_day: int = 1,
    resume: bool = False,
) -> None:
    """KBO 정규시즌 전체 수집"""
    setup_logging(year)

    collector = KBODataCollector(delay=1.0)
    loader = DBLoader()

    load_existing_player_ids(loader.db_path)

    progress = load_progress(year) if resume else {
        "year": year, "completed_dates": [], "failed_dates": [], "stats": {},
    }
    completed_set = set(progress["completed_dates"])

    totals = {
        "games": 0, "batters": 0, "pitchers": 0, "players": 0,
        "dates_processed": 0, "dates_skipped": 0, "dates_failed": 0,
    }

    start_time = time.time()
    logger.info("=" * 60)
    logger.info("%d KBO 정규시즌 수집 시작: %d월 ~ %d월", year, start_month, end_month)
    if resume:
        logger.info("재개 모드: %d일 이미 완료", len(completed_set))
    logger.info("=" * 60)

    for month in range(start_month, end_month + 1):
        days_in_month = calendar.monthrange(year, month)[1]
        logger.info("\n--- %d년 %d월 (%d일) ---", year, month, days_in_month)
        month_games = 0

        first_day = start_day if month == start_month else 1
        for day in range(first_day, days_in_month + 1):
            date_str = f"{year}{month:02d}{day:02d}"

            if date_str in completed_set:
                totals["dates_skipped"] += 1
                continue

            try:
                result = collect_date(collector, loader, date_str)
                totals["games"] += result["games"]
                totals["batters"] += result["batters"]
                totals["pitchers"] += result["pitchers"]
                totals["players"] += result["players"]
                totals["dates_processed"] += 1
                month_games += result["games"]

                progress["completed_dates"].append(date_str)
                completed_set.add(date_str)

                if result["games"] > 0:
                    logger.info(
                        "  %s: %d경기, 타자 %d건, 투수 %d건",
                        date_str, result["games"],
                        result["batters"], result["pitchers"],
                    )

            except Exception as e:
                logger.error("  %s: 수집 실패 - %s", date_str, e)
                progress["failed_dates"].append(date_str)
                totals["dates_failed"] += 1

            if day % 10 == 0:
                save_progress(year, progress)

        logger.info("  %d월 완료: %d경기 수집", month, month_games)
        save_progress(year, progress)

    elapsed = time.time() - start_time
    progress["stats"] = {
        "total_games": totals["games"],
        "total_batters": totals["batters"],
        "total_pitchers": totals["pitchers"],
        "total_players": totals["players"],
        "completed_at": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
    }
    save_progress(year, progress)

    db_stats = loader.get_stats()

    logger.info("\n" + "=" * 60)
    logger.info("수집 완료!")
    logger.info("  시즌: %d", year)
    logger.info("  소요 시간: %.1f분", elapsed / 60)
    logger.info(
        "  처리 일수: %d일 (건너뜀 %d일, 실패 %d일)",
        totals["dates_processed"], totals["dates_skipped"], totals["dates_failed"],
    )
    logger.info("  수집 경기: %d건", totals["games"])
    logger.info("  수집 타자 기록: %d건", totals["batters"])
    logger.info("  수집 투수 기록: %d건", totals["pitchers"])
    logger.info("  등록 선수: %d명", totals["players"])
    logger.info("\nDB 현황:")
    for table, count in db_stats.items():
        logger.info("  %s: %d건", table, count)
    logger.info("=" * 60)


def retry_failed(year: int) -> None:
    """이전 실행에서 실패한 날짜만 재시도"""
    setup_logging(year)

    path = progress_file(year)
    if not path.exists():
        logger.info("%d년 진행 파일이 없습니다.", year)
        return

    with open(path, "r", encoding="utf-8") as f:
        progress = json.load(f)

    failed = progress.get("failed_dates", [])
    if not failed:
        logger.info("재시도할 실패 날짜가 없습니다.")
        return

    logger.info("%d년 실패 날짜 %d일 재시도 시작", year, len(failed))
    collector = KBODataCollector(delay=1.0)
    loader = DBLoader()
    load_existing_player_ids(loader.db_path)

    newly_completed: list[str] = []
    still_failed: list[str] = []

    for date_str in failed:
        try:
            result = collect_date(collector, loader, date_str)
            newly_completed.append(date_str)
            logger.info("  %s: 재시도 성공 - %d경기", date_str, result["games"])
        except Exception as e:
            still_failed.append(date_str)
            logger.error("  %s: 재시도 실패 - %s", date_str, e)

    progress["completed_dates"].extend(newly_completed)
    progress["failed_dates"] = still_failed
    save_progress(year, progress)

    logger.info(
        "재시도 완료: 성공 %d일, 여전히 실패 %d일",
        len(newly_completed), len(still_failed),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="KBO 정규시즌 데이터 수집")
    parser.add_argument(
        "--year", type=int, default=DEFAULT_YEAR,
        help=f"수집 시즌 연도 (기본: {DEFAULT_YEAR})",
    )
    parser.add_argument(
        "--month", type=int, default=0,
        help="특정 월만 수집 (예: 4). 미지정 시 전체",
    )
    parser.add_argument(
        "--start-month", type=int, default=0,
        help="수집 시작 월 (예: 3)",
    )
    parser.add_argument(
        "--end-month", type=int, default=0,
        help="수집 종료 월 (예: 10)",
    )
    parser.add_argument(
        "--start-day", type=int, default=1,
        help="시작 월의 시작 일 (예: 22 → 시작월 22일부터)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="이전 진행 상황에서 재개",
    )
    parser.add_argument(
        "--retry-failed", action="store_true",
        help="이전 실행에서 실패한 날짜만 재시도",
    )
    args = parser.parse_args()

    if args.retry_failed:
        retry_failed(args.year)
    elif args.month:
        collect_season(
            year=args.year,
            start_month=args.month,
            end_month=args.month,
            start_day=args.start_day,
            resume=args.resume,
        )
    elif args.start_month:
        collect_season(
            year=args.year,
            start_month=args.start_month,
            end_month=args.end_month or END_MONTH,
            start_day=args.start_day,
            resume=args.resume,
        )
    else:
        collect_season(year=args.year, resume=args.resume)


if __name__ == "__main__":
    main()
