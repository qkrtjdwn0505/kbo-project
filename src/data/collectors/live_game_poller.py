"""실시간 경기 폴링 수집기 — 2026 시즌 play-by-play 상황 데이터

GetKboGameList를 30초마다 폴링하여 타석별 주자 상황·점수차·이닝을 수집한다.
타자가 바뀔 때 이전 타자의 타석 상황을 at_bat_situations 테이블에 기록한다.
경기 종료 후 batter_stats 상황 컬럼(runners_on_scoring, score_diff, inning)을 업데이트한다.

실행:
    python -m src.data.collectors.live_game_poller              # 오늘 경기
    python -m src.data.collectors.live_game_poller --date 20260322
    python -m src.data.collectors.live_game_poller --daemon     # 하루 종일 실행
"""

import argparse
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from src.data.collectors.kbo_data_collector import KBODataCollector
from src.data.migrations.create_at_bat_situations import run as ensure_table

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"

# 폴링 간격
POLL_INTERVAL = 30       # 진행 중 경기: 30초
IDLE_INTERVAL = 300      # 경기 없는 시간: 5분
DAEMON_SLEEP = 3600      # 데몬 모드 경기 없는 날: 1시간


# ─── 상태 추적 ──────────────────────────────────────────────────────────


@dataclass
class GameState:
    """진행 중 경기 1건의 실시간 상태"""

    game_id: str
    home_team_id: int
    away_team_id: int

    current_batter: str = ""
    current_pitcher: str = ""
    current_inning: int = 1
    is_top_half: bool = True
    runners: list = field(default_factory=lambda: [False, False, False])
    home_score: int = 0
    away_score: int = 0
    out_count: int = 0
    at_bat_count: int = 0
    batting_team_id: int = 0
    pitching_team_id: int = 0
    score_diff_for_batter: int = 0

    def update(self, raw: dict) -> None:
        """GetKboGameList 원본 dict로 상태 갱신"""
        self.current_inning = int(raw.get("GAME_INN_NO") or 1)
        self.is_top_half = (raw.get("GAME_TB_SC", "T") == "T")
        self.runners = [
            int(raw.get("B1_BAT_ORDER_NO") or 0) > 0,
            int(raw.get("B2_BAT_ORDER_NO") or 0) > 0,
            int(raw.get("B3_BAT_ORDER_NO") or 0) > 0,
        ]
        self.home_score = int(raw.get("B_SCORE_CN") or 0)
        self.away_score = int(raw.get("T_SCORE_CN") or 0)
        self.out_count = int(raw.get("OUT_CN") or 0)

        # T_P_NM/B_P_NM 의미: T=원정, B=홈 → 초(is_top_half)엔 원정이 공격
        if self.is_top_half:
            self.current_batter = (raw.get("B_P_NM") or "").strip()   # 홈 투수가 아님 — 원정 타자
            self.current_pitcher = (raw.get("T_P_NM") or "").strip()
            self.batting_team_id = self.away_team_id
            self.pitching_team_id = self.home_team_id
            self.score_diff_for_batter = self.away_score - self.home_score
        else:
            self.current_batter = (raw.get("T_P_NM") or "").strip()   # 말: 홈 타자
            self.current_pitcher = (raw.get("B_P_NM") or "").strip()
            self.batting_team_id = self.home_team_id
            self.pitching_team_id = self.away_team_id
            self.score_diff_for_batter = self.home_score - self.away_score

    # ── 주의 ──────────────────────────────────────────────────────────────
    # KBO API에서 B_P_NM과 T_P_NM의 의미가 모호하게 문서화되어 있다.
    # 실제 응답을 보고 "현재 타자(B_P_NM)" / "현재 투수(T_P_NM)" 인지
    # 또는 "홈 대표선수 / 원정 대표선수" 인지 확인 후 update()를 수정해야 한다.
    # 2026 시즌 첫 경기 폴링 후 로그로 검증 필요.


# ─── 메인 폴러 ──────────────────────────────────────────────────────────


class LiveGamePoller:
    """KBO 실시간 경기 폴러"""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self.collector = KBODataCollector(delay=0.5)
        self.active_games: dict[str, GameState] = {}
        ensure_table(db_path)

    # ── 메인 루프 ──────────────────────────────────────────────────────

    def run(self, date_str: Optional[str] = None, daemon: bool = False) -> None:
        """폴링 메인 루프

        Args:
            date_str: "YYYYMMDD". None이면 오늘.
            daemon: True면 하루 종일 실행 (경기 없으면 IDLE_INTERVAL 대기).
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")

        logger.info("폴링 시작: %s daemon=%s", date_str, daemon)

        while True:
            games = self.collector.get_game_list(date_str)
            live = [g for g in games if g["status_code"] == "2"]
            done = [g for g in games if g["status_code"] == "3"]

            if live:
                for g in live:
                    self._process(g)
                logger.info("[%s] 진행 중 %d경기, %ds 후 재폴링", date_str, len(live), POLL_INTERVAL)
                time.sleep(POLL_INTERVAL)

            elif done and not live:
                # 오늘 경기 전부 종료
                logger.info("[%s] 모든 경기 종료 — 마무리 처리 시작", date_str)
                self._finalize(date_str)
                if daemon:
                    # 다음 날까지 대기
                    logger.info("데몬 모드: 다음 경기 날까지 대기")
                    time.sleep(DAEMON_SLEEP)
                    date_str = datetime.now().strftime("%Y%m%d")
                    self.active_games.clear()
                else:
                    break

            else:
                # 경기 없거나 아직 시작 전
                if daemon:
                    logger.debug("경기 없음 — %ds 후 재확인", IDLE_INTERVAL)
                    time.sleep(IDLE_INTERVAL)
                    date_str = datetime.now().strftime("%Y%m%d")
                else:
                    logger.info("[%s] 진행 중 경기 없음. 종료.", date_str)
                    break

    # ── 단일 경기 처리 ──────────────────────────────────────────────────

    def _process(self, raw: dict) -> None:
        """진행 중 경기 1건: 타자 변경 감지 → 타석 기록"""
        game_id: str = raw["game_id"]

        if game_id not in self.active_games:
            self.active_games[game_id] = GameState(
                game_id=game_id,
                home_team_id=raw["home_team_id"],
                away_team_id=raw["away_team_id"],
            )

        state = self.active_games[game_id]
        prev_batter = state.current_batter

        # 상태 갱신 전에 이전 타자 저장
        state.update(raw)
        new_batter = state.current_batter

        if not new_batter:
            return

        # 타자가 바뀐 경우 → 이전 타자의 타석 완료
        if prev_batter and prev_batter != new_batter:
            self._record(game_id, prev_batter, state)

    def _record(self, game_id: str, batter_name: str, state: GameState) -> None:
        """at_bat_situations에 타석 1건 INSERT"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO at_bat_situations
                  (game_id, inning, is_top_half,
                   batter_name, batter_team_id,
                   pitcher_name, pitcher_team_id,
                   runners_on_1b, runners_on_2b, runners_on_3b, runners_on_scoring,
                   home_score, away_score, score_diff, out_count, at_bat_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    state.current_inning,
                    state.is_top_half,
                    batter_name,
                    state.batting_team_id,
                    state.current_pitcher,
                    state.pitching_team_id,
                    state.runners[0],
                    state.runners[1],
                    state.runners[2],
                    state.runners[1] or state.runners[2],
                    state.home_score,
                    state.away_score,
                    state.score_diff_for_batter,
                    state.out_count,
                    state.at_bat_count,
                ),
            )
            conn.commit()
            logger.debug(
                "[%s] 타석 기록: %s 이닝=%d 주자=%s 점수차=%+d",
                game_id, batter_name, state.current_inning,
                "".join(["1" if r else "0" for r in state.runners]),
                state.score_diff_for_batter,
            )
        finally:
            conn.close()

        state.at_bat_count += 1

    # ── 종료 후 처리 ────────────────────────────────────────────────────

    def _finalize(self, date_str: str) -> None:
        """경기 종료 후 at_bat_situations → batter_stats 반영

        1. game_id → game_int_id(DB games.id) 매핑
        2. batter_name → player_id 매핑
        3. batter_stats 상황 컬럼 UPDATE
        """
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        conn = sqlite3.connect(self.db_path)
        try:
            # ① game_int_id 매핑 (아직 NULL인 것만)
            game_rows = conn.execute(
                """
                SELECT DISTINCT a.game_id, g.id
                FROM at_bat_situations a
                JOIN games g ON g.date = ?
                    AND (g.home_team_id = a.batter_team_id OR g.away_team_id = a.batter_team_id)
                WHERE a.game_int_id IS NULL
                  AND a.game_id LIKE ?
                """,
                (formatted_date, f"{date_str}%"),
            ).fetchall()

            for kbo_gid, int_id in game_rows:
                conn.execute(
                    "UPDATE at_bat_situations SET game_int_id = ? WHERE game_id = ? AND game_int_id IS NULL",
                    (int_id, kbo_gid),
                )
            conn.commit()
            logger.info("game_int_id 매핑: %d경기", len(game_rows))

            # ② 집계: game별 선수별 상황 요약
            rows = conn.execute(
                """
                SELECT
                    a.game_int_id,
                    p.id AS player_id,
                    MAX(a.runners_on_scoring) AS had_risp,
                    AVG(a.score_diff)         AS avg_diff,
                    MIN(a.inning)             AS first_inning
                FROM at_bat_situations a
                JOIN players p ON p.name = a.batter_name
                WHERE a.game_int_id IS NOT NULL
                  AND a.game_id LIKE ?
                GROUP BY a.game_int_id, p.id
                """,
                (f"{date_str}%",),
            ).fetchall()

            updated = 0
            for game_int_id, player_id, had_risp, avg_diff, first_inning in rows:
                if game_int_id is None:
                    continue
                score_diff = round(avg_diff) if avg_diff is not None else None
                res = conn.execute(
                    """
                    UPDATE batter_stats
                    SET runners_on_scoring = ?,
                        score_diff         = COALESCE(score_diff, ?),
                        inning             = COALESCE(inning, ?)
                    WHERE game_id = ? AND player_id = ?
                    """,
                    (bool(had_risp), score_diff, first_inning, game_int_id, player_id),
                )
                updated += res.rowcount

            conn.commit()
            logger.info("batter_stats 업데이트: %d행", updated)

        finally:
            conn.close()

    # ── 시뮬레이션 테스트 ────────────────────────────────────────────────

    def test_with_finished_game(self, date_str: str) -> None:
        """종료 경기로 구조 테스트 (실제 라이브 없을 때)

        GetKboGameList를 호출해 종료 경기 목록을 출력하고
        마지막 상태의 타자/투수 필드를 확인한다.
        """
        print(f"\n[TEST] {date_str} 경기 목록 조회")
        games = self.collector.get_game_list(date_str)
        if not games:
            print("  경기 없음")
            return

        for g in games:
            status = {"1": "예정", "2": "진행중", "3": "종료", "4": "취소"}.get(g["status_code"], "?")
            print(
                f"  {g['game_id']} {g['away_team']}@{g['home_team']} "
                f"{g['away_score']}-{g['home_score']} [{status}]"
            )

        # 종료 경기 1건으로 필드 확인
        finished = [g for g in games if g["status_code"] == "3"]
        if finished:
            sample = finished[0]
            print(f"\n[TEST] 샘플 raw 필드 (game_id={sample['game_id']}):")
            for k in ("GAME_INN_NO", "GAME_TB_SC", "OUT_CN",
                      "B1_BAT_ORDER_NO", "B2_BAT_ORDER_NO", "B3_BAT_ORDER_NO",
                      "T_SCORE_CN", "B_SCORE_CN", "T_P_NM", "B_P_NM"):
                # raw는 collector 내부에서 정규화되므로 API를 직접 재호출
                pass
            print("  (raw 필드 확인은 collector._request 직접 호출로만 가능)")
            print(f"  정규화된 필드: {sample}")

        # at_bat_situations 저장 테스트
        print("\n[TEST] at_bat_situations INSERT 테스트")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT OR IGNORE INTO at_bat_situations
              (game_id, inning, is_top_half, batter_name, pitcher_name,
               runners_on_scoring, score_diff, at_bat_order)
            VALUES ('TEST_GAME_001', 5, 1, '테스트타자', '테스트투수', 1, -1, 0)
            """
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM at_bat_situations WHERE game_id='TEST_GAME_001'"
        ).fetchone()
        conn.execute("DELETE FROM at_bat_situations WHERE game_id='TEST_GAME_001'")
        conn.commit()
        conn.close()
        print(f"  INSERT/SELECT/DELETE 정상: {row[:6]}...")
        print("[TEST] 완료\n")


# ─── 진입점 ─────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="KBO 실시간 폴링 수집기")
    parser.add_argument("--date", help="날짜 YYYYMMDD (기본: 오늘)")
    parser.add_argument("--daemon", action="store_true", help="하루 종일 실행")
    parser.add_argument("--test", metavar="DATE", help="종료 경기로 구조 테스트 (예: 20250930)")
    args = parser.parse_args()

    poller = LiveGamePoller()

    if args.test:
        poller.test_with_finished_game(args.test)
    else:
        poller.run(date_str=args.date, daemon=args.daemon)


if __name__ == "__main__":
    main()
