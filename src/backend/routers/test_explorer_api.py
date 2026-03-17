"""탐색기 API 엔드포인트 테스트 — TestClient 사용"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

SEASON = 2025


def test_explorer_batter_all_avg():
    """1. 경로 A 정상 호출 — 타자 전체 타율 상위 5명"""
    r = client.get(f"/api/v1/explorer?target=batter&stat=avg&sort=desc&limit=5&season={SEASON}")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 5
    assert len(data["results"]) == 5
    assert data["results"][0]["primary_stat"] >= data["results"][1]["primary_stat"]
    assert "secondary_stats" in data["results"][0]


def test_explorer_pitcher_era_asc():
    """투수 ERA 낮은 순 5명"""
    r = client.get(f"/api/v1/explorer?target=pitcher&stat=era&sort=asc&limit=5&season={SEASON}")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 5
    assert data["results"][0]["primary_stat"] <= data["results"][1]["primary_stat"]


def test_explorer_batter_risp_ops():
    """2. 경로 B 정상 호출 — 득점권 OPS (데이터 비어있어도 200)"""
    r = client.get(f"/api/v1/explorer?target=batter&condition=risp&stat=ops&sort=desc&limit=5&season={SEASON}")
    assert r.status_code == 200


def test_explorer_invalid_target():
    """3. 잘못된 target → 400"""
    r = client.get("/api/v1/explorer?target=catcher&stat=avg")
    assert r.status_code == 400
    assert "detail" in r.json()


def test_explorer_invalid_sort():
    """잘못된 sort → 400"""
    r = client.get("/api/v1/explorer?target=batter&stat=avg&sort=up")
    assert r.status_code == 400
    assert "잘못된 정렬" in r.json()["detail"]


def test_explorer_invalid_limit():
    """잘못된 limit → 400"""
    r = client.get("/api/v1/explorer?target=batter&stat=avg&limit=99")
    assert r.status_code == 400
    assert "잘못된 범위" in r.json()["detail"]


def test_explorer_invalid_combination():
    """4. 잘못된 조합 (투수 + risp) → 400"""
    r = client.get(f"/api/v1/explorer?target=pitcher&condition=risp&stat=era&season={SEASON}")
    assert r.status_code == 400


def test_explorer_default_season():
    """5. season 미지정 → 기본값(현재 연도)으로 동작, 200 반환"""
    r = client.get("/api/v1/explorer?target=batter&stat=avg&sort=desc&limit=5")
    assert r.status_code == 200


def test_explorer_options_batter():
    """options 엔드포인트 — 타자 지표 목록"""
    r = client.get("/api/v1/explorer/options?target=batter")
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert "avg" in data["stats"]
    assert "conditions" in data


def test_explorer_options_pitcher_starter():
    """options — pitcher_starter도 pitcher로 매핑"""
    r = client.get("/api/v1/explorer/options?target=pitcher_starter")
    assert r.status_code == 200
    assert "era" in r.json()["stats"]


def test_explorer_options_invalid():
    """options — 잘못된 target → 400"""
    r = client.get("/api/v1/explorer/options?target=catcher")
    assert r.status_code == 400
