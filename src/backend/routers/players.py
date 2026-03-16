"""선수 API — 검색, 세부정보, 기록 조회"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Optional

from src.backend.database import get_db

router = APIRouter()


@router.get("/players/search")
def search_players(
    q: str = Query(..., min_length=2, description="검색어 (2글자 이상)"),
    limit: int = Query(10, description="결과 수"),
    db: Session = Depends(get_db),
):
    """선수 검색 — 자동완성용"""
    # TODO: T-2.4에서 구현
    return {"query": q, "results": [], "message": "T-2.4에서 구현 예정"}


@router.get("/players/{player_id}")
def get_player(
    player_id: int = Path(..., description="선수 ID"),
    db: Session = Depends(get_db),
):
    """선수 프로필 + 시즌 기본 정보"""
    # TODO: T-2.4에서 구현
    return {"player_id": player_id, "message": "T-2.4에서 구현 예정"}


@router.get("/players/{player_id}/classic")
def get_player_classic(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """클래식 스탯 탭"""
    # TODO: T-2.4에서 구현
    return {"player_id": player_id, "tab": "classic", "message": "T-2.4에서 구현 예정"}


@router.get("/players/{player_id}/sabermetrics")
def get_player_sabermetrics(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """세이버메트릭스 탭"""
    # TODO: T-2.4에서 구현
    return {"player_id": player_id, "tab": "sabermetrics", "message": "T-2.4에서 구현 예정"}


@router.get("/players/{player_id}/splits")
def get_player_splits(
    player_id: int = Path(...),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """스플릿 탭"""
    # TODO: T-2.4에서 구현
    return {"player_id": player_id, "tab": "splits", "message": "T-2.4에서 구현 예정"}


@router.get("/players/list")
def list_players(
    team_id: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    sort_by: str = Query("avg", description="정렬 기준 지표"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """선수 목록 — 기록 조회 (REQ-06)"""
    # TODO: T-5.3에서 구현
    return {"results": [], "total": 0, "message": "T-5.3에서 구현 예정"}
