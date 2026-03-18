"""기록 조회 API 테스트 — pytest + TestClient"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── 타자 기록 ─────────────────────────────────────────────

def test_batter_records_200():
    r = client.get("/api/v1/players/records?type=batter")
    assert r.status_code == 200


def test_batter_records_structure():
    r = client.get("/api/v1/players/records?type=batter")
    d = r.json()
    assert d["type"] == "batter"
    assert d["season"] == 2025
    assert d["total"] > 0
    assert d["page"] == 1
    assert d["per_page"] == 20
    assert len(d["players"]) <= 20


def test_batter_records_fields():
    r = client.get("/api/v1/players/records?type=batter")
    p = r.json()["players"][0]
    assert "rank" in p
    assert "player_id" in p
    assert "player_name" in p
    assert "team" in p
    assert "avg" in p
    assert "ops" in p
    assert "war" in p
    assert "woba" in p


def test_batter_rank_sequence():
    r = client.get("/api/v1/players/records?type=batter")
    players = r.json()["players"]
    assert [p["rank"] for p in players] == list(range(1, len(players) + 1))


def test_batter_sort_hr():
    r = client.get("/api/v1/players/records?type=batter&sort=hr&order=desc")
    players = r.json()["players"]
    hrs = [p["hr"] for p in players if p["hr"] is not None]
    assert hrs == sorted(hrs, reverse=True)


def test_batter_sort_avg_asc():
    r = client.get("/api/v1/players/records?type=batter&sort=avg&order=asc&min_pa=100")
    players = r.json()["players"]
    avgs = [p["avg"] for p in players if p["avg"] is not None]
    assert avgs == sorted(avgs)


def test_batter_min_pa_filter():
    """min_pa=200 → pa >= 200인 타자만"""
    r = client.get("/api/v1/players/records?type=batter&min_pa=200")
    players = r.json()["players"]
    assert all(p["pa"] >= 200 for p in players if p["pa"] is not None)


def test_batter_team_filter():
    """팀 필터 — 삼성(2)만"""
    r = client.get("/api/v1/players/records?type=batter&team=2&min_pa=0")
    d = r.json()
    assert d["total"] > 0
    assert all(p["team"] == "삼성" for p in d["players"])


def test_batter_pagination():
    """page=2 → rank가 per_page+1부터 시작"""
    r1 = client.get("/api/v1/players/records?type=batter&page=1&per_page=10")
    r2 = client.get("/api/v1/players/records?type=batter&page=2&per_page=10")
    p1 = r1.json()["players"]
    p2 = r2.json()["players"]
    assert p1[0]["rank"] == 1
    assert p2[0]["rank"] == 11
    # 두 페이지의 선수가 중복되지 않아야 함
    ids1 = {p["player_id"] for p in p1}
    ids2 = {p["player_id"] for p in p2}
    assert ids1.isdisjoint(ids2)


# ── 투수 기록 ─────────────────────────────────────────────

def test_pitcher_records_200():
    r = client.get("/api/v1/players/records?type=pitcher")
    assert r.status_code == 200
    assert r.json()["type"] == "pitcher"


def test_pitcher_records_fields():
    r = client.get("/api/v1/players/records?type=pitcher")
    p = r.json()["players"][0]
    assert "era" in p
    assert "fip" in p
    assert "war" in p
    assert "ip_display" in p
    assert "so_count" in p


def test_pitcher_sort_era_asc():
    r = client.get("/api/v1/players/records?type=pitcher&sort=era&order=asc&min_ip=20")
    players = r.json()["players"]
    eras = [p["era"] for p in players if p["era"] is not None]
    assert eras == sorted(eras)


def test_pitcher_min_ip_filter():
    r = client.get("/api/v1/players/records?type=pitcher&min_ip=50")
    players = r.json()["players"]
    # ip_display는 문자열이라 직접 확인 어려움 — total이 줄어야 함
    total_50 = r.json()["total"]
    r2 = client.get("/api/v1/players/records?type=pitcher&min_ip=0")
    total_0 = r2.json()["total"]
    assert total_50 < total_0


# ── 오류 처리 ─────────────────────────────────────────────

def test_invalid_type():
    r = client.get("/api/v1/players/records?type=unknown")
    assert r.status_code == 400


def test_invalid_order():
    r = client.get("/api/v1/players/records?type=batter&order=invalid")
    assert r.status_code == 400
