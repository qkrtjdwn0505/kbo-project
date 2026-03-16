"""일정/결과 API (2순위)"""

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional

from src.backend.database import get_db

router = APIRouter()


@router.get("/games/today")
def get_today_games(db: Session = Depends(get_db)):
    """오늘 경기 목록"""
    # TODO: T-5.1에서 구현
    return {"games": [], "message": "T-5.1에서 구현 예정"}


@router.get("/games/date/{date}")
def get_games_by_date(
    date: str = Path(..., description="날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """특정 날짜 경기 목록"""
    # TODO: T-5.1에서 구현
    return {"date": date, "games": [], "message": "T-5.1에서 구현 예정"}


@router.get("/games/{game_id}")
def get_game_detail(
    game_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """경기 상세 (스코어보드, 박스스코어)"""
    # TODO: T-5.1에서 구현
    return {"game_id": game_id, "message": "T-5.1에서 구현 예정"}


@router.get("/games/{game_id}/preview")
def get_game_preview(
    game_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """선발투수 프리뷰"""
    # TODO: T-5.1에서 구현
    return {"game_id": game_id, "message": "T-5.1에서 구현 예정"}


@router.get("/games/{game_id}/lineups")
def get_game_lineups(
    game_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """경기별 풀 라인업 (선발+불펜+벤치)"""
    # TODO: T-5.2에서 구현
    return {"game_id": game_id, "lineups": [], "message": "T-5.2에서 구현 예정"}
