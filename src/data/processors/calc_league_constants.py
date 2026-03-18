"""2025 KBO 리그 상수 자체 계산

batter_stats + pitcher_stats 전체 데이터에서 wOBA 가중치, FIP 상수 등을
직접 계산하여 league_constants 테이블에 저장한다.

계산 후 season_aggregator.py의 DEFAULT_LC도 업데이트하여,
_get_league_constants가 wOBA 가중치까지 실측값을 쓰도록 한다.

실행:
    python -m src.data.processors.calc_league_constants --season 2025
"""

import argparse
import logging
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path

from src.data.processors.sabermetrics_engine import LeagueConstants

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"
AGGREGATOR_PATH = Path(__file__).parent / "season_aggregator.py"

# 정규시즌 날짜 범위 (시즌별)
_SEASON_DATES = {
    2025: ("2025-03-22", "2025-10-05"),
    2026: ("2026-03-21", "2026-10-04"),  # 추정
}


def _query_batter_totals(conn: sqlite3.Connection, date_from: str, date_to: str) -> dict:
    row = conn.execute("""
        SELECT
            SUM(pa)                    AS lg_pa,
            SUM(ab)                    AS lg_ab,
            SUM(hits)                  AS lg_h,
            SUM(doubles)               AS lg_2b,
            SUM(triples)               AS lg_3b,
            SUM(hr)                    AS lg_hr,
            SUM(bb)                    AS lg_bb,
            SUM(COALESCE(ibb, 0))      AS lg_ibb,
            SUM(hbp)                   AS lg_hbp,
            SUM(sf)                    AS lg_sf,
            SUM(so)                    AS lg_so,
            SUM(runs)                  AS lg_r
        FROM batter_stats bs
        JOIN games g ON bs.game_id = g.id
        WHERE g.date >= ? AND g.date <= ? AND g.status = 'final'
    """, (date_from, date_to)).fetchone()

    if not row or not row[0]:
        raise ValueError(f"타자 집계 데이터 없음: {date_from} ~ {date_to}")

    return {
        "lg_pa":  row[0], "lg_ab":  row[1], "lg_h":   row[2],
        "lg_2b":  row[3], "lg_3b":  row[4], "lg_hr":  row[5],
        "lg_bb":  row[6], "lg_ibb": row[7], "lg_hbp": row[8],
        "lg_sf":  row[9], "lg_so":  row[10], "lg_r":  row[11],
    }


def _query_pitcher_totals(conn: sqlite3.Connection, date_from: str, date_to: str) -> dict:
    row = conn.execute("""
        SELECT
            SUM(ip_outs)                   AS lg_ip_outs,
            SUM(er)                        AS lg_er,
            SUM(hr_allowed)                AS lg_hr_p,
            SUM(bb_allowed)                AS lg_bb_p,
            SUM(COALESCE(hbp_allowed, 0))  AS lg_hbp_p,
            SUM(so_count)                  AS lg_so_p
        FROM pitcher_stats ps
        JOIN games g ON ps.game_id = g.id
        WHERE g.date >= ? AND g.date <= ? AND g.status = 'final'
    """, (date_from, date_to)).fetchone()

    if not row or not row[0]:
        raise ValueError(f"투수 집계 데이터 없음: {date_from} ~ {date_to}")

    return {
        "lg_ip_outs": row[0], "lg_er":    row[1], "lg_hr_p":  row[2],
        "lg_bb_p":    row[3], "lg_hbp_p": row[4], "lg_so_p":  row[5],
    }


def calc_constants(season: int, db_path: str = str(DB_PATH)) -> LeagueConstants:
    """DB 데이터에서 리그 상수 계산 후 LeagueConstants 반환"""
    conn = sqlite3.connect(db_path)
    try:
        date_from, date_to = _SEASON_DATES.get(season, (f"{season}-03-22", f"{season}-10-05"))
        b = _query_batter_totals(conn, date_from, date_to)
        p = _query_pitcher_totals(conn, date_from, date_to)
    finally:
        conn.close()

    # ── 파생 집계 ─────────────────────────────────────────
    lg_1b  = b["lg_h"] - b["lg_2b"] - b["lg_3b"] - b["lg_hr"]
    lg_ubb = b["lg_bb"] - b["lg_ibb"]   # 비고의 볼넷

    # ── 리그 기본 비율 ────────────────────────────────────
    lg_pa   = b["lg_pa"]
    lg_ab   = b["lg_ab"]
    lg_r    = b["lg_r"]
    lg_hbp  = b["lg_hbp"]
    lg_sf   = b["lg_sf"]
    lg_bb   = b["lg_bb"]
    lg_2b   = b["lg_2b"]
    lg_3b   = b["lg_3b"]
    lg_hr   = b["lg_hr"]

    lg_obp  = (b["lg_h"] + lg_bb + lg_hbp) / (lg_ab + lg_bb + lg_hbp + lg_sf)
    rppa    = lg_r / lg_pa

    # ── wOBA 가중치 계산 ──────────────────────────────────
    # MLB 기준 비율(Tom Tango)을 KBO R/PA로 스케일링
    # 기준 R/PA = 0.12 (MLB 평균)
    MLB_RPPA = 0.12
    run_bb  = rppa * (0.69 / MLB_RPPA)
    run_hbp = rppa * (0.72 / MLB_RPPA)
    run_1b  = rppa * (0.89 / MLB_RPPA)
    run_2b  = rppa * (1.27 / MLB_RPPA)
    run_3b  = rppa * (1.62 / MLB_RPPA)
    run_hr  = rppa * (2.10 / MLB_RPPA)

    # wOBA raw (스케일 적용 전)
    woba_raw_num = (run_bb  * lg_ubb + run_hbp * lg_hbp +
                    run_1b  * lg_1b  + run_2b  * lg_2b  +
                    run_3b  * lg_3b  + run_hr  * lg_hr)
    woba_raw_den = lg_ab + lg_ubb + lg_sf + lg_hbp
    woba_raw     = woba_raw_num / woba_raw_den

    # wOBA Scale = 리그 OBP / wOBA raw → league_woba ≈ lg_obp
    woba_scale = lg_obp / woba_raw

    w_bb  = run_bb  * woba_scale
    w_hbp = run_hbp * woba_scale
    w_1b  = run_1b  * woba_scale
    w_2b  = run_2b  * woba_scale
    w_3b  = run_3b  * woba_scale
    w_hr  = run_hr  * woba_scale

    league_woba = (
        w_bb  * lg_ubb + w_hbp * lg_hbp +
        w_1b  * lg_1b  + w_2b  * lg_2b  +
        w_3b  * lg_3b  + w_hr  * lg_hr
    ) / woba_raw_den   # ≈ lg_obp (스케일링 정의)

    # ── FIP 상수 ──────────────────────────────────────────
    lg_ip     = p["lg_ip_outs"] / 3
    lg_era    = p["lg_er"] * 9 / lg_ip
    lg_fip_raw = (
        13 * p["lg_hr_p"]
        + 3 * (p["lg_bb_p"] + p["lg_hbp_p"])
        - 2 * p["lg_so_p"]
    ) / lg_ip
    fip_constant = lg_era - lg_fip_raw

    lc = LeagueConstants(
        season=season,
        w_bb=round(w_bb,   4),
        w_hbp=round(w_hbp, 4),
        w_1b=round(w_1b,   4),
        w_2b=round(w_2b,   4),
        w_3b=round(w_3b,   4),
        w_hr=round(w_hr,   4),
        woba_scale=round(woba_scale,   4),
        league_woba=round(league_woba, 4),
        league_obp=round(lg_obp,       4),
        rppa=round(rppa,               4),
        league_rpw=10.0,
        league_r_pa=round(rppa,        4),
        fip_constant=round(fip_constant, 4),
        league_hr_fb_rate=0.10,   # FB 데이터 없어 근사값 유지
    )
    return lc


def save_to_db(lc: LeagueConstants, db_path: str = str(DB_PATH)) -> None:
    """league_constants 테이블에 INSERT OR REPLACE"""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO league_constants
              (season, woba_scale, league_woba, league_wrc,
               fip_constant, league_hr_fb_rate, rppa, league_rpw)
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
        """, (
            lc.season,
            lc.woba_scale, lc.league_woba,
            lc.fip_constant, lc.league_hr_fb_rate,
            lc.rppa, lc.league_rpw,
        ))
        conn.commit()
        logger.info("league_constants 저장 완료: season=%d", lc.season)
    finally:
        conn.close()


def update_default_lc(lc: LeagueConstants) -> None:
    """season_aggregator.py의 DEFAULT_LC를 계산된 값으로 교체"""
    src = AGGREGATOR_PATH.read_text(encoding="utf-8")

    new_lc = (
        f"DEFAULT_LC = LeagueConstants(\n"
        f"    season={lc.season},\n"
        f"    # wOBA 가중치 — {lc.season} KBO 실측 계산값 (calc_league_constants.py)\n"
        f"    w_bb={lc.w_bb},   w_hbp={lc.w_hbp},  w_1b={lc.w_1b},\n"
        f"    w_2b={lc.w_2b},  w_3b={lc.w_3b},  w_hr={lc.w_hr},\n"
        f"    woba_scale={lc.woba_scale},\n"
        f"    league_woba={lc.league_woba},\n"
        f"    league_obp={lc.league_obp},\n"
        f"    rppa={lc.rppa},\n"
        f"    league_rpw={lc.league_rpw},\n"
        f"    league_r_pa={lc.league_r_pa},\n"
        f"    fip_constant={lc.fip_constant},\n"
        f"    league_hr_fb_rate={lc.league_hr_fb_rate},\n"
        f")"
    )

    updated = re.sub(
        r"DEFAULT_LC\s*=\s*LeagueConstants\([^)]*\)",
        new_lc,
        src,
        flags=re.DOTALL,
    )
    if updated == src:
        logger.warning("DEFAULT_LC 패턴 미발견 — season_aggregator.py 수동 확인 필요")
        return
    AGGREGATOR_PATH.write_text(updated, encoding="utf-8")
    logger.info("DEFAULT_LC 업데이트 완료: season_aggregator.py")


def run_aggregation(season: int, db_path: str = str(DB_PATH)) -> None:
    """season_aggregator 재실행"""
    from src.data.processors.season_aggregator import SeasonAggregator
    agg = SeasonAggregator(db_path)
    b_count = agg.aggregate_batters(season)
    p_count = agg.aggregate_pitchers(season)
    logger.info("재집계 완료: 타자 %d명, 투수 %d명", b_count, p_count)


def verify(season: int, db_path: str = str(DB_PATH)) -> None:
    """결과 검증"""
    conn = sqlite3.connect(db_path)

    lc_row = conn.execute(
        "SELECT * FROM league_constants WHERE season = ?", (season,)
    ).fetchone()
    assert lc_row, f"{season} 리그 상수 미저장!"
    print(f"\n[✓] league_constants({season}): {lc_row}")

    diaz = conn.execute("""
        SELECT p.name, bs.hr, bs.woba, bs.wrc_plus, bs.war
        FROM batter_season bs JOIN players p ON bs.player_id = p.id
        WHERE p.name LIKE '%디아즈%' AND bs.season = ?
    """, (season,)).fetchone()
    print(f"[디아즈] {diaz}")
    assert diaz and diaz[1] == 50, f"디아즈 HR 이상: {diaz}"

    ponce = conn.execute("""
        SELECT p.name, ps.fip, ps.xfip, ps.war
        FROM pitcher_season ps JOIN players p ON ps.player_id = p.id
        WHERE p.name LIKE '%폰세%' AND ps.season = ?
    """, (season,)).fetchone()
    print(f"[폰세]   {ponce}")

    sb_top3 = conn.execute("""
        SELECT p.name, bs.sb FROM batter_season bs
        JOIN players p ON bs.player_id = p.id
        WHERE bs.season = ? ORDER BY bs.sb DESC LIMIT 3
    """, (season,)).fetchall()
    print(f"[도루 TOP3] {sb_top3}")
    names = [r[0] for r in sb_top3]
    assert "박해민" in names, f"박해민 도루 TOP3 미포함: {sb_top3}"

    conn.close()
    print("\n[✓] 모든 검증 통과")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="KBO 리그 상수 자체 계산")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--db", default=str(DB_PATH), help="DB 경로")
    parser.add_argument("--no-update-default", action="store_true",
                        help="season_aggregator.py DEFAULT_LC 수정 안 함")
    parser.add_argument("--no-reaggregate", action="store_true",
                        help="시즌 재집계 건너뜀")
    parser.add_argument("--verify-only", action="store_true",
                        help="검증만 실행")
    args = parser.parse_args()

    if args.verify_only:
        verify(args.season, args.db)
        return

    logger.info("=== %d 리그 상수 계산 시작 ===", args.season)
    lc = calc_constants(args.season, args.db)

    print(f"\n계산된 리그 상수 ({args.season}):")
    print(f"  wOBA 가중치: BB={lc.w_bb}, HBP={lc.w_hbp}, 1B={lc.w_1b}, "
          f"2B={lc.w_2b}, 3B={lc.w_3b}, HR={lc.w_hr}")
    print(f"  wOBA Scale: {lc.woba_scale}")
    print(f"  League wOBA: {lc.league_woba}  (≈ League OBP: {lc.league_obp})")
    print(f"  FIP 상수: {lc.fip_constant}")
    print(f"  R/PA: {lc.rppa}")

    save_to_db(lc, args.db)

    if not args.no_update_default:
        update_default_lc(lc)

    if not args.no_reaggregate:
        logger.info("=== 시즌 재집계 시작 ===")
        run_aggregation(args.season, args.db)

    verify(args.season, args.db)


if __name__ == "__main__":
    main()
