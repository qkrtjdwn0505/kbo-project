"""일정/결과 API"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from src.backend.database import get_db
from src.backend.schemas.game import (
    BatterLineupItem,
    DatesResponse,
    GameDetail,
    GameItem,
    LineupResponse,
    PitcherLineupItem,
    PitcherResult,
    ScheduleResponse,
    TeamInfo,
    TopBatter,
)

router = APIRouter()


# ── 헬퍼 ─────────────────────────────────────────────────

_IP_FRAC = {0: "0", 1: "1/3", 2: "2/3"}


def _outs_to_ip(ip_outs: Optional[int]) -> str:
    if not ip_outs:
        return "0"
    full = ip_outs // 3
    frac = ip_outs % 3
    return f"{full} {_IP_FRAC[frac]}" if frac else str(full)


def _build_game_item(row, win_map: dict, lose_map: dict) -> GameItem:
    gid = row[0]
    return GameItem(
        id=gid,
        date=row[1],
        time=row[2],
        stadium=row[3],
        status=row[4] or "final",
        home_score=row[5],
        away_score=row[6],
        home_team=TeamInfo(id=row[7], name=row[8], short_name=row[9]),
        away_team=TeamInfo(id=row[10], name=row[11], short_name=row[12]),
        winning_pitcher=win_map.get(gid),
        losing_pitcher=lose_map.get(gid),
    )


def _get_pitcher_decisions(db: Session, game_ids: list[int]) -> tuple[dict, dict]:
    if not game_ids:
        return {}, {}
    placeholders = ",".join(str(g) for g in game_ids)
    rows = db.execute(
        text(f"""
            SELECT ps.game_id, ps.decision, p.name
            FROM pitcher_stats ps
            JOIN players p ON ps.player_id = p.id
            WHERE ps.game_id IN ({placeholders})
              AND ps.decision IN ('승', '패')
        """),
    ).fetchall()
    win_map, lose_map = {}, {}
    for gid, decision, name in rows:
        if decision == "승":
            win_map[gid] = name
        elif decision == "패":
            lose_map[gid] = name
    return win_map, lose_map


def _query_games_on_date(db: Session, date: str):
    return db.execute(
        text("""
            SELECT
                g.id, g.date, g.time, g.stadium, g.status,
                g.home_score, g.away_score,
                g.home_team_id, ht.name, ht.short_name,
                g.away_team_id, at_.name, at_.short_name
            FROM games g
            JOIN teams ht  ON g.home_team_id = ht.id
            JOIN teams at_ ON g.away_team_id = at_.id
            WHERE g.date = :date
            ORDER BY g.time
        """),
        {"date": date},
    ).fetchall()


# ── 날짜 목록 ─────────────────────────────────────────────

@router.get("/games/dates", response_model=DatesResponse)
def get_game_dates(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """해당 월에 경기가 있는 날짜 목록 (캘린더 점 표시용)"""
    rows = db.execute(
        text("""
            SELECT DISTINCT date FROM games
            WHERE date LIKE :prefix AND status IN ('final', 'scheduled', 'in_progress')
            ORDER BY date
        """),
        {"prefix": f"{month}%"},
    ).fetchall()
    return DatesResponse(month=month, dates=[r[0] for r in rows])


# ── 날짜별 경기 목록 ──────────────────────────────────────

@router.get("/games/schedule", response_model=ScheduleResponse)
def get_schedule(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """해당 날짜 경기 목록 + 승/패 투수"""
    rows = _query_games_on_date(db, date)
    game_ids = [r[0] for r in rows]
    win_map, lose_map = _get_pitcher_decisions(db, game_ids)
    return ScheduleResponse(
        date=date,
        games=[_build_game_item(r, win_map, lose_map) for r in rows],
    )


# ── 경기 상세 ─────────────────────────────────────────────

@router.get("/games/{game_id}/detail", response_model=GameDetail)
def get_game_detail(
    game_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """경기 상세 — 최종 스코어 + 주요 타자/투수"""
    rows = db.execute(
        text("""
            SELECT
                g.id, g.date, g.time, g.stadium, g.status,
                g.home_score, g.away_score,
                g.home_team_id, ht.name, ht.short_name,
                g.away_team_id, at_.name, at_.short_name
            FROM games g
            JOIN teams ht  ON g.home_team_id = ht.id
            JOIN teams at_ ON g.away_team_id = at_.id
            WHERE g.id = :gid
        """),
        {"gid": game_id},
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="경기를 찾을 수 없습니다")

    win_map, lose_map = _get_pitcher_decisions(db, [game_id])
    game_item = _build_game_item(rows[0], win_map, lose_map)

    # 투수 기록 (승/패/세)
    p_rows = db.execute(
        text("""
            SELECT ps.decision, p.id, p.name, t.short_name,
                   ps.ip_outs, ps.er, ps.so_count
            FROM pitcher_stats ps
            JOIN players p ON ps.player_id = p.id
            JOIN teams t   ON ps.team_id   = t.id
            WHERE ps.game_id = :gid AND ps.decision IN ('승','패','세')
        """),
        {"gid": game_id},
    ).fetchall()

    def _pr(r) -> PitcherResult:
        return PitcherResult(
            player_id=r[1], name=r[2], team=r[3],
            ip=_outs_to_ip(r[4]), er=r[5] or 0, so=r[6] or 0,
        )

    win_p = lose_p = save_p = None
    for r in p_rows:
        if r[0] == "승":
            win_p = _pr(r)
        elif r[0] == "패":
            lose_p = _pr(r)
        elif r[0] == "세":
            save_p = _pr(r)

    # 주요 타자 (홈런·타점 기준 상위 5명)
    b_rows = db.execute(
        text("""
            SELECT p.id, p.name, t.short_name,
                   bs.ab, bs.hits, bs.hr, bs.rbi
            FROM batter_stats bs
            JOIN players p ON bs.player_id = p.id
            JOIN teams t   ON bs.team_id   = t.id
            WHERE bs.game_id = :gid AND bs.hits > 0
            ORDER BY (bs.hr * 3 + bs.hits + bs.rbi) DESC
            LIMIT 5
        """),
        {"gid": game_id},
    ).fetchall()

    top_batters = [
        TopBatter(
            player_id=r[0], name=r[1], team=r[2],
            ab=r[3] or 0, hits=r[4] or 0, hr=r[5] or 0, rbi=r[6] or 0,
        )
        for r in b_rows
    ]

    return GameDetail(
        game=game_item,
        top_batters=top_batters,
        winning_pitcher=win_p,
        losing_pitcher=lose_p,
        save_pitcher=save_p,
    )


# ── 경기 라인업 ────────────────────────────────────────────

@router.get("/games/{game_id}/lineups", response_model=LineupResponse)
def get_game_lineups(
    game_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """경기 라인업 — 양팀 타자(게임별 집계) + 투수 등판 기록"""
    row = db.execute(
        text("""
            SELECT
                g.home_team_id, ht.name, ht.short_name,
                g.away_team_id, at_.name, at_.short_name
            FROM games g
            JOIN teams ht  ON g.home_team_id = ht.id
            JOIN teams at_ ON g.away_team_id = at_.id
            WHERE g.id = :gid
        """),
        {"gid": game_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="경기를 찾을 수 없습니다")

    home_team = TeamInfo(id=row[0], name=row[1], short_name=row[2])
    away_team = TeamInfo(id=row[3], name=row[4], short_name=row[5])

    def _get_batters(team_id: int) -> list[BatterLineupItem]:
        rows = db.execute(
            text("""
                SELECT bs.player_id, p.name, p.position,
                       SUM(bs.ab), SUM(bs.hits), SUM(bs.rbi),
                       SUM(bs.runs), SUM(bs.hr), SUM(bs.bb), SUM(bs.so)
                FROM batter_stats bs
                JOIN players p ON bs.player_id = p.id
                WHERE bs.game_id = :gid AND bs.team_id = :tid
                GROUP BY bs.player_id, p.name, p.position
                ORDER BY SUM(bs.ab) DESC, p.name
            """),
            {"gid": game_id, "tid": team_id},
        ).fetchall()
        return [
            BatterLineupItem(
                player_id=r[0], player_name=r[1], position=r[2],
                ab=r[3] or 0, hits=r[4] or 0, rbi=r[5] or 0,
                runs=r[6] or 0, hr=r[7] or 0, bb=r[8] or 0, so=r[9] or 0,
            )
            for r in rows
        ]

    def _get_pitchers(team_id: int) -> list[PitcherLineupItem]:
        rows = db.execute(
            text("""
                SELECT ps.player_id, p.name, ps.ip_outs,
                       ps.hits_allowed, ps.er, ps.bb_allowed, ps.so_count,
                       ps.decision, ps.is_starter
                FROM pitcher_stats ps
                JOIN players p ON ps.player_id = p.id
                WHERE ps.game_id = :gid AND ps.team_id = :tid
                ORDER BY ps.id
            """),
            {"gid": game_id, "tid": team_id},
        ).fetchall()
        return [
            PitcherLineupItem(
                player_id=r[0], player_name=r[1],
                ip=_outs_to_ip(r[2]),
                hits_allowed=r[3] or 0, er=r[4] or 0,
                bb_allowed=r[5] or 0, so_count=r[6] or 0,
                decision=r[7], is_starter=bool(r[8]),
            )
            for r in rows
        ]

    return LineupResponse(
        game_id=game_id,
        home_team=home_team,
        away_team=away_team,
        home_batters=_get_batters(home_team.id),
        away_batters=_get_batters(away_team.id),
        home_pitchers=_get_pitchers(home_team.id),
        away_pitchers=_get_pitchers(away_team.id),
    )


# ── 실시간 스코어 SSE ──────────────────────────────────────

_logger = logging.getLogger(__name__)

_INNING_HALF = {"T": "초", "B": "말"}


@router.get("/games/live")
async def live_scores(request: Request):
    """SSE 스트림 — 30초마다 오늘 경기 실시간 스코어 전송"""

    async def event_generator():
        from src.data.collectors.kbo_data_collector import KBODataCollector

        collector = KBODataCollector(delay=0.5)
        while True:
            if await request.is_disconnected():
                _logger.info("SSE 클라이언트 연결 해제")
                break
            date_str = datetime.now().strftime("%Y%m%d")
            try:
                games = collector.get_game_list(date_str)
                live_data = []
                for g in games:
                    inning = g.get("GAME_INN_NO")
                    tb = g.get("GAME_TB_SC")
                    live_data.append({
                        "game_id": g["game_id"],
                        "home_team": g["home_team"],
                        "away_team": g["away_team"],
                        "home_score": g["home_score"],
                        "away_score": g["away_score"],
                        "status_code": str(g["status_code"]),
                        "inning": int(inning) if inning else None,
                        "inning_half": _INNING_HALF.get(tb, ""),
                    })
                yield {
                    "event": "scores",
                    "data": json.dumps(live_data, ensure_ascii=False),
                }
            except Exception as e:
                _logger.warning("SSE 폴링 에러: %s", e)
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}, ensure_ascii=False),
                }
            await asyncio.sleep(30)

    return EventSourceResponse(event_generator())
