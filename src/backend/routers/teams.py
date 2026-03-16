"""팀/순위 API"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.backend.database import get_db

router = APIRouter()


@router.get("/teams/standings")
def get_standings(
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """팀 순위표"""
    # TODO: T-2.5에서 구현
    return {"standings": [], "message": "T-2.5에서 구현 예정"}


@router.get("/teams/comparison")
def get_team_comparison(
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """팀스탯 종합 비교 카드 4개 (공격력/투수력/수비력/주루)"""
    # TODO: T-2.5에서 구현
    return {"comparison": [], "message": "T-2.5에서 구현 예정"}


@router.get("/rankings/top")
def get_top_rankings(
    stat: str = Query("avg", description="지표"),
    limit: int = Query(5),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """주요 지표별 선수 TOP N"""
    # TODO: T-2.5에서 구현
    return {"stat": stat, "rankings": [], "message": "T-2.5에서 구현 예정"}
