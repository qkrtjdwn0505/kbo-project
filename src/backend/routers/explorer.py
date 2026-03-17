"""탐색기 API — 핵심 차별화 기능"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from src.backend.database import get_db
from src.backend.explorer.query_builder import build_explorer_query
from src.backend.schemas.explorer import ExplorerResponse

router = APIRouter()

VALID_TARGETS = {"batter", "pitcher", "pitcher_starter", "pitcher_bullpen", "team"}
VALID_SORTS = {"desc", "asc"}
VALID_LIMITS = {"5", "10", "20", "all"}


@router.get("/explorer", response_model=ExplorerResponse)
def explore_data(
    target: str = Query(..., description="대상: batter, pitcher, pitcher_starter, pitcher_bullpen, team"),
    condition: str = Query("all", description="조건: all, vs_lhb, vs_rhb, risp, home, away, night 등"),
    stat: str = Query(..., description="지표: avg, ops, woba, era, fip 등"),
    sort: str = Query("desc", description="정렬: desc, asc"),
    limit: str = Query("5", description="범위: 5, 10, 20, all"),
    season: Optional[int] = Query(None, description="시즌 (기본: 현재)"),
    db: Session = Depends(get_db),
) -> ExplorerResponse:
    """복합 조건 질의 실행 — 드롭다운 5단 조합"""
    if target not in VALID_TARGETS:
        raise HTTPException(status_code=400, detail=f"잘못된 대상: {target}")
    if sort not in VALID_SORTS:
        raise HTTPException(status_code=400, detail=f"잘못된 정렬: {sort}")
    if limit not in VALID_LIMITS:
        raise HTTPException(status_code=400, detail=f"잘못된 범위: {limit}")

    try:
        return build_explorer_query(
            db=db,
            target=target,
            condition=condition,
            stat=stat,
            sort=sort,
            limit=limit,
            season=season,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/explorer/options")
def get_explorer_options(
    target: str = Query(..., description="대상 선택에 따른 가용 지표 목록"),
):
    """대상 변경 시 가용 지표 목록 반환 (드롭다운 동적 변경용)"""
    options = {
        "batter": {
            "stats": ["avg", "hr", "rbi", "hits", "sb", "ops", "woba", "wrc_plus", "war", "babip", "iso", "bb_pct", "k_pct", "ops_risp"],
            "conditions": ["all", "vs_lhp", "vs_rhp", "risp", "bases_loaded", "no_runners", "inning_1_3", "inning_4_6", "inning_7_9", "home", "away", "weekday", "weekend", "night", "day", "leading", "tied", "trailing"],
        },
        "pitcher": {
            "stats": ["era", "wins", "losses", "whip", "so_count", "fip", "xfip", "k_per_9", "bb_per_9", "war", "babip", "lob_pct", "holds", "saves"],
            "conditions": ["all", "vs_lhb", "vs_rhb", "home", "away", "night", "day", "leading", "tied", "trailing"],
        },
        "team": {
            "stats": ["win_pct", "runs", "runs_allowed", "team_war", "team_fip", "team_wrc_plus", "team_drs", "comeback_pct", "close_game_pct"],
            "conditions": ["all", "home", "away", "weekday", "weekend"],
        },
    }

    target_key = target.replace("pitcher_starter", "pitcher").replace("pitcher_bullpen", "pitcher")
    if target_key not in options:
        raise HTTPException(status_code=400, detail=f"잘못된 대상: {target}")

    return options[target_key]
