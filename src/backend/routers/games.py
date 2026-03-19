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
    InningScores,
    LineupResponse,
    PitcherLineupItem,
    PitcherResult,
    ScoreboardSummary,
    ScheduleResponse,
    TeamInfo,
    TopBatter,
)

router = APIRouter()

# DB team_id → KBO 영문코드 (game_id 복원용)
_TEAM_ID_TO_CODE = {
    1: "HT", 2: "SS", 3: "LG", 4: "OB", 5: "KT",
    6: "SK", 7: "LT", 8: "HH", 9: "NC", 10: "WO",
}


def _fetch_scoreboard(db_game) -> tuple:
    """DB game row로부터 KBO API 스코어보드 조회. (InningScores, ScoreboardSummary) 또는 (None, None)"""
    from src.data.collectors.kbo_data_collector import KBODataCollector

    game_date = db_game[1]  # "YYYY-MM-DD"
    home_tid = db_game[7]
    away_tid = db_game[10]

    date_str = game_date.replace("-", "")
    away_code = _TEAM_ID_TO_CODE.get(away_tid, "")
    home_code = _TEAM_ID_TO_CODE.get(home_tid, "")
    if not away_code or not home_code:
        return None, None

    kbo_game_id = f"{date_str}{away_code}{home_code}0"

    # sr_id 결정: 날짜로 game_list에서 찾기 (캐시 없으므로 직접 호출)
    collector = KBODataCollector(delay=0.3)
    games = collector.get_game_list(date_str)
    matched = next((g for g in games if g["game_id"] == kbo_game_id), None)

    if not matched:
        # 더블헤더 등으로 ID가 다를 수 있음 — 팀 매칭으로 재시도
        matched = next(
            (g for g in games
             if g["home_team_id"] == home_tid and g["away_team_id"] == away_tid),
            None,
        )

    if not matched:
        return None, None

    sb = collector.get_scoreboard(matched["game_id"], matched["sr_id"], matched["season"])
    if not sb:
        return None, None

    inning = InningScores(
        away=sb["inning_scores"]["away"],
        home=sb["inning_scores"]["home"],
    )
    summary = ScoreboardSummary(
        away=sb["summary"]["away"],
        home=sb["summary"]["home"],
    )
    return inning, summary


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

    # 이닝별 스코어보드 (KBO API에서 가져오기)
    inning_scores = None
    summary = None
    if game_item.status in ("final", "in_progress"):
        try:
            inning_scores, summary = _fetch_scoreboard(rows[0])
        except Exception as e:
            _logger.warning("스코어보드 조회 실패 game_id=%d: %s", game_id, e)

    return GameDetail(
        game=game_item,
        top_batters=top_batters,
        winning_pitcher=win_p,
        losing_pitcher=lose_p,
        save_pitcher=save_p,
        inning_scores=inning_scores,
        summary=summary,
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
    """SSE 스트림 — 점수 30초, 박스스코어 60초 간격 전송"""

    async def event_generator():
        from src.data.collectors.kbo_data_collector import KBODataCollector

        collector = KBODataCollector(delay=0.5)
        tick = 0  # 0, 1, 0, 1... — 짝수 틱에만 박스스코어

        while True:
            if await request.is_disconnected():
                _logger.info("SSE 클라이언트 연결 해제")
                break

            date_str = datetime.now().strftime("%Y%m%d")
            try:
                games = collector.get_game_list(date_str)
                live_data = []
                live_game_ids = []
                for g in games:
                    inning = g.get("GAME_INN_NO")
                    tb = g.get("GAME_TB_SC")
                    status = str(g["status_code"])
                    live_data.append({
                        "game_id": g["game_id"],
                        "home_team": g["home_team"],
                        "away_team": g["away_team"],
                        "home_score": g["home_score"],
                        "away_score": g["away_score"],
                        "status_code": status,
                        "inning": int(inning) if inning else None,
                        "inning_half": _INNING_HALF.get(tb, ""),
                    })
                    if status == "2":
                        live_game_ids.append(g)

                # scores 이벤트 (매 30초)
                yield {
                    "event": "scores",
                    "data": json.dumps(live_data, ensure_ascii=False),
                }

                # boxscore 이벤트 (매 60초 = 짝수 틱, 진행 중 경기만)
                if tick % 2 == 0 and live_game_ids:
                    box_list = []
                    for g in live_game_ids:
                        try:
                            box = collector.get_boxscore(
                                g["game_id"], g["sr_id"], g["season"]
                            )
                            if not box:
                                continue
                            sb = collector.get_scoreboard(
                                g["game_id"], g["sr_id"], g["season"]
                            )
                            box_list.append({
                                "game_id": g["game_id"],
                                "home_team": g["home_team"],
                                "away_team": g["away_team"],
                                "inning_scores": sb["inning_scores"] if sb else None,
                                "summary": sb["summary"] if sb else None,
                                "home_batters": box["home_batters"],
                                "away_batters": box["away_batters"],
                                "home_pitchers": box["home_pitchers"],
                                "away_pitchers": box["away_pitchers"],
                            })
                        except Exception as e:
                            _logger.warning("박스스코어 수집 실패 %s: %s", g["game_id"], e)
                    if box_list:
                        yield {
                            "event": "boxscore",
                            "data": json.dumps(box_list, ensure_ascii=False),
                        }

            except Exception as e:
                _logger.warning("SSE 폴링 에러: %s", e)
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}, ensure_ascii=False),
                }

            tick += 1
            await asyncio.sleep(30)

    return EventSourceResponse(event_generator())
