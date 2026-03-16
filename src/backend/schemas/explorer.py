"""탐색기 API Pydantic 응답 모델"""

from pydantic import BaseModel
from typing import Optional


class ExplorerQuery(BaseModel):
    target: str
    condition: str
    stat: str
    sort: str
    limit: str
    season: int


class ExplorerResultItem(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_name: str
    primary_stat: Optional[float] = None
    secondary_stats: dict[str, Optional[float | int]] = {}


class ExplorerResponse(BaseModel):
    query: ExplorerQuery
    results: list[ExplorerResultItem]
    total_count: int
