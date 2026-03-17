"""선수 API — 검색, 프로필, 기록 3탭, 선수 목록"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.backend.database import get_db, get_latest_season
from src.backend.models import batter_season, pitcher_season, players, teams
from src.backend.schemas.player import (
    BatterClassicStats,
    BatterSaberStats,
    ClassicStatsResponse,
    PitcherClassicStats,
    PitcherSaberStats,
    PlayerListItem,
    PlayerListResponse,
    PlayerProfile,
    PlayerSearchItem,
    PlayerSearchResponse,
    SaberStatsResponse,
    SplitPair,
    SplitsStatsResponse,
)

router = APIRouter()

# ── 화이트리스트 ────────────────────────────────────────

_BATTER_SORT_COLS = {
    "avg", "ops", "obp", "slg", "hr", "rbi", "runs", "sb",
    "bb", "so", "pa", "hits", "woba", "wrc_plus", "war", "babip",
}
_PITCHER_SORT_COLS = {
    "era", "wins", "saves", "holds", "so_count", "whip",
    "fip", "xfip", "war", "bb_allowed", "hr_allowed",
}


# ── 유틸 ────────────────────────────────────────────────

def _player_type(position: str) -> str:
    return "pitcher" if position == "투수" else "batter"


def _ip_outs_to_display(ip_outs: int) -> str:
    """아웃 카운트 → 이닝 표시 문자열. 18 → '6.0', 14 → '4.2'"""
    return f"{ip_outs // 3}.{ip_outs % 3}"




def _get_player_or_404(db: Session, player_id: int) -> dict:
    """선수 + 팀명 조회. 없으면 404."""
    stmt = (
        select(
            players.c.id,
            players.c.name,
            players.c.position,
            players.c.back_number,
            players.c.birth_date,
            players.c.height,
            players.c.weight,
            players.c.bat_hand,
            players.c.throw_hand,
            teams.c.short_name.label("team_name"),
        )
        .select_from(players.join(teams, players.c.team_id == teams.c.id))
        .where(players.c.id == player_id)
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"선수를 찾을 수 없습니다: {player_id}")
    return dict(row)


# ── 검색 ────────────────────────────────────────────────

@router.get("/players/search", response_model=PlayerSearchResponse)
def search_players(
    q: str = Query(..., min_length=2, description="검색어 (2글자 이상)"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """선수 검색 — 자동완성용"""
    stmt = (
        select(
            players.c.id,
            players.c.name,
            players.c.position,
            players.c.back_number,
            teams.c.short_name.label("team_name"),
        )
        .select_from(players.join(teams, players.c.team_id == teams.c.id))
        .where(players.c.name.like(f"%{q}%"))
        .where(players.c.is_active == True)
        .order_by(players.c.name)
        .limit(limit)
    )
    rows = db.execute(stmt).mappings().all()
    return PlayerSearchResponse(
        query=q,
        results=[PlayerSearchItem(**dict(r)) for r in rows],
    )


# ── 선수 목록 ────────────────────────────────────────────
# /players/list 는 /players/{player_id} 앞에 등록

@router.get("/players/list", response_model=PlayerListResponse)
def list_players(
    team_id: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    sort_by: str = Query("avg"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """선수 목록 — 기록 조회"""
    if sort_order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort_order는 asc 또는 desc")

    season = season or get_latest_season(db)
    is_pitcher = position == "투수"

    if is_pitcher:
        if sort_by not in _PITCHER_SORT_COLS:
            sort_by = "era"
        tbl = pitcher_season
    else:
        if sort_by not in _BATTER_SORT_COLS:
            sort_by = "avg"
        tbl = batter_season

    sort_col = tbl.c[sort_by]
    order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    offset = (page - 1) * per_page

    base = (
        select(
            players.c.id,
            players.c.name,
            players.c.position,
            teams.c.short_name.label("team_name"),
            sort_col.label("primary_stat"),
            *(
                [tbl.c.avg, tbl.c.hr, tbl.c.rbi, tbl.c.ops]
                if not is_pitcher
                else []
            ),
        )
        .select_from(
            tbl.join(players, tbl.c.player_id == players.c.id)
            .join(teams, tbl.c.team_id == teams.c.id)
        )
        .where(tbl.c.season == season)
    )
    if team_id is not None:
        base = base.where(tbl.c.team_id == team_id)
    if position is not None:
        base = base.where(players.c.position == position)

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(base.order_by(order_expr).limit(per_page).offset(offset)).mappings().all()

    results = []
    for r in rows:
        d = dict(r)
        results.append(PlayerListItem(
            id=d["id"],
            name=d["name"],
            team_name=d["team_name"],
            position=d["position"],
            player_type=_player_type(d["position"]),
            primary_stat=d.get("primary_stat"),
            avg=d.get("avg"),
            hr=d.get("hr"),
            rbi=d.get("rbi"),
            ops=d.get("ops"),
        ))

    return PlayerListResponse(
        results=results,
        total=total,
        page=page,
        per_page=per_page,
        season=season,
    )


# ── 프로필 ───────────────────────────────────────────────

@router.get("/players/{player_id}", response_model=PlayerProfile)
def get_player(
    player_id: int = Path(..., description="선수 ID"),
    db: Session = Depends(get_db),
):
    """선수 프로필"""
    p = _get_player_or_404(db, player_id)
    return PlayerProfile(
        id=p["id"],
        name=p["name"],
        team_name=p["team_name"],
        position=p["position"],
        player_type=_player_type(p["position"]),
        back_number=p.get("back_number"),
        birth_date=p.get("birth_date"),
        height=p.get("height"),
        weight=p.get("weight"),
        bat_hand=p.get("bat_hand"),
        throw_hand=p.get("throw_hand"),
    )


# ── 클래식 스탯 ─────────────────────────────────────────

@router.get("/players/{player_id}/classic", response_model=ClassicStatsResponse)
def get_player_classic(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """클래식 스탯 탭"""
    p = _get_player_or_404(db, player_id)
    season = season or get_latest_season(db)
    ptype = _player_type(p["position"])

    if ptype == "batter":
        stmt = select(batter_season).where(
            batter_season.c.player_id == player_id,
            batter_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        stats = BatterClassicStats(
            season=row["season"],
            games=row["games"] or 0,
            pa=row["pa"] or 0,
            ab=row["ab"] or 0,
            hits=row["hits"] or 0,
            doubles=row["doubles"] or 0,
            triples=row["triples"] or 0,
            hr=row["hr"] or 0,
            rbi=row["rbi"] or 0,
            runs=row["runs"] or 0,
            sb=row["sb"] or 0,
            cs=row["cs"] or 0,
            bb=row["bb"] or 0,
            hbp=row["hbp"] or 0,
            so=row["so"] or 0,
            gdp=row["gdp"] or 0,
            avg=row["avg"],
            obp=row["obp"],
            slg=row["slg"],
            ops=row["ops"],
        ).model_dump()
    else:
        stmt = select(pitcher_season).where(
            pitcher_season.c.player_id == player_id,
            pitcher_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        ip_outs = row["ip_outs"] or 0
        stats = PitcherClassicStats(
            season=row["season"],
            games=row["games"] or 0,
            wins=row["wins"] or 0,
            losses=row["losses"] or 0,
            saves=row["saves"] or 0,
            holds=row["holds"] or 0,
            ip_outs=ip_outs,
            ip_display=_ip_outs_to_display(ip_outs),
            hits_allowed=row["hits_allowed"] or 0,
            hr_allowed=row["hr_allowed"] or 0,
            bb_allowed=row["bb_allowed"] or 0,
            so_count=row["so_count"] or 0,
            er=row["er"] or 0,
            era=row["era"],
            whip=row["whip"],
        ).model_dump()

    return ClassicStatsResponse(
        player_id=player_id,
        player_name=p["name"],
        player_type=ptype,
        season=season,
        stats=stats,
    )


# ── 세이버메트릭스 ──────────────────────────────────────

@router.get("/players/{player_id}/sabermetrics", response_model=SaberStatsResponse)
def get_player_sabermetrics(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """세이버메트릭스 탭"""
    p = _get_player_or_404(db, player_id)
    season = season or get_latest_season(db)
    ptype = _player_type(p["position"])

    if ptype == "batter":
        stmt = select(batter_season).where(
            batter_season.c.player_id == player_id,
            batter_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        stats = BatterSaberStats(
            season=row["season"],
            woba=row["woba"],
            wrc_plus=row["wrc_plus"],
            war=row["war"],
            babip=row["babip"],
            iso=row["iso"],
            bb_pct=row["bb_pct"],
            k_pct=row["k_pct"],
        ).model_dump()
    else:
        stmt = select(pitcher_season).where(
            pitcher_season.c.player_id == player_id,
            pitcher_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        stats = PitcherSaberStats(
            season=row["season"],
            fip=row["fip"],
            xfip=row["xfip"],
            war=row["war"],
            babip=row["babip"],
            lob_pct=row["lob_pct"] or 0.0,
            k_per_9=row["k_per_9"],
            bb_per_9=row["bb_per_9"],
            hr_per_9=row["hr_per_9"],
            k_bb_ratio=row["k_bb_ratio"],
        ).model_dump()

    return SaberStatsResponse(
        player_id=player_id,
        player_name=p["name"],
        player_type=ptype,
        season=season,
        stats=stats,
    )


# ── 스플릿 ──────────────────────────────────────────────

@router.get("/players/{player_id}/splits", response_model=SplitsStatsResponse)
def get_player_splits(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """스플릿 탭"""
    p = _get_player_or_404(db, player_id)
    season = season or get_latest_season(db)
    ptype = _player_type(p["position"])

    if ptype == "batter":
        stmt = select(batter_season).where(
            batter_season.c.player_id == player_id,
            batter_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        splits = [
            SplitPair(label="vs 좌투", stat_name="ops", value=row["ops_vs_lhp"] or 0.0),
            SplitPair(label="vs 우투", stat_name="ops", value=row["ops_vs_rhp"] or 0.0),
            SplitPair(label="홈", stat_name="ops", value=row["ops_home"] or 0.0),
            SplitPair(label="원정", stat_name="ops", value=row["ops_away"] or 0.0),
            SplitPair(label="득점권", stat_name="ops", value=row["ops_risp"] or 0.0),
        ]
    else:
        stmt = select(pitcher_season).where(
            pitcher_season.c.player_id == player_id,
            pitcher_season.c.season == season,
        )
        row = db.execute(stmt).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="해당 시즌 기록이 없습니다")
        splits = [
            SplitPair(label="vs 좌타", stat_name="avg", value=row["avg_vs_lhb"] or 0.0),
            SplitPair(label="vs 우타", stat_name="avg", value=row["avg_vs_rhb"] or 0.0),
            SplitPair(label="홈", stat_name="era", value=row["era_home"] or 0.0),
            SplitPair(label="원정", stat_name="era", value=row["era_away"] or 0.0),
        ]

    return SplitsStatsResponse(
        player_id=player_id,
        player_name=p["name"],
        player_type=ptype,
        season=season,
        splits=splits,
    )
