"""선수 API Pydantic 응답 모델"""

from typing import Any, Optional
from pydantic import BaseModel


# ── 검색 ────────────────────────────────────────────────

class PlayerSearchItem(BaseModel):
    id: int
    name: str
    team_name: str
    position: str
    back_number: Optional[int] = None


class PlayerSearchResponse(BaseModel):
    query: str
    results: list[PlayerSearchItem]


# ── 프로필 ───────────────────────────────────────────────

class PlayerProfile(BaseModel):
    id: int
    name: str
    team_name: str
    position: str
    player_type: str  # "batter" or "pitcher"
    back_number: Optional[int] = None
    birth_date: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    bat_hand: Optional[str] = None
    throw_hand: Optional[str] = None


# ── 클래식 스탯 ─────────────────────────────────────────

class BatterClassicStats(BaseModel):
    season: int
    games: int
    pa: int
    ab: int
    hits: int
    doubles: int
    triples: int
    hr: int
    rbi: int
    runs: int
    sb: int
    cs: int
    bb: int
    hbp: int
    so: int
    gdp: int
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    ops: Optional[float] = None


class PitcherClassicStats(BaseModel):
    season: int
    games: int
    wins: int
    losses: int
    saves: int
    holds: int
    ip_outs: int
    ip_display: str  # "6.0", "4.2" 형식
    hits_allowed: int
    hr_allowed: int
    bb_allowed: int
    so_count: int
    er: int
    era: Optional[float] = None
    whip: Optional[float] = None


class ClassicStatsResponse(BaseModel):
    player_id: int
    player_name: str
    player_type: str
    season: int
    stats: dict[str, Any]


# ── 세이버메트릭스 ──────────────────────────────────────

class BatterSaberStats(BaseModel):
    season: int
    woba: Optional[float] = None
    wrc_plus: Optional[float] = None
    war: Optional[float] = None
    babip: Optional[float] = None
    iso: Optional[float] = None
    bb_pct: Optional[float] = None
    k_pct: Optional[float] = None


class PitcherSaberStats(BaseModel):
    season: int
    fip: Optional[float] = None
    xfip: Optional[float] = None
    war: Optional[float] = None
    babip: Optional[float] = None
    lob_pct: Optional[float] = None
    k_per_9: Optional[float] = None
    bb_per_9: Optional[float] = None
    hr_per_9: Optional[float] = None
    k_bb_ratio: Optional[float] = None


class SaberStatsResponse(BaseModel):
    player_id: int
    player_name: str
    player_type: str
    season: int
    stats: dict[str, Any]


# ── 스플릿 ──────────────────────────────────────────────

class SplitPair(BaseModel):
    label: str
    stat_name: str
    value: Optional[float] = None


class SplitsStatsResponse(BaseModel):
    player_id: int
    player_name: str
    player_type: str
    season: int
    splits: list[SplitPair]


# ── 선수 목록 ────────────────────────────────────────────

class PlayerListItem(BaseModel):
    id: int
    name: str
    team_name: str
    position: str
    player_type: str
    primary_stat: Optional[float] = None
    avg: Optional[float] = None
    hr: Optional[int] = None
    rbi: Optional[int] = None
    ops: Optional[float] = None


class PlayerListResponse(BaseModel):
    results: list[PlayerListItem]
    total: int
    page: int
    per_page: int
    season: int


# ── 기록 조회 ─────────────────────────────────────────────

class RecordPlayer(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team: str
    position: str
    games: int
    # 타자 클래식
    pa: Optional[int] = None
    ab: Optional[int] = None
    hits: Optional[int] = None
    hr: Optional[int] = None
    rbi: Optional[int] = None
    runs: Optional[int] = None
    sb: Optional[int] = None
    bb: Optional[int] = None
    so: Optional[int] = None
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    ops: Optional[float] = None
    # 타자 세이버
    woba: Optional[float] = None
    wrc_plus: Optional[float] = None
    war: Optional[float] = None
    babip: Optional[float] = None
    iso: Optional[float] = None
    bb_pct: Optional[float] = None
    k_pct: Optional[float] = None
    # 투수 클래식
    wins: Optional[int] = None
    losses: Optional[int] = None
    saves: Optional[int] = None
    holds: Optional[int] = None
    ip_display: Optional[str] = None
    hits_allowed: Optional[int] = None
    er: Optional[int] = None
    bb_allowed: Optional[int] = None
    so_count: Optional[int] = None
    era: Optional[float] = None
    whip: Optional[float] = None
    # 투수 세이버
    fip: Optional[float] = None
    xfip: Optional[float] = None
    lob_pct: Optional[float] = None
    k_per_9: Optional[float] = None
    bb_per_9: Optional[float] = None
    hr_per_9: Optional[float] = None
    k_bb_ratio: Optional[float] = None


class RecordsResponse(BaseModel):
    type: str
    season: int
    total: int
    page: int
    per_page: int
    players: list[RecordPlayer]
