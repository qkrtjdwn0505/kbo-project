"""일정/결과/라인업 API 테스트 — pytest + TestClient"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

SAMPLE_GAME_ID = 202509180351  # LG vs KT (2025-09-18)


# ── 날짜 목록 ─────────────────────────────────────────────

def test_game_dates_returns_list():
    """GET /games/dates?month=2025-09 → 200, dates 리스트"""
    r = client.get("/api/v1/games/dates?month=2025-09")
    assert r.status_code == 200
    data = r.json()
    assert data["month"] == "2025-09"
    assert isinstance(data["dates"], list)
    assert len(data["dates"]) > 0


def test_game_dates_format():
    """dates는 YYYY-MM-DD 형식"""
    r = client.get("/api/v1/games/dates?month=2025-09")
    dates = r.json()["dates"]
    for d in dates:
        assert len(d) == 10
        assert d[4] == "-" and d[7] == "-"


# ── 일정 ─────────────────────────────────────────────────

def test_schedule_returns_games():
    """GET /games/schedule?date=2025-09-18 → 경기 목록"""
    r = client.get("/api/v1/games/schedule?date=2025-09-18")
    assert r.status_code == 200
    data = r.json()
    assert data["date"] == "2025-09-18"
    assert len(data["games"]) > 0


def test_schedule_game_fields():
    """경기 항목에 팀 정보와 스코어 포함"""
    r = client.get("/api/v1/games/schedule?date=2025-09-18")
    game = r.json()["games"][0]
    assert "home_team" in game
    assert "away_team" in game
    assert "home_score" in game
    assert "away_score" in game


# ── 경기 상세 ─────────────────────────────────────────────

def test_game_detail_200():
    """GET /games/{id}/detail → 200"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/detail")
    assert r.status_code == 200


def test_game_detail_structure():
    """detail에 game, top_batters, 투수 정보 포함"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/detail")
    data = r.json()
    assert "game" in data
    assert "top_batters" in data
    assert isinstance(data["top_batters"], list)


def test_game_detail_404():
    """존재하지 않는 game_id → 404"""
    r = client.get("/api/v1/games/9999999/detail")
    assert r.status_code == 404


# ── 라인업 ────────────────────────────────────────────────

def test_lineup_200():
    """GET /games/{id}/lineups → 200"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/lineups")
    assert r.status_code == 200


def test_lineup_structure():
    """lineup에 home/away 팀 + 타자/투수 리스트 포함"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/lineups")
    data = r.json()
    assert data["game_id"] == SAMPLE_GAME_ID
    assert "home_team" in data
    assert "away_team" in data
    assert isinstance(data["home_batters"], list)
    assert isinstance(data["away_batters"], list)
    assert isinstance(data["home_pitchers"], list)
    assert isinstance(data["away_pitchers"], list)


def test_lineup_batters_have_stats():
    """타자 기록에 ab, hits, hr, rbi 포함"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/lineups")
    data = r.json()
    batters = data["home_batters"] + data["away_batters"]
    assert len(batters) > 0
    for b in batters:
        assert "ab" in b
        assert "hits" in b
        assert "hr" in b
        assert "rbi" in b


def test_lineup_pitchers_have_stats():
    """투수 기록에 ip, er, so_count 포함"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/lineups")
    data = r.json()
    pitchers = data["home_pitchers"] + data["away_pitchers"]
    assert len(pitchers) > 0
    for p in pitchers:
        assert "ip" in p
        assert "er" in p
        assert "so_count" in p


def test_lineup_pitcher_decision():
    """승/패 투수 decision 필드 존재"""
    r = client.get(f"/api/v1/games/{SAMPLE_GAME_ID}/lineups")
    data = r.json()
    pitchers = data["home_pitchers"] + data["away_pitchers"]
    decisions = [p["decision"] for p in pitchers if p["decision"]]
    assert len(decisions) >= 2  # 최소 승/패


def test_lineup_404():
    """존재하지 않는 game_id → 404"""
    r = client.get("/api/v1/games/9999999/lineups")
    assert r.status_code == 404
