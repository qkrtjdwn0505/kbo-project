"""시즌 집계 + 세이버메트릭스 계산 → DB 저장

경기별 기록(batter_stats, pitcher_stats)을 시즌 단위로 집계하고,
세이버메트릭스를 계산하여 batter_season, pitcher_season 테이블에 저장합니다.

사용법:
    python -m src.data.processors.season_aggregator --season 2025

    또는 코드에서:
        aggregator = SeasonAggregator("kbo.db")
        aggregator.aggregate_batters(2025)
        aggregator.aggregate_pitchers(2025)
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from src.data.processors.sabermetrics_engine import (
    LeagueConstants,
    calc_avg,
    calc_obp,
    calc_slg,
    calc_ops,
    calc_iso,
    calc_babip,
    calc_bb_pct,
    calc_k_pct,
    calc_woba,
    calc_wrc_plus,
    calc_batter_war_simplified,
    calc_era,
    calc_whip,
    calc_fip,
    calc_xfip,
    calc_per_9,
    calc_k_bb_ratio,
    calc_pitcher_babip,
    calc_pitcher_war_simplified,
)

logger = logging.getLogger(__name__)

# DB 기본 경로
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"

# 2025 KBO 리그 상수 기본값 (추후 KBReport에서 실측값으로 교체)
DEFAULT_LC = LeagueConstants(
    season=2025,
    w_bb=0.69, w_hbp=0.72, w_1b=0.89,
    w_2b=1.27, w_3b=1.62, w_hr=2.10,
    woba_scale=1.15,
    league_woba=0.320,
    league_obp=0.340,
    rppa=0.12,
    league_rpw=10.0,
    league_r_pa=0.12,
    fip_constant=3.10,
    league_hr_fb_rate=0.10,
)


class SeasonAggregator:
    """시즌 집계 + 세이버메트릭스 계산기"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DEFAULT_DB_PATH)

    def _get_league_constants(
        self, conn: sqlite3.Connection, season: int,
    ) -> LeagueConstants:
        """league_constants 테이블에서 리그 상수 로드, 없으면 기본값"""
        cursor = conn.execute(
            "SELECT * FROM league_constants WHERE season = ?", (season,),
        )
        row = cursor.fetchone()
        if row:
            return LeagueConstants(
                season=row[0],
                woba_scale=row[1] or DEFAULT_LC.woba_scale,
                league_woba=row[2] or DEFAULT_LC.league_woba,
                # league_wrc은 사용하지 않지만 스키마에 있으므로 건너뜀
                fip_constant=row[4] or DEFAULT_LC.fip_constant,
                league_hr_fb_rate=row[5] or DEFAULT_LC.league_hr_fb_rate,
                rppa=row[6] or DEFAULT_LC.rppa,
                league_rpw=row[7] or DEFAULT_LC.league_rpw,
            )
        logger.warning(
            "%d 시즌 리그 상수 미등록 — 기본값 사용. "
            "정확도 향상을 위해 league_constants에 실측값을 삽입하세요.",
            season,
        )
        return DEFAULT_LC

    # ─── 타자 시즌 집계 ────────────────────────────────

    def aggregate_batters(self, season: int) -> int:
        """타자 시즌 누적 + 세이버메트릭스 계산 → batter_season 저장

        Returns:
            저장된 선수 수
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        lc = self._get_league_constants(conn, season)

        # 1. 경기별 기록을 선수별로 합산
        # games 테이블의 date 컬럼에서 시즌 필터
        rows = conn.execute("""
            SELECT
                bs.player_id,
                bs.team_id,
                COUNT(DISTINCT bs.game_id) as games,
                SUM(bs.pa) as pa,
                SUM(bs.ab) as ab,
                SUM(bs.hits) as hits,
                SUM(bs.doubles) as doubles,
                SUM(bs.triples) as triples,
                SUM(bs.hr) as hr,
                SUM(bs.rbi) as rbi,
                SUM(bs.runs) as runs,
                SUM(bs.sb) as sb,
                SUM(bs.cs) as cs,
                SUM(bs.bb) as bb,
                SUM(bs.hbp) as hbp,
                SUM(bs.so) as so,
                SUM(bs.gdp) as gdp,
                SUM(bs.sf) as sf,
                SUM(CASE WHEN bs.ibb IS NOT NULL THEN bs.ibb ELSE 0 END) as ibb
            FROM batter_stats bs
            JOIN games g ON bs.game_id = g.id
            WHERE g.date >= ? || '-03-22'
              AND g.date <= ? || '-10-05'
              AND g.status = 'final'
            GROUP BY bs.player_id, bs.team_id
        """, (str(season), str(season))).fetchall()

        count = 0
        for r in rows:
            hits = r["hits"] or 0
            ab = r["ab"] or 0
            hr = r["hr"] or 0
            doubles = r["doubles"] or 0
            triples = r["triples"] or 0
            bb = r["bb"] or 0
            hbp = r["hbp"] or 0
            so = r["so"] or 0
            sf = r["sf"] or 0
            pa = r["pa"] or 0
            ibb = r["ibb"] or 0
            singles = hits - doubles - triples - hr

            # 클래식 계산
            avg = calc_avg(hits, ab)
            obp = calc_obp(hits, bb, hbp, ab, sf)
            slg = calc_slg(singles, doubles, triples, hr, ab)
            ops = calc_ops(obp, slg)

            # 세이버메트릭스 계산
            woba = calc_woba(bb, ibb, hbp, singles, doubles, triples, hr, ab, sf, lc)
            wrc_plus = calc_wrc_plus(woba, pa, lc)
            war = calc_batter_war_simplified(woba, pa, lc)
            babip = calc_babip(hits, hr, ab, so, sf)
            iso = calc_iso(slg, avg)
            bb_pct = calc_bb_pct(bb, pa)
            k_pct = calc_k_pct(so, pa)

            conn.execute("""
                INSERT INTO batter_season (
                    player_id, season, team_id,
                    games, pa, ab, hits, doubles, triples, hr, rbi,
                    runs, sb, cs, bb, hbp, so, gdp, sf,
                    avg, obp, slg, ops,
                    woba, wrc_plus, war, babip, iso, bb_pct, k_pct,
                    updated_at
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT(player_id, season) DO UPDATE SET
                    team_id=excluded.team_id,
                    games=excluded.games, pa=excluded.pa, ab=excluded.ab,
                    hits=excluded.hits, doubles=excluded.doubles,
                    triples=excluded.triples, hr=excluded.hr, rbi=excluded.rbi,
                    runs=excluded.runs, sb=excluded.sb, cs=excluded.cs,
                    bb=excluded.bb, hbp=excluded.hbp, so=excluded.so,
                    gdp=excluded.gdp, sf=excluded.sf,
                    avg=excluded.avg, obp=excluded.obp, slg=excluded.slg,
                    ops=excluded.ops,
                    woba=excluded.woba, wrc_plus=excluded.wrc_plus,
                    war=excluded.war, babip=excluded.babip, iso=excluded.iso,
                    bb_pct=excluded.bb_pct, k_pct=excluded.k_pct,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                r["player_id"], season, r["team_id"],
                r["games"], pa, ab, hits, doubles, triples, hr, r["rbi"] or 0,
                r["runs"] or 0, r["sb"] or 0, r["cs"] or 0,
                bb, hbp, so, r["gdp"] or 0, sf,
                avg, obp, slg, ops,
                woba, wrc_plus, war, babip, iso, bb_pct, k_pct,
            ))
            count += 1

        conn.commit()
        self._calculate_batter_splits(conn, season)
        conn.close()
        logger.info("타자 시즌 집계 완료: %d시즌, %d명", season, count)
        return count

    def _calculate_batter_splits(self, conn: sqlite3.Connection, season: int) -> None:
        """타자 스플릿 OPS 계산 → batter_season UPDATE.

        계산 가능한 스플릿:
          - ops_vs_lhp: opponent_pitcher_hand = '좌투'
          - ops_vs_rhp: opponent_pitcher_hand = '우투'
          - ops_home:   is_home = 1
          - ops_away:   is_home = 0

        계산 불가 (NULL 유지):
          - ops_risp: runners_on_scoring이 NULL (play-by-play 미수집)
        """
        # (컬럼명, WHERE 조건) — 값은 모두 코드 내부 상수이므로 f-string 사용 안전
        splits = [
            ("ops_vs_lhp", "bs.opponent_pitcher_hand = '좌투'"),
            ("ops_vs_rhp", "bs.opponent_pitcher_hand = '우투'"),
            ("ops_home",   "bs.is_home = 1"),
            ("ops_away",   "bs.is_home = 0"),
        ]

        season_str = str(season)
        for col_name, where_clause in splits:
            rows = conn.execute(f"""
                SELECT
                    bs.player_id,
                    SUM(bs.hits)    as hits,
                    SUM(bs.ab)      as ab,
                    SUM(bs.bb)      as bb,
                    SUM(bs.hbp)     as hbp,
                    SUM(bs.sf)      as sf,
                    SUM(bs.doubles) as doubles,
                    SUM(bs.triples) as triples,
                    SUM(bs.hr)      as hr
                FROM batter_stats bs
                JOIN games g ON bs.game_id = g.id
                WHERE {where_clause}
                  AND g.date >= ? || '-03-22'
                  AND g.date <= ? || '-10-05'
                  AND g.status = 'final'
                GROUP BY bs.player_id
            """, (season_str, season_str)).fetchall()

            for row in rows:
                hits    = row[1] or 0
                ab      = row[2] or 0
                bb      = row[3] or 0
                hbp     = row[4] or 0
                sf      = row[5] or 0
                doubles = row[6] or 0
                triples = row[7] or 0
                hr      = row[8] or 0
                singles = hits - doubles - triples - hr

                obp_denom = ab + bb + hbp + sf
                obp = (hits + bb + hbp) / obp_denom if obp_denom > 0 else 0.0
                slg = (singles + 2 * doubles + 3 * triples + 4 * hr) / ab if ab > 0 else 0.0
                ops = round(obp + slg, 3)

                conn.execute(
                    f"UPDATE batter_season SET {col_name} = ? WHERE player_id = ? AND season = ?",
                    (ops, row[0], season),
                )

        conn.commit()
        logger.info("타자 스플릿 계산 완료: %d시즌", season)

    # ─── 투수 시즌 집계 ────────────────────────────────

    def aggregate_pitchers(self, season: int) -> int:
        """투수 시즌 누적 + 세이버메트릭스 계산 → pitcher_season 저장

        Returns:
            저장된 선수 수
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        lc = self._get_league_constants(conn, season)

        rows = conn.execute("""
            SELECT
                ps.player_id,
                ps.team_id,
                COUNT(DISTINCT ps.game_id) as games,
                SUM(CASE WHEN ps.decision = '승' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN ps.decision = '패' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN ps.decision = '세' THEN 1 ELSE 0 END) as saves,
                SUM(CASE WHEN ps.decision = '홀드' THEN 1 ELSE 0 END) as holds,
                SUM(ps.ip_outs) as ip_outs,
                SUM(ps.hits_allowed) as hits_allowed,
                SUM(ps.hr_allowed) as hr_allowed,
                SUM(ps.bb_allowed) as bb_allowed,
                SUM(ps.hbp_allowed) as hbp_allowed,
                SUM(ps.so_count) as so_count,
                SUM(ps.runs_allowed) as runs_allowed,
                SUM(ps.er) as er,
                -- 선발 등판이 과반이면 선발로 분류
                CASE WHEN SUM(CASE WHEN ps.is_starter = 1 THEN 1 ELSE 0 END) * 2
                     >= COUNT(DISTINCT ps.game_id)
                     THEN 1 ELSE 0 END as is_starter
            FROM pitcher_stats ps
            JOIN games g ON ps.game_id = g.id
            WHERE g.date >= ? || '-03-22'
              AND g.date <= ? || '-10-05'
              AND g.status = 'final'
            GROUP BY ps.player_id, ps.team_id
        """, (str(season), str(season))).fetchall()

        count = 0
        for r in rows:
            ip_outs = r["ip_outs"] or 0
            hits_a = r["hits_allowed"] or 0
            hr_a = r["hr_allowed"] or 0
            bb_a = r["bb_allowed"] or 0
            hbp_a = r["hbp_allowed"] or 0
            so = r["so_count"] or 0
            er = r["er"] or 0

            # 클래식
            era = calc_era(er, ip_outs)
            whip = calc_whip(hits_a, bb_a, ip_outs)

            # 세이버메트릭스
            fip = calc_fip(hr_a, bb_a, hbp_a, so, ip_outs, lc)
            xfip = calc_xfip(None, bb_a, hbp_a, so, ip_outs, lc)  # FB 없음
            war = calc_pitcher_war_simplified(fip, ip_outs, lc)
            babip = calc_pitcher_babip(hits_a, hr_a, ip_outs, so)
            k_per_9 = calc_per_9(so, ip_outs)
            bb_per_9 = calc_per_9(bb_a, ip_outs)
            hr_per_9 = calc_per_9(hr_a, ip_outs)
            k_bb = calc_k_bb_ratio(so, bb_a)

            conn.execute("""
                INSERT INTO pitcher_season (
                    player_id, season, team_id,
                    games, wins, losses, saves, holds,
                    ip_outs, hits_allowed, hr_allowed, bb_allowed,
                    hbp_allowed, so_count, runs_allowed, er,
                    era, whip,
                    fip, xfip, war, babip, lob_pct,
                    k_per_9, bb_per_9, hr_per_9, k_bb_ratio,
                    is_starter,
                    updated_at
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?, NULL,
                    ?, ?, ?, ?,
                    ?,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT(player_id, season) DO UPDATE SET
                    team_id=excluded.team_id,
                    games=excluded.games, wins=excluded.wins,
                    losses=excluded.losses, saves=excluded.saves,
                    holds=excluded.holds,
                    ip_outs=excluded.ip_outs, hits_allowed=excluded.hits_allowed,
                    hr_allowed=excluded.hr_allowed, bb_allowed=excluded.bb_allowed,
                    hbp_allowed=excluded.hbp_allowed, so_count=excluded.so_count,
                    runs_allowed=excluded.runs_allowed, er=excluded.er,
                    era=excluded.era, whip=excluded.whip,
                    fip=excluded.fip, xfip=excluded.xfip, war=excluded.war,
                    babip=excluded.babip,
                    k_per_9=excluded.k_per_9, bb_per_9=excluded.bb_per_9,
                    hr_per_9=excluded.hr_per_9, k_bb_ratio=excluded.k_bb_ratio,
                    is_starter=excluded.is_starter,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                r["player_id"], season, r["team_id"],
                r["games"], r["wins"], r["losses"], r["saves"], r["holds"],
                ip_outs, hits_a, hr_a, bb_a,
                hbp_a, so, r["runs_allowed"] or 0, er,
                era, whip,
                fip, xfip, war, babip,
                k_per_9, bb_per_9, hr_per_9, k_bb,
                r["is_starter"],
            ))
            count += 1

        conn.commit()
        self._calculate_pitcher_splits(conn, season)
        conn.close()
        logger.info("투수 시즌 집계 완료: %d시즌, %d명", season, count)
        return count

    def _calculate_pitcher_splits(self, conn: sqlite3.Connection, season: int) -> None:
        """투수 스플릿 ERA 계산 → pitcher_season UPDATE.

        계산 가능한 스플릿:
          - era_home: is_home = 1
          - era_away: is_home = 0

        계산 불가 (NULL 유지):
          - era_vs_lhb / era_vs_rhb: pitcher_stats.batter_hand 미수집
        """
        splits = [
            ("era_home", "ps.is_home = 1"),
            ("era_away", "ps.is_home = 0"),
        ]

        season_str = str(season)
        for col_name, where_clause in splits:
            rows = conn.execute(f"""
                SELECT
                    ps.player_id,
                    SUM(ps.er)      as er,
                    SUM(ps.ip_outs) as ip_outs
                FROM pitcher_stats ps
                JOIN games g ON ps.game_id = g.id
                WHERE {where_clause}
                  AND g.date >= ? || '-03-22'
                  AND g.date <= ? || '-10-05'
                  AND g.status = 'final'
                GROUP BY ps.player_id
            """, (season_str, season_str)).fetchall()

            for row in rows:
                er      = row[1] or 0
                ip_outs = row[2] or 0
                era = round((er * 27) / ip_outs, 2) if ip_outs > 0 else 0.0

                conn.execute(
                    f"UPDATE pitcher_season SET {col_name} = ? WHERE player_id = ? AND season = ?",
                    (era, row[0], season),
                )

        conn.commit()
        logger.info("투수 스플릿 계산 완료: %d시즌", season)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()

    agg = SeasonAggregator()
    batters = agg.aggregate_batters(args.season)
    pitchers = agg.aggregate_pitchers(args.season)
    print(f"집계 완료: 타자 {batters}명, 투수 {pitchers}명")
