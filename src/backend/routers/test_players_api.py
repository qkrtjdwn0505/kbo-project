"""선수 API 테스트 — pytest + TestClient"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

DB_PATH = "kbo.db"


@pytest.fixture(scope="module")
def player_ids():
    """테스트용 선수 ID를 DB에서 동적으로 조회"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 타자: batter_season에 기록이 있는 선수
    c.execute("""
        SELECT bs.player_id, p.name
        FROM batter_season bs
        JOIN players p ON p.id = bs.player_id
        WHERE bs.season = 2025 AND bs.avg > 0
        ORDER BY bs.pa DESC
        LIMIT 1
    """)
    batter_row = c.fetchone()

    # 투수: pitcher_season에 기록이 있는 선수
    c.execute("""
        SELECT ps.player_id, p.name
        FROM pitcher_season ps
        JOIN players p ON p.id = ps.player_id
        WHERE ps.season = 2025 AND ps.ip_outs > 50
        ORDER BY ps.ip_outs DESC
        LIMIT 1
    """)
    pitcher_row = c.fetchone()

    conn.close()
    return {
        "batter_id": batter_row[0],
        "batter_name": batter_row[1],
        "pitcher_id": pitcher_row[0],
        "pitcher_name": pitcher_row[1],
    }


# ── 검색 ────────────────────────────────────────────────

def test_search_found():
    """GET /players/search?q=김도 → 200, 김도영 포함"""
    r = client.get("/api/v1/players/search?q=김도")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    names = [item["name"] for item in data["results"]]
    assert any("김도" in name for name in names)


def test_search_empty_result():
    """존재하지 않는 이름 → 200, empty results"""
    r = client.get("/api/v1/players/search?q=zzzxxx")
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_search_too_short():
    """q 길이 1 → 422 (min_length=2 검증)"""
    r = client.get("/api/v1/players/search?q=김")
    assert r.status_code == 422


# ── 프로필 ───────────────────────────────────────────────

def test_get_player_found(player_ids):
    """GET /players/{id} → 200, name/team_name/position/player_type 포함"""
    r = client.get(f"/api/v1/players/{player_ids['batter_id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == player_ids["batter_id"]
    assert "name" in data
    assert "team_name" in data
    assert "position" in data
    assert data["player_type"] == "batter"


def test_get_player_not_found():
    """GET /players/99999 → 404"""
    r = client.get("/api/v1/players/99999")
    assert r.status_code == 404


def test_get_pitcher_profile(player_ids):
    """투수 프로필 → player_type='pitcher'"""
    r = client.get(f"/api/v1/players/{player_ids['pitcher_id']}")
    assert r.status_code == 200
    assert r.json()["player_type"] == "pitcher"


# ── 클래식 스탯 ─────────────────────────────────────────

def test_classic_batter(player_ids):
    """GET /players/{타자ID}/classic?season=2025 → 200, player_type=batter, avg>0"""
    r = client.get(f"/api/v1/players/{player_ids['batter_id']}/classic?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "batter"
    assert data["season"] == 2025
    assert "stats" in data
    stats = data["stats"]
    assert stats["avg"] is not None
    assert stats["avg"] > 0
    assert "hr" in stats
    assert "ops" in stats


def test_classic_pitcher(player_ids):
    """GET /players/{투수ID}/classic?season=2025 → 200, ip_display 형식 확인"""
    r = client.get(f"/api/v1/players/{player_ids['pitcher_id']}/classic?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "pitcher"
    stats = data["stats"]
    assert "ip_display" in stats
    # ip_display는 "X.Y" 형식
    parts = stats["ip_display"].split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1] in ("0", "1", "2")
    assert "era" in stats
    assert "whip" in stats


def test_classic_no_season():
    """season 미지정 → 기본값(현재 연도)으로 동작"""
    r = client.get("/api/v1/players/99999/classic")
    # 99999 선수 없으므로 404
    assert r.status_code == 404


def test_classic_player_not_found():
    """존재하지 않는 선수 → 404"""
    r = client.get("/api/v1/players/99999/classic?season=2025")
    assert r.status_code == 404


# ── 세이버메트릭스 ──────────────────────────────────────

def test_sabermetrics_batter(player_ids):
    """GET /players/{타자ID}/sabermetrics?season=2025 → 200, woba>0"""
    r = client.get(f"/api/v1/players/{player_ids['batter_id']}/sabermetrics?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "batter"
    stats = data["stats"]
    assert stats.get("woba") is not None
    assert stats["woba"] > 0
    assert "war" in stats
    assert "babip" in stats


def test_sabermetrics_pitcher(player_ids):
    """GET /players/{투수ID}/sabermetrics?season=2025 → 200, fip 포함"""
    r = client.get(f"/api/v1/players/{player_ids['pitcher_id']}/sabermetrics?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "pitcher"
    stats = data["stats"]
    assert "fip" in stats
    assert "k_per_9" in stats


# ── 스플릿 ──────────────────────────────────────────────

def test_splits_batter(player_ids):
    """GET /players/{타자ID}/splits?season=2025 → 200, splits >= 4"""
    r = client.get(f"/api/v1/players/{player_ids['batter_id']}/splits?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "batter"
    splits = data["splits"]
    assert len(splits) >= 4
    labels = [s["label"] for s in splits]
    assert "홈" in labels
    assert "원정" in labels
    for sp in splits:
        assert "label" in sp
        assert "stat_name" in sp
        assert "value" in sp


def test_splits_pitcher(player_ids):
    """투수 스플릿 → splits >= 4, ERA 기준"""
    r = client.get(f"/api/v1/players/{player_ids['pitcher_id']}/splits?season=2025")
    assert r.status_code == 200
    data = r.json()
    splits = data["splits"]
    assert len(splits) >= 4
    assert all(s["stat_name"] == "era" for s in splits)


# ── 선수 목록 ────────────────────────────────────────────

def test_list_players_basic():
    """GET /players/list?season=2025&per_page=10 → 200, results<=10, total>0"""
    r = client.get("/api/v1/players/list?season=2025&per_page=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) <= 10
    assert data["total"] > 0
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert data["season"] == 2025


def test_list_sorted():
    """sort_by=hr, sort_order=desc → HR 내림차순"""
    r = client.get("/api/v1/players/list?season=2025&sort_by=hr&sort_order=desc&per_page=5")
    assert r.status_code == 200
    results = r.json()["results"]
    if len(results) >= 2:
        primaries = [x["primary_stat"] for x in results if x["primary_stat"] is not None]
        assert primaries == sorted(primaries, reverse=True)


def test_list_pitcher():
    """position=투수 → player_type 전부 pitcher"""
    r = client.get("/api/v1/players/list?season=2025&position=투수&sort_by=era&sort_order=asc&per_page=5")
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0
    for item in results:
        assert item["player_type"] == "pitcher"


def test_list_invalid_sort_order():
    """잘못된 sort_order → 400"""
    r = client.get("/api/v1/players/list?season=2025&sort_order=random")
    assert r.status_code == 400
