"""팀/순위 API — 순위표, 팀스탯 비교, 선수 TOP N"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.backend.database import get_db, get_latest_season
from src.backend.models import batter_season, games, pitcher_season, players, teams
from src.backend.schemas.team import (
    StandingsResponse,
    TeamCompareCard,
    TeamComparisonResponse,
    TeamRankItem,
    TeamStanding,
    TopRankItem,
    TopRankingsResponse,
)

router = APIRouter()

# ── 화이트리스트 ────────────────────────────────────────

_BATTER_STATS = {
    "avg", "obp", "slg", "ops", "hr", "rbi", "runs", "sb", "bb",
    "so", "hits", "pa", "woba", "wrc_plus", "war", "babip", "iso",
    "bb_pct", "k_pct",
}
_PITCHER_STATS = {
    "era", "wins", "losses", "saves", "holds", "so_count", "whip",
    "fip", "xfip", "war", "babip", "k_per_9", "bb_per_9", "hr_per_9",
    "k_bb_ratio", "bb_allowed", "hr_allowed",
}
# 낮을수록 좋은 투수 지표 — ASC 정렬
_PITCHER_ASC = {"era", "fip", "xfip", "whip", "bb_per_9", "hr_per_9", "bb_allowed", "hr_allowed"}

_SEASON_START = "-03-22"
_SEASON_END = "-10-05"




# ── 팀 순위표 ────────────────────────────────────────────

@router.get("/teams/standings", response_model=StandingsResponse)
def get_standings(
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """팀 순위표"""
    season = season or get_latest_season(db)
    date_from = f"{season}{_SEASON_START}"
    date_to = f"{season}{_SEASON_END}"

    stmt = text("""
        SELECT
            t.id   AS team_id,
            t.short_name AS team_name,
            COUNT(*)  AS games,
            SUM(CASE WHEN
                (g.home_team_id = t.id AND g.home_score > g.away_score) OR
                (g.away_team_id = t.id AND g.away_score > g.home_score)
                THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN
                (g.home_team_id = t.id AND g.home_score < g.away_score) OR
                (g.away_team_id = t.id AND g.away_score < g.home_score)
                THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN g.home_score = g.away_score THEN 1 ELSE 0 END) AS draws
        FROM teams t
        JOIN games g ON (g.home_team_id = t.id OR g.away_team_id = t.id)
        WHERE g.status = 'final'
          AND g.date >= :date_from
          AND g.date <= :date_to
        GROUP BY t.id, t.short_name
        ORDER BY wins DESC
    """)
    rows = db.execute(stmt, {"date_from": date_from, "date_to": date_to}).mappings().all()

    # 승률 계산 후 내림차순 재정렬 (동일 승수일 때 패수 적은 팀 우선)
    raw = []
    for r in rows:
        wins = r["wins"] or 0
        losses = r["losses"] or 0
        draws = r["draws"] or 0
        win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.0
        raw.append({
            "team_id": r["team_id"],
            "team_name": r["team_name"],
            "games": r["games"] or 0,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_pct": round(win_pct, 4),
        })
    raw.sort(key=lambda x: x["win_pct"], reverse=True)

    # recent_5 + streak: 모든 팀 경기를 한 번에 조회 → Python에서 팀별 분리
    recent_stmt = text("""
        SELECT
            g.date,
            g.home_team_id,
            g.away_team_id,
            g.home_score,
            g.away_score
        FROM games g
        WHERE g.status = 'final'
          AND g.date >= :date_from
          AND g.date <= :date_to
        ORDER BY g.date DESC
    """)
    all_games = db.execute(recent_stmt, {"date_from": date_from, "date_to": date_to}).mappings().all()

    # 팀별 최신순 결과 리스트 구성
    team_results: dict[int, list[str]] = {}
    for g in all_games:
        htid = g["home_team_id"]
        atid = g["away_team_id"]
        hs, as_ = g["home_score"], g["away_score"]
        if hs is None or as_ is None:
            continue
        if hs > as_:
            home_r, away_r = "W", "L"
        elif hs < as_:
            home_r, away_r = "L", "W"
        else:
            home_r, away_r = "D", "D"
        team_results.setdefault(htid, []).append(home_r)
        team_results.setdefault(atid, []).append(away_r)

    standings = []
    top_wins = top_losses = None
    for i, d in enumerate(raw):
        if i == 0:
            top_wins, top_losses = d["wins"], d["losses"]
            gb = 0.0
        else:
            gb = ((top_wins - d["wins"]) + (d["losses"] - top_losses)) / 2

        tid = d["team_id"]
        results = team_results.get(tid, [])
        recent_5 = results[:5]
        streak = _calc_streak(results)

        standings.append(TeamStanding(
            rank=i + 1,
            **{k: d[k] for k in ("team_id", "team_name", "games", "wins", "losses", "draws", "win_pct")},
            games_behind=round(max(gb, 0.0), 1),
            recent_5=recent_5,
            streak=streak,
        ))

    return StandingsResponse(season=season, standings=standings)


def _calc_streak(results: list[str]) -> str:
    if not results:
        return ""
    first = results[0]
    count = 1
    for r in results[1:]:
        if r == first:
            count += 1
        else:
            break
    label = {"W": "연승", "L": "연패", "D": "무"}
    return f"{count}{label.get(first, '')}"


# ── 팀스탯 비교 ──────────────────────────────────────────

@router.get("/teams/comparison", response_model=TeamComparisonResponse)
def get_team_comparison(
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """팀스탯 종합 비교 카드 4개"""
    season = season or get_latest_season(db)
    cards = []

    # 공격력: 타자 OPS 팀 평균 (PA >= 50 필터)
    stmt = text("""
        SELECT bs.team_id, t.short_name AS team_name,
               AVG(bs.ops) AS value
        FROM batter_season bs
        JOIN teams t ON bs.team_id = t.id
        WHERE bs.season = :season AND bs.pa >= 50
        GROUP BY bs.team_id
        ORDER BY value DESC
    """)
    rows = db.execute(stmt, {"season": season}).mappings().all()
    cards.append(_build_card("공격력", "team_ops", rows))

    # 투수력: 팀 ERA (ip_outs >= 30 필터)
    stmt = text("""
        SELECT ps.team_id, t.short_name AS team_name,
               SUM(ps.er) * 9.0 / (SUM(ps.ip_outs) / 3.0) AS value
        FROM pitcher_season ps
        JOIN teams t ON ps.team_id = t.id
        WHERE ps.season = :season AND ps.ip_outs >= 30
        GROUP BY ps.team_id
        ORDER BY value ASC
    """)
    rows = db.execute(stmt, {"season": season}).mappings().all()
    cards.append(_build_card("투수력", "team_era", rows))

    # 수비력: 팀 WHIP
    stmt = text("""
        SELECT ps.team_id, t.short_name AS team_name,
               (SUM(ps.hits_allowed) + SUM(ps.bb_allowed)) * 1.0
               / (SUM(ps.ip_outs) / 3.0) AS value
        FROM pitcher_season ps
        JOIN teams t ON ps.team_id = t.id
        WHERE ps.season = :season AND ps.ip_outs >= 30
        GROUP BY ps.team_id
        ORDER BY value ASC
    """)
    rows = db.execute(stmt, {"season": season}).mappings().all()
    cards.append(_build_card("수비력", "team_whip", rows))

    # 주루: 팀 도루 합산
    stmt = text("""
        SELECT bs.team_id, t.short_name AS team_name,
               SUM(bs.sb) AS value
        FROM batter_season bs
        JOIN teams t ON bs.team_id = t.id
        WHERE bs.season = :season
        GROUP BY bs.team_id
        ORDER BY value DESC
    """)
    rows = db.execute(stmt, {"season": season}).mappings().all()
    cards.append(_build_card("주루", "team_sb", rows))

    return TeamComparisonResponse(season=season, cards=cards)


def _build_card(category: str, stat_name: str, rows) -> TeamCompareCard:
    rankings = [
        TeamRankItem(
            rank=i + 1,
            team_id=r["team_id"],
            team_name=r["team_name"],
            value=round(r["value"], 4) if r["value"] is not None else None,
        )
        for i, r in enumerate(rows)
    ]
    leader = rankings[0] if rankings else None
    return TeamCompareCard(
        category=category,
        stat_name=stat_name,
        leader_team=leader.team_name if leader else "",
        leader_value=leader.value if leader else None,
        rankings=rankings,
    )


# ── 선수 TOP N ───────────────────────────────────────────

@router.get("/rankings/top", response_model=TopRankingsResponse)
def get_top_rankings(
    stat: str = Query("avg"),
    limit: int = Query(5, ge=1, le=50),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """주요 지표별 선수 TOP N"""
    season = season or get_latest_season(db)

    is_pitcher = stat in _PITCHER_STATS
    is_batter = stat in _BATTER_STATS

    if not is_batter and not is_pitcher:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 지표: {stat}")

    if is_pitcher:
        asc = stat in _PITCHER_ASC
        order_dir = "ASC" if asc else "DESC"
        stmt = text(f"""
            SELECT ps.player_id, p.name AS player_name,
                   t.short_name AS team_name, ps.{stat} AS value
            FROM pitcher_season ps
            JOIN players p ON ps.player_id = p.id
            JOIN teams t ON ps.team_id = t.id
            WHERE ps.season = :season AND ps.ip_outs >= 30
              AND ps.{stat} IS NOT NULL
            ORDER BY ps.{stat} {order_dir}
            LIMIT :limit
        """)
        player_type = "pitcher"
    else:
        stmt = text(f"""
            SELECT bs.player_id, p.name AS player_name,
                   t.short_name AS team_name, bs.{stat} AS value
            FROM batter_season bs
            JOIN players p ON bs.player_id = p.id
            JOIN teams t ON bs.team_id = t.id
            WHERE bs.season = :season AND bs.pa >= 50
              AND bs.{stat} IS NOT NULL
            ORDER BY bs.{stat} DESC
            LIMIT :limit
        """)
        player_type = "batter"

    rows = db.execute(stmt, {"season": season, "limit": limit}).mappings().all()

    rankings = [
        TopRankItem(
            rank=i + 1,
            player_id=r["player_id"],
            player_name=r["player_name"],
            team_name=r["team_name"],
            value=r["value"],
        )
        for i, r in enumerate(rows)
    ]

    return TopRankingsResponse(
        season=season,
        stat=stat,
        player_type=player_type,
        limit=limit,
        rankings=rankings,
    )
