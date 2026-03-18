"""일정/결과 API Pydantic 응답 모델"""

from typing import Optional
from pydantic import BaseModel


class TeamInfo(BaseModel):
    id: int
    name: str
    short_name: str


class PitcherResult(BaseModel):
    player_id: int
    name: str
    team: str
    ip: str
    er: int
    so: int


class TopBatter(BaseModel):
    player_id: int
    name: str
    team: str
    ab: int
    hits: int
    hr: int
    rbi: int


class GameItem(BaseModel):
    id: int
    date: str
    time: Optional[str]
    stadium: Optional[str]
    home_team: TeamInfo
    away_team: TeamInfo
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    winning_pitcher: Optional[str] = None
    losing_pitcher: Optional[str] = None


class ScheduleResponse(BaseModel):
    date: str
    games: list[GameItem]


class DatesResponse(BaseModel):
    month: str
    dates: list[str]


class GameDetail(BaseModel):
    game: GameItem
    top_batters: list[TopBatter]
    winning_pitcher: Optional[PitcherResult] = None
    losing_pitcher: Optional[PitcherResult] = None
    save_pitcher: Optional[PitcherResult] = None


class BatterLineupItem(BaseModel):
    player_id: int
    player_name: str
    position: Optional[str] = None
    ab: int
    hits: int
    rbi: int
    runs: int
    hr: int
    bb: int
    so: int


class PitcherLineupItem(BaseModel):
    player_id: int
    player_name: str
    ip: str
    hits_allowed: int
    er: int
    bb_allowed: int
    so_count: int
    decision: Optional[str] = None
    is_starter: bool = False


class LineupResponse(BaseModel):
    game_id: int
    home_team: TeamInfo
    away_team: TeamInfo
    home_batters: list[BatterLineupItem]
    away_batters: list[BatterLineupItem]
    home_pitchers: list[PitcherLineupItem]
    away_pitchers: list[PitcherLineupItem]
