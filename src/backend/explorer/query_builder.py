"""동적 SQL 빌더 — 탐색기 핵심 엔진

드롭다운 5단 조합(target, condition, stat, sort, limit)을
SQLAlchemy Core 쿼리로 변환하고, 필요 시 Python에서 세이버메트릭스를 재계산합니다.

경로 A (condition="all"): batter_season / pitcher_season에서 직접 조회
경로 B (condition≠"all"): batter_stats / pitcher_stats에서 GROUP BY 집계 → Python 후처리
"""

from typing import Optional

from sqlalchemy import select, func, case, and_, or_
from sqlalchemy.engine import Connection

from src.backend.models import (
    batter_season, pitcher_season,
    batter_stats, pitcher_stats,
    games, players, teams,
    league_constants,
)
from src.backend.schemas.explorer import (
    ExplorerQuery, ExplorerResultItem, ExplorerResponse,
)
from src.data.processors.sabermetrics_engine import (
    LeagueConstants,
    calc_avg, calc_obp, calc_slg, calc_ops, calc_iso,
    calc_babip, calc_bb_pct, calc_k_pct,
    calc_woba, calc_wrc_plus, calc_batter_war_simplified,
    calc_era, calc_whip, calc_fip, calc_xfip,
    calc_per_9, calc_k_bb_ratio, calc_pitcher_babip,
    calc_pitcher_war_simplified,
)

# 최소 타석/이닝 (노이즈 방지)
MIN_PA = 30
MIN_IP_OUTS = 30  # = 10.0 이닝

# 기본 리그 상수 (league_constants 테이블에 없을 때)
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

# 타자 전용 조건 (투수에게 사용하면 ValueError)
_BATTER_ONLY_CONDITIONS = frozenset({
    "vs_lhp", "vs_rhp", "risp", "bases_loaded", "no_runners",
    "inning_1_3", "inning_4_6", "inning_7_9",
})

# 투수 전용 조건
_PITCHER_ONLY_CONDITIONS = frozenset({
    "vs_lhb", "vs_rhb",
})

# 유효 타자 지표
_BATTER_STATS = frozenset({
    "avg", "hr", "rbi", "hits", "sb", "ops", "woba", "wrc_plus",
    "war", "babip", "iso", "bb_pct", "k_pct", "pa", "ab",
    "doubles", "triples", "bb", "so", "hbp", "gdp", "sf", "runs",
    "obp", "slg",
})

# 유효 투수 지표
_PITCHER_STATS = frozenset({
    "era", "wins", "losses", "whip", "so_count", "fip", "xfip",
    "k_per_9", "bb_per_9", "hr_per_9", "war", "babip", "lob_pct",
    "holds", "saves", "games", "ip_outs", "k_bb_ratio",
})

# batter_season 컬럼 매핑 (직접 조회 가능한 컬럼)
_BATTER_SEASON_COLS = {
    "avg", "obp", "slg", "ops", "hr", "rbi", "hits", "sb", "pa", "ab",
    "doubles", "triples", "bb", "so", "hbp", "gdp", "sf", "runs",
    "woba", "wrc_plus", "war", "babip", "iso", "bb_pct", "k_pct",
    "games",
}

# pitcher_season 컬럼 매핑
_PITCHER_SEASON_COLS = {
    "era", "whip", "fip", "xfip", "war", "babip", "lob_pct",
    "k_per_9", "bb_per_9", "hr_per_9", "k_bb_ratio",
    "wins", "losses", "saves", "holds", "so_count", "games", "ip_outs",
}


def build_explorer_query(
    conn: Connection,
    target: str,
    condition: str,
    stat: str,
    sort: str,
    limit: str,
    season: int = 2025,
) -> ExplorerResponse:
    """메인 진입점 — 5단 드롭다운 조합을 실행하여 ExplorerResponse 반환"""
    _validate_inputs(target, condition, stat, sort, limit)

    if condition == "all":
        rows = _query_season_table(conn, target, stat, sort, limit, season)
    else:
        raw_agg = _query_gamelog_aggregate(conn, target, condition, season)
        rows = _compute_and_rank(raw_agg, target, stat, sort, limit, season, conn)

    secondary_keys = _get_secondary_stats(target, stat)
    results = _format_results(rows, stat, secondary_keys)

    query_model = ExplorerQuery(
        target=target, condition=condition, stat=stat,
        sort=sort, limit=limit, season=season,
    )
    return ExplorerResponse(
        query=query_model,
        results=results,
        total_count=len(results),
    )


def _validate_inputs(
    target: str, condition: str, stat: str, sort: str, limit: str,
) -> None:
    """입력값 검증 — 잘못된 조합 시 ValueError"""
    valid_targets = {"batter", "pitcher", "pitcher_starter", "pitcher_bullpen"}
    if target not in valid_targets:
        raise ValueError(f"잘못된 target: {target}")

    if sort not in ("asc", "desc"):
        raise ValueError(f"잘못된 sort: {sort}")

    if limit not in ("5", "10", "20", "all"):
        raise ValueError(f"잘못된 limit: {limit}")

    is_pitcher = target in ("pitcher", "pitcher_starter", "pitcher_bullpen")

    if is_pitcher and condition in _BATTER_ONLY_CONDITIONS:
        raise ValueError(
            f"투수에게 사용할 수 없는 조건: {condition}"
        )

    if not is_pitcher and condition in _PITCHER_ONLY_CONDITIONS:
        raise ValueError(
            f"타자에게 사용할 수 없는 조건: {condition}"
        )

    if is_pitcher:
        if stat not in _PITCHER_STATS:
            raise ValueError(f"잘못된 투수 지표: {stat}")
    else:
        if stat not in _BATTER_STATS:
            raise ValueError(f"잘못된 타자 지표: {stat}")


# ─── 경로 A: 시즌 테이블 직접 조회 ──────────────────────────


def _query_season_table(
    conn: Connection,
    target: str,
    stat: str,
    sort: str,
    limit: str,
    season: int,
) -> list[dict]:
    """batter_season / pitcher_season에서 직접 조회 (condition=all)"""
    is_pitcher = target in ("pitcher", "pitcher_starter", "pitcher_bullpen")

    if is_pitcher:
        tbl = pitcher_season
        min_filter = tbl.c.ip_outs >= MIN_IP_OUTS
    else:
        tbl = batter_season
        min_filter = tbl.c.pa >= MIN_PA

    stat_col = tbl.c[stat]

    stmt = (
        select(
            tbl,
            players.c.name.label("player_name"),
            teams.c.short_name.label("team_name"),
        )
        .select_from(
            tbl
            .join(players, tbl.c.player_id == players.c.id)
            .join(teams, tbl.c.team_id == teams.c.id)
        )
        .where(tbl.c.season == season)
        .where(min_filter)
        .where(stat_col.isnot(None))
    )

    # 선발/불펜 필터
    if target == "pitcher_starter":
        stmt = stmt.where(tbl.c.is_starter == True)  # noqa: E712
    elif target == "pitcher_bullpen":
        stmt = stmt.where(tbl.c.is_starter == False)  # noqa: E712

    # 정렬
    if sort == "desc":
        stmt = stmt.order_by(stat_col.desc())
    else:
        stmt = stmt.order_by(stat_col.asc())

    # limit
    if limit != "all":
        stmt = stmt.limit(int(limit))

    result = conn.execute(stmt)
    return [dict(row._mapping) for row in result]


# ─── 경로 B: 경기별 테이블 집계 → Python 후처리 ──────────────


def _query_gamelog_aggregate(
    conn: Connection,
    target: str,
    condition: str,
    season: int,
) -> list[dict]:
    """batter_stats / pitcher_stats에서 조건 필터 + GROUP BY 집계"""
    is_pitcher = target in ("pitcher", "pitcher_starter", "pitcher_bullpen")
    season_str = str(season)

    if is_pitcher:
        tbl = pitcher_stats
        agg_cols = [
            tbl.c.player_id,
            func.sum(tbl.c.ip_outs).label("ip_outs"),
            func.sum(tbl.c.hits_allowed).label("hits_allowed"),
            func.sum(tbl.c.hr_allowed).label("hr_allowed"),
            func.sum(tbl.c.bb_allowed).label("bb_allowed"),
            func.sum(tbl.c.hbp_allowed).label("hbp_allowed"),
            func.sum(tbl.c.so_count).label("so_count"),
            func.sum(tbl.c.runs_allowed).label("runs_allowed"),
            func.sum(tbl.c.er).label("er"),
            func.count(tbl.c.game_id.distinct()).label("games"),
            func.sum(case((tbl.c.decision == "W", 1), else_=0)).label("wins"),
            func.sum(case((tbl.c.decision == "L", 1), else_=0)).label("losses"),
            func.sum(case((tbl.c.decision == "S", 1), else_=0)).label("saves"),
            func.sum(case((tbl.c.decision == "H", 1), else_=0)).label("holds"),
        ]
    else:
        tbl = batter_stats
        agg_cols = [
            tbl.c.player_id,
            func.sum(tbl.c.pa).label("pa"),
            func.sum(tbl.c.ab).label("ab"),
            func.sum(tbl.c.hits).label("hits"),
            func.sum(tbl.c.doubles).label("doubles"),
            func.sum(tbl.c.triples).label("triples"),
            func.sum(tbl.c.hr).label("hr"),
            func.sum(tbl.c.rbi).label("rbi"),
            func.sum(tbl.c.runs).label("runs"),
            func.sum(tbl.c.sb).label("sb"),
            func.sum(tbl.c.cs).label("cs"),
            func.sum(tbl.c.bb).label("bb"),
            func.sum(tbl.c.hbp).label("hbp"),
            func.sum(tbl.c.so).label("so"),
            func.sum(tbl.c.gdp).label("gdp"),
            func.sum(tbl.c.sf).label("sf"),
            func.sum(func.coalesce(tbl.c.ibb, 0)).label("ibb"),
            func.count(tbl.c.game_id.distinct()).label("games"),
        ]

    # player_name, team_name 추가
    agg_cols.extend([
        players.c.name.label("player_name"),
        teams.c.short_name.label("team_name"),
    ])

    join_expr = (
        tbl
        .join(players, tbl.c.player_id == players.c.id)
        .join(teams, tbl.c.team_id == teams.c.id)
    )

    # 조건에 따라 games 테이블 JOIN 필요 여부 결정
    needs_games_join = condition in (
        "night", "day", "weekday", "weekend",
    ) or condition.startswith("vs_team:")

    if needs_games_join:
        join_expr = join_expr.join(games, tbl.c.game_id == games.c.id)

    stmt = select(*agg_cols).select_from(join_expr)

    # 시즌 필터: games 테이블 JOIN 여부에 따라 분기
    if needs_games_join:
        stmt = stmt.where(
            and_(
                games.c.date >= season_str + "-03-22",
                games.c.date <= season_str + "-10-05",
                games.c.status == "final",
            )
        )
    else:
        # games JOIN 없이는 batter_stats/pitcher_stats에서
        # game_id → games.date 서브쿼리로 필터
        game_ids_in_season = (
            select(games.c.id)
            .where(games.c.date >= season_str + "-03-22")
            .where(games.c.date <= season_str + "-10-05")
            .where(games.c.status == "final")
        )
        stmt = stmt.where(tbl.c.game_id.in_(game_ids_in_season))

    # 조건 적용
    stmt = _apply_condition(stmt, tbl, target, condition, is_pitcher)

    # 선발/불펜 필터
    if is_pitcher and target == "pitcher_starter":
        stmt = stmt.where(tbl.c.is_starter == True)  # noqa: E712
    elif is_pitcher and target == "pitcher_bullpen":
        stmt = stmt.where(tbl.c.is_starter == False)  # noqa: E712

    # GROUP BY
    stmt = stmt.group_by(tbl.c.player_id, players.c.name, teams.c.short_name)

    result = conn.execute(stmt)
    return [dict(row._mapping) for row in result]


def _apply_condition(stmt, tbl, target: str, condition: str, is_pitcher: bool):
    """WHERE절에 조건 추가"""
    if condition == "all":
        return stmt

    # 타자 조건
    if not is_pitcher:
        if condition == "vs_lhp":
            return stmt.where(tbl.c.opponent_pitcher_hand == "좌투")
        elif condition == "vs_rhp":
            return stmt.where(tbl.c.opponent_pitcher_hand == "우투")
        elif condition == "risp":
            return stmt.where(tbl.c.runners_on_scoring == True)  # noqa: E712
        elif condition == "no_runners":
            return stmt.where(tbl.c.runners_on_scoring == False)  # noqa: E712
        elif condition == "inning_1_3":
            return stmt.where(tbl.c.inning.between(1, 3))
        elif condition == "inning_4_6":
            return stmt.where(tbl.c.inning.between(4, 6))
        elif condition == "inning_7_9":
            return stmt.where(tbl.c.inning.between(7, 9))
        elif condition == "leading":
            return stmt.where(tbl.c.score_diff > 0)
        elif condition == "tied":
            return stmt.where(tbl.c.score_diff == 0)
        elif condition == "trailing":
            return stmt.where(tbl.c.score_diff < 0)

    # 투수 조건
    if is_pitcher:
        if condition == "vs_lhb":
            return stmt.where(tbl.c.batter_hand == "좌타")
        elif condition == "vs_rhb":
            return stmt.where(tbl.c.batter_hand == "우타")

    # 공통 조건 (타자/투수 모두)
    if condition == "home":
        return stmt.where(tbl.c.is_home == True)  # noqa: E712
    elif condition == "away":
        return stmt.where(tbl.c.is_home == False)  # noqa: E712
    elif condition == "night":
        return stmt.where(games.c.is_night_game == True)  # noqa: E712
    elif condition == "day":
        return stmt.where(games.c.is_night_game == False)  # noqa: E712
    elif condition == "weekday":
        return stmt.where(games.c.day_of_week.in_(["월", "화", "수", "목", "금"]))
    elif condition == "weekend":
        return stmt.where(games.c.day_of_week.in_(["토", "일"]))
    elif condition.startswith("vs_team:"):
        opp_team_id = int(condition.split(":")[1])
        if is_pitcher:
            # 투수의 상대 팀 = 홈이면 원정팀, 원정이면 홈팀
            return stmt.where(
                or_(
                    and_(tbl.c.is_home == True, games.c.away_team_id == opp_team_id),  # noqa: E712
                    and_(tbl.c.is_home == False, games.c.home_team_id == opp_team_id),  # noqa: E712
                )
            )
        else:
            return stmt.where(
                or_(
                    and_(tbl.c.is_home == True, games.c.away_team_id == opp_team_id),  # noqa: E712
                    and_(tbl.c.is_home == False, games.c.home_team_id == opp_team_id),  # noqa: E712
                )
            )
    elif condition == "bases_loaded":
        raise ValueError("bases_loaded 조건은 현재 스키마에서 미지원")

    raise ValueError(f"알 수 없는 조건: {condition}")


def _compute_and_rank(
    raw_agg: list[dict],
    target: str,
    stat: str,
    sort: str,
    limit: str,
    season: int,
    conn: Connection,
) -> list[dict]:
    """집계된 raw 수치에 세이버메트릭스 재계산 → 정렬 → limit"""
    lc = _load_league_constants(conn, season)
    is_pitcher = target in ("pitcher", "pitcher_starter", "pitcher_bullpen")

    computed = []
    for row in raw_agg:
        if is_pitcher:
            enriched = _compute_pitcher_stats(row, lc)
            if (enriched.get("ip_outs") or 0) < MIN_IP_OUTS:
                continue
        else:
            enriched = _compute_batter_stats(row, lc)
            if (enriched.get("pa") or 0) < MIN_PA:
                continue
        computed.append(enriched)

    # 정렬
    reverse = sort == "desc"
    computed.sort(
        key=lambda r: (r.get(stat) is not None, r.get(stat) or 0),
        reverse=reverse,
    )

    # limit
    if limit != "all":
        computed = computed[: int(limit)]

    return computed


def _compute_batter_stats(row: dict, lc: LeagueConstants) -> dict:
    """raw 타자 집계에 세이버메트릭스 계산 추가"""
    result = dict(row)
    hits = row.get("hits") or 0
    ab = row.get("ab") or 0
    hr = row.get("hr") or 0
    doubles = row.get("doubles") or 0
    triples = row.get("triples") or 0
    bb = row.get("bb") or 0
    hbp = row.get("hbp") or 0
    so = row.get("so") or 0
    sf = row.get("sf") or 0
    pa = row.get("pa") or 0
    ibb = row.get("ibb") or 0
    singles = hits - doubles - triples - hr

    result["avg"] = calc_avg(hits, ab)
    result["obp"] = calc_obp(hits, bb, hbp, ab, sf)
    slg = calc_slg(singles, doubles, triples, hr, ab)
    result["slg"] = slg
    obp = result["obp"]
    result["ops"] = calc_ops(obp, slg)
    result["babip"] = calc_babip(hits, hr, ab, so, sf)
    result["iso"] = calc_iso(slg, result["avg"])
    result["bb_pct"] = calc_bb_pct(bb, pa)
    result["k_pct"] = calc_k_pct(so, pa)

    woba = calc_woba(bb, ibb, hbp, singles, doubles, triples, hr, ab, sf, lc)
    result["woba"] = woba
    result["wrc_plus"] = calc_wrc_plus(woba, pa, lc)
    result["war"] = calc_batter_war_simplified(woba, pa, lc)

    return result


def _compute_pitcher_stats(row: dict, lc: LeagueConstants) -> dict:
    """raw 투수 집계에 세이버메트릭스 계산 추가"""
    result = dict(row)
    ip_outs = row.get("ip_outs") or 0
    hits_a = row.get("hits_allowed") or 0
    hr_a = row.get("hr_allowed") or 0
    bb_a = row.get("bb_allowed") or 0
    hbp_a = row.get("hbp_allowed") or 0
    so = row.get("so_count") or 0
    er = row.get("er") or 0

    result["era"] = calc_era(er, ip_outs)
    result["whip"] = calc_whip(hits_a, bb_a, ip_outs)
    fip = calc_fip(hr_a, bb_a, hbp_a, so, ip_outs, lc)
    result["fip"] = fip
    result["xfip"] = calc_xfip(None, bb_a, hbp_a, so, ip_outs, lc)
    result["war"] = calc_pitcher_war_simplified(fip, ip_outs, lc)
    result["babip"] = calc_pitcher_babip(hits_a, hr_a, ip_outs, so)
    result["k_per_9"] = calc_per_9(so, ip_outs)
    result["bb_per_9"] = calc_per_9(bb_a, ip_outs)
    result["hr_per_9"] = calc_per_9(hr_a, ip_outs)
    result["k_bb_ratio"] = calc_k_bb_ratio(so, bb_a)

    return result


def _load_league_constants(conn: Connection, season: int) -> LeagueConstants:
    """league_constants 테이블에서 시즌 상수 로드, 없으면 기본값"""
    stmt = select(league_constants).where(league_constants.c.season == season)
    row = conn.execute(stmt).fetchone()
    if row:
        m = row._mapping
        return LeagueConstants(
            season=season,
            woba_scale=m.get("woba_scale") or DEFAULT_LC.woba_scale,
            league_woba=m.get("league_woba") or DEFAULT_LC.league_woba,
            fip_constant=m.get("fip_constant") or DEFAULT_LC.fip_constant,
            league_hr_fb_rate=m.get("league_hr_fb_rate") or DEFAULT_LC.league_hr_fb_rate,
            rppa=m.get("rppa") or DEFAULT_LC.rppa,
            league_rpw=m.get("league_rpw") or DEFAULT_LC.league_rpw,
        )
    return DEFAULT_LC


# ─── 보조 지표 ────────────────────────────────────────────


_BATTER_SECONDARY: dict[str, list[str]] = {
    "avg": ["hr", "rbi", "ops"],
    "hr": ["avg", "rbi", "ops"],
    "rbi": ["avg", "hr", "ops"],
    "hits": ["avg", "hr", "ops"],
    "sb": ["avg", "hits", "ops"],
    "ops": ["avg", "hr", "rbi"],
    "obp": ["avg", "bb_pct", "ops"],
    "slg": ["avg", "hr", "ops"],
    "woba": ["avg", "ops", "wrc_plus"],
    "wrc_plus": ["woba", "ops", "war"],
    "war": ["wrc_plus", "ops", "avg"],
    "babip": ["avg", "ops", "k_pct"],
    "iso": ["hr", "slg", "ops"],
    "bb_pct": ["obp", "k_pct", "ops"],
    "k_pct": ["avg", "bb_pct", "so"],
}

_PITCHER_SECONDARY: dict[str, list[str]] = {
    "era": ["wins", "so_count", "whip"],
    "fip": ["era", "xfip", "k_per_9"],
    "whip": ["era", "fip", "bb_per_9"],
    "so_count": ["era", "k_per_9", "wins"],
    "war": ["fip", "era", "k_per_9"],
    "wins": ["era", "so_count", "whip"],
    "losses": ["era", "whip", "fip"],
    "saves": ["era", "holds", "whip"],
    "holds": ["era", "saves", "whip"],
    "k_per_9": ["bb_per_9", "fip", "era"],
    "bb_per_9": ["k_per_9", "whip", "era"],
    "xfip": ["fip", "era", "k_per_9"],
    "babip": ["era", "fip", "whip"],
    "k_bb_ratio": ["k_per_9", "bb_per_9", "fip"],
}


def _get_secondary_stats(target: str, primary_stat: str) -> list[str]:
    """주요 지표에 따른 보조 지표 2~3개 선택"""
    is_pitcher = target in ("pitcher", "pitcher_starter", "pitcher_bullpen")
    mapping = _PITCHER_SECONDARY if is_pitcher else _BATTER_SECONDARY
    return mapping.get(primary_stat, ["avg", "ops", "hr"] if not is_pitcher else ["era", "whip", "fip"])


# ─── 결과 포맷팅 ──────────────────────────────────────────


def _format_results(
    rows: list[dict],
    primary_stat: str,
    secondary_keys: list[str],
) -> list[ExplorerResultItem]:
    """결과를 ExplorerResultItem 리스트로 변환"""
    results = []
    for i, row in enumerate(rows, 1):
        primary_val = row.get(primary_stat)
        secondary = {}
        for key in secondary_keys:
            val = row.get(key)
            if val is not None and isinstance(val, float):
                secondary[key] = round(val, 3)
            else:
                secondary[key] = val

        if primary_val is not None and isinstance(primary_val, float):
            primary_val = round(primary_val, 3)

        results.append(ExplorerResultItem(
            rank=i,
            player_id=row.get("player_id", 0),
            player_name=row.get("player_name", ""),
            team_name=row.get("team_name", ""),
            primary_stat=primary_val,
            secondary_stats=secondary,
        ))
    return results
