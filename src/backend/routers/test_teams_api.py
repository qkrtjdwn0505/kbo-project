"""팀/순위 API 테스트 — pytest + TestClient"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── 팀 순위표 ────────────────────────────────────────────

def test_standings_returns_10_teams():
    """GET /teams/standings?season=2025 → 200, 10팀 반환"""
    r = client.get("/api/v1/teams/standings?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == 2025
    assert len(data["standings"]) == 10


def test_standings_sorted_by_win_pct():
    """승률 내림차순 정렬 확인"""
    r = client.get("/api/v1/teams/standings?season=2025")
    standings = r.json()["standings"]
    win_pcts = [s["win_pct"] for s in standings]
    assert win_pcts == sorted(win_pcts, reverse=True)


def test_standings_rank_sequence():
    """rank는 1부터 10까지 순서대로"""
    r = client.get("/api/v1/teams/standings?season=2025")
    ranks = [s["rank"] for s in r.json()["standings"]]
    assert ranks == list(range(1, 11))


def test_standings_first_place_games_behind_zero():
    """1위의 게임차는 0.0"""
    r = client.get("/api/v1/teams/standings?season=2025")
    first = r.json()["standings"][0]
    assert first["games_behind"] == 0.0


def test_standings_games_behind_increasing():
    """게임차는 순위가 낮아질수록 증가(또는 동일)"""
    standings = client.get("/api/v1/teams/standings?season=2025").json()["standings"]
    gbs = [s["games_behind"] for s in standings]
    assert gbs == sorted(gbs)


def test_standings_wins_losses_positive():
    """모든 팀의 승/패 > 0"""
    standings = client.get("/api/v1/teams/standings?season=2025").json()["standings"]
    for s in standings:
        assert s["wins"] > 0
        assert s["losses"] > 0


def test_standings_default_season():
    """season 미지정 → 200 반환"""
    r = client.get("/api/v1/teams/standings")
    assert r.status_code == 200


# ── 팀스탯 비교 ──────────────────────────────────────────

def test_comparison_returns_4_cards():
    """GET /teams/comparison?season=2025 → 200, 4개 카드"""
    r = client.get("/api/v1/teams/comparison?season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == 2025
    assert len(data["cards"]) == 4


def test_comparison_card_categories():
    """4개 카드의 카테고리 확인"""
    cards = client.get("/api/v1/teams/comparison?season=2025").json()["cards"]
    categories = {c["category"] for c in cards}
    assert categories == {"공격력", "투수력", "수비력", "주루"}


def test_comparison_each_card_has_10_teams():
    """각 카드의 rankings에 10팀 포함"""
    cards = client.get("/api/v1/teams/comparison?season=2025").json()["cards"]
    for card in cards:
        assert len(card["rankings"]) == 10, f"{card['category']} 카드에 팀 수 부족"


def test_comparison_leader_is_rank1():
    """leader_team이 rankings[0]과 일치"""
    cards = client.get("/api/v1/teams/comparison?season=2025").json()["cards"]
    for card in cards:
        assert card["leader_team"] == card["rankings"][0]["team_name"]


def test_comparison_attack_sorted_desc():
    """공격력(team_ops)은 내림차순 정렬"""
    cards = client.get("/api/v1/teams/comparison?season=2025").json()["cards"]
    attack = next(c for c in cards if c["category"] == "공격력")
    vals = [r["value"] for r in attack["rankings"] if r["value"] is not None]
    assert vals == sorted(vals, reverse=True)


def test_comparison_pitching_sorted_asc():
    """투수력(team_era)은 오름차순 정렬"""
    cards = client.get("/api/v1/teams/comparison?season=2025").json()["cards"]
    pitching = next(c for c in cards if c["category"] == "투수력")
    vals = [r["value"] for r in pitching["rankings"] if r["value"] is not None]
    assert vals == sorted(vals)


# ── 선수 TOP N ───────────────────────────────────────────

def test_top_rankings_avg():
    """GET /rankings/top?stat=avg&limit=5&season=2025 → 200, 5명"""
    r = client.get("/api/v1/rankings/top?stat=avg&limit=5&season=2025")
    assert r.status_code == 200
    data = r.json()
    assert len(data["rankings"]) == 5
    assert data["stat"] == "avg"
    assert data["player_type"] == "batter"


def test_top_rankings_avg_sorted_desc():
    """타율은 내림차순"""
    rankings = client.get("/api/v1/rankings/top?stat=avg&limit=5&season=2025").json()["rankings"]
    vals = [r["value"] for r in rankings]
    assert vals == sorted(vals, reverse=True)


def test_top_rankings_era_sorted_asc():
    """ERA는 오름차순"""
    r = client.get("/api/v1/rankings/top?stat=era&limit=5&season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "pitcher"
    vals = [r["value"] for r in data["rankings"]]
    assert vals == sorted(vals)


def test_top_rankings_rank_sequence():
    """rank는 1부터 순서대로"""
    rankings = client.get("/api/v1/rankings/top?stat=hr&limit=10&season=2025").json()["rankings"]
    assert [r["rank"] for r in rankings] == list(range(1, len(rankings) + 1))


def test_top_rankings_invalid_stat():
    """잘못된 stat → 400"""
    r = client.get("/api/v1/rankings/top?stat=invalid_stat&season=2025")
    assert r.status_code == 400


def test_top_rankings_pitcher_stat():
    """투수 지표(fip) → player_type=pitcher"""
    r = client.get("/api/v1/rankings/top?stat=fip&limit=5&season=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["player_type"] == "pitcher"
    vals = [r["value"] for r in data["rankings"]]
    assert vals == sorted(vals)  # FIP도 낮을수록 좋음 → ASC


# ── recent_5 / streak (T-2.6) ───────────────────────────

def test_standings_recent_5_length():
    """모든 팀의 recent_5 길이 <= 5"""
    standings = client.get("/api/v1/teams/standings?season=2025").json()["standings"]
    for s in standings:
        assert len(s["recent_5"]) <= 5


def test_standings_recent_5_values():
    """recent_5 원소가 W/L/D 중 하나"""
    standings = client.get("/api/v1/teams/standings?season=2025").json()["standings"]
    valid = {"W", "L", "D"}
    for s in standings:
        for result in s["recent_5"]:
            assert result in valid, f"잘못된 결과값: {result}"


def test_standings_streak_format():
    """streak이 'N연승', 'N연패', 'N무' 형식"""
    import re
    standings = client.get("/api/v1/teams/standings?season=2025").json()["standings"]
    pattern = re.compile(r"^\d+(연승|연패|무)$")
    for s in standings:
        assert pattern.match(s["streak"]), f"잘못된 streak 형식: {s['streak']}"
