"""팀/순위 API Pydantic 응답 모델"""

from typing import Optional
from pydantic import BaseModel


# ── 팀 순위표 ────────────────────────────────────────────

class TeamStanding(BaseModel):
    rank: int
    team_id: int
    team_name: str
    games: int
    wins: int
    losses: int
    draws: int
    win_pct: float
    games_behind: float
    recent_5: list[str] = []   # T-2.6에서 구현
    streak: str = ""            # T-2.6에서 구현


class StandingsResponse(BaseModel):
    season: int
    standings: list[TeamStanding]


# ── 팀스탯 비교 ──────────────────────────────────────────

class TeamRankItem(BaseModel):
    rank: int
    team_id: int
    team_name: str
    value: Optional[float] = None


class TeamCompareCard(BaseModel):
    category: str       # "공격력", "투수력", "수비력", "주루"
    stat_name: str      # "team_ops", "team_era", "team_whip", "team_sb"
    leader_team: str    # 1위 팀명
    leader_value: Optional[float] = None
    rankings: list[TeamRankItem]


class TeamComparisonResponse(BaseModel):
    season: int
    cards: list[TeamCompareCard]


# ── 선수 TOP N ───────────────────────────────────────────

class TopRankItem(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_name: str
    value: Optional[float] = None


class TopRankingsResponse(BaseModel):
    season: int
    stat: str
    player_type: str    # "batter" or "pitcher"
    limit: int
    rankings: list[TopRankItem]
