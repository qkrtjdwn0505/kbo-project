"""DB 저장 — 수집 데이터를 SQLite에 upsert"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"


class DBLoader:
    """수집 데이터를 DB에 저장하는 로더"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def load_players(self, players: list[dict]) -> int:
        """선수 데이터 upsert"""
        conn = self._connect()
        cursor = conn.cursor()
        count = 0

        for p in players:
            cursor.execute("""
                INSERT INTO players (id, name, team_id, position, position_detail,
                    back_number, birth_date, height, weight, bat_hand, throw_hand, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, team_id=excluded.team_id,
                    position=excluded.position, position_detail=excluded.position_detail,
                    back_number=excluded.back_number, is_active=excluded.is_active
            """, (
                p["id"], p["name"], p["team_id"], p["position"],
                p.get("position_detail"), p.get("back_number"),
                p.get("birth_date"), p.get("height"), p.get("weight"),
                p.get("bat_hand"), p.get("throw_hand"), p.get("is_active", True),
            ))
            count += 1

        conn.commit()
        conn.close()
        logger.info(f"선수 {count}명 저장 완료")
        return count

    def load_games(self, games: list[dict]) -> int:
        """경기 데이터 upsert"""
        conn = self._connect()
        cursor = conn.cursor()
        count = 0

        for g in games:
            cursor.execute("""
                INSERT INTO games (id, date, time, stadium, home_team_id, away_team_id,
                    home_score, away_score, status, day_of_week, is_night_game)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    home_score=excluded.home_score, away_score=excluded.away_score,
                    status=excluded.status
            """, (
                g["id"], g["date"], g.get("time"), g.get("stadium"),
                g["home_team_id"], g["away_team_id"],
                g.get("home_score"), g.get("away_score"),
                g.get("status", "final"), g.get("day_of_week"), g.get("is_night_game"),
            ))
            count += 1

        conn.commit()
        conn.close()
        logger.info(f"경기 {count}건 저장 완료")
        return count

    def load_batter_stats(self, stats: list[dict]) -> int:
        """타자 경기별 기록 저장"""
        conn = self._connect()
        cursor = conn.cursor()
        count = 0

        for s in stats:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO batter_stats
                    (game_id, player_id, team_id, pa, ab, hits, doubles, triples,
                     hr, rbi, runs, sb, cs, bb, hbp, so, gdp, sf, ibb,
                     runners_on_scoring, opponent_pitcher_hand, is_home, score_diff)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s["game_id"], s["player_id"], s["team_id"],
                    s.get("pa", 0), s.get("ab", 0), s.get("hits", 0),
                    s.get("doubles", 0), s.get("triples", 0), s.get("hr", 0),
                    s.get("rbi", 0), s.get("runs", 0), s.get("sb", 0),
                    s.get("cs", 0), s.get("bb", 0), s.get("hbp", 0),
                    s.get("so", 0), s.get("gdp", 0), s.get("sf", 0),
                    s.get("ibb", 0),
                    s.get("runners_on_scoring"), s.get("opponent_pitcher_hand"),
                    s.get("is_home"), s.get("score_diff"),
                ))
                count += 1
            except sqlite3.IntegrityError as e:
                logger.warning(f"타자 기록 중복: {s['player_id']} game {s['game_id']} - {e}")

        conn.commit()
        conn.close()
        logger.info(f"타자 기록 {count}건 저장 완료")
        return count

    def load_pitcher_stats(self, stats: list[dict]) -> int:
        """투수 경기별 기록 저장"""
        conn = self._connect()
        cursor = conn.cursor()
        count = 0

        for s in stats:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO pitcher_stats
                    (game_id, player_id, team_id, ip_outs, hits_allowed, hr_allowed,
                     bb_allowed, hbp_allowed, so_count, runs_allowed, er,
                     is_starter, decision, batter_hand, is_home)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s["game_id"], s["player_id"], s["team_id"],
                    s.get("ip_outs", 0), s.get("hits_allowed", 0),
                    s.get("hr_allowed", 0), s.get("bb_allowed", 0),
                    s.get("hbp_allowed", 0), s.get("so_count", 0),
                    s.get("runs_allowed", 0), s.get("er", 0),
                    s.get("is_starter"), s.get("decision"),
                    s.get("batter_hand"), s.get("is_home"),
                ))
                count += 1
            except sqlite3.IntegrityError as e:
                logger.warning(f"투수 기록 중복: {s['player_id']} game {s['game_id']} - {e}")

        conn.commit()
        conn.close()
        logger.info(f"투수 기록 {count}건 저장 완료")
        return count

    def get_stats(self) -> dict:
        """DB 현황 통계"""
        conn = self._connect()
        cursor = conn.cursor()
        stats = {}
        for table in ["players", "games", "batter_stats", "pitcher_stats",
                       "batter_season", "pitcher_season"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        conn.close()
        return stats
