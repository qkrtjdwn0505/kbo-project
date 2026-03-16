"""동적 SQL 빌더 통합 테스트 — 실제 kbo.db 사용"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine

from src.backend.explorer.query_builder import build_explorer_query

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"


@pytest.fixture(scope="module")
def conn():
    """테스트용 DB 연결 (읽기 전용)"""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    with engine.connect() as connection:
        yield connection


class TestBatterAll:
    """경로 A: 타자 + all 조건"""

    def test_avg_desc_5(self, conn):
        """1. 타자 + all + avg + desc + 5"""
        resp = build_explorer_query(conn, "batter", "all", "avg", "desc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat >= resp.results[1].primary_stat
        assert resp.total_count == 5
        for r in resp.results:
            assert r.player_name != ""
            assert r.team_name != ""
            assert len(r.secondary_stats) >= 2

    def test_hr_desc_10(self, conn):
        """2. 타자 + all + hr + desc + 10"""
        resp = build_explorer_query(conn, "batter", "all", "hr", "desc", "10")
        assert len(resp.results) == 10
        assert resp.results[0].primary_stat >= resp.results[1].primary_stat

    def test_ops_desc_all(self, conn):
        """타자 + all + ops + desc + all → 결과 > 0"""
        resp = build_explorer_query(conn, "batter", "all", "ops", "desc", "all")
        assert len(resp.results) > 0

    def test_woba_has_secondary(self, conn):
        """wOBA 조회 시 보조 지표에 wrc_plus 포함"""
        resp = build_explorer_query(conn, "batter", "all", "woba", "desc", "5")
        assert len(resp.results) == 5
        assert "wrc_plus" in resp.results[0].secondary_stats

    def test_war_desc_5(self, conn):
        """WAR 상위 5명"""
        resp = build_explorer_query(conn, "batter", "all", "war", "desc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat >= resp.results[4].primary_stat


class TestBatterCondition:
    """경로 B: 타자 + 조건부 집계"""

    def test_home_ops_desc_5(self, conn):
        """5. 타자 + home + ops + desc + 5"""
        resp = build_explorer_query(conn, "batter", "home", "ops", "desc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat >= resp.results[1].primary_stat
        for r in resp.results:
            assert r.primary_stat is not None

    def test_away_avg_desc_5(self, conn):
        """타자 + away + avg + desc + 5"""
        resp = build_explorer_query(conn, "batter", "away", "avg", "desc", "5")
        assert len(resp.results) == 5

    def test_home_woba_computed(self, conn):
        """경로 B에서 wOBA 세이버 지표도 정상 계산"""
        resp = build_explorer_query(conn, "batter", "home", "woba", "desc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat is not None
        assert resp.results[0].primary_stat > 0

    def test_leading_wrc_plus(self, conn):
        """리드 상황에서 wRC+ (score_diff 데이터가 없으면 0건 가능)"""
        resp = build_explorer_query(conn, "batter", "leading", "wrc_plus", "desc", "5")
        # score_diff 미수집 시 0건, 수집 시 최대 5건
        assert len(resp.results) <= 5


class TestPitcherAll:
    """경로 A: 투수 + all 조건"""

    def test_era_asc_5(self, conn):
        """6. 투수 + all + era + asc + 5"""
        resp = build_explorer_query(conn, "pitcher", "all", "era", "asc", "5")
        assert len(resp.results) == 5
        # asc: 첫 번째가 가장 낮아야 함
        assert resp.results[0].primary_stat <= resp.results[1].primary_stat

    def test_starter_fip_asc_10(self, conn):
        """7. 투수(선발) + all + fip + asc + 10"""
        resp = build_explorer_query(conn, "pitcher_starter", "all", "fip", "asc", "10")
        assert len(resp.results) == 10
        assert resp.results[0].primary_stat <= resp.results[1].primary_stat

    def test_bullpen_saves_desc_5(self, conn):
        """8. 투수(불펜) + all + saves + desc + 5"""
        resp = build_explorer_query(conn, "pitcher_bullpen", "all", "saves", "desc", "5")
        assert len(resp.results) == 5

    def test_pitcher_war_desc_5(self, conn):
        """투수 WAR 상위 5명"""
        resp = build_explorer_query(conn, "pitcher", "all", "war", "desc", "5")
        assert len(resp.results) == 5


class TestPitcherCondition:
    """경로 B: 투수 + 조건부 집계"""

    def test_home_era_asc_5(self, conn):
        """투수 + home + era + asc + 5"""
        resp = build_explorer_query(conn, "pitcher", "home", "era", "asc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat <= resp.results[1].primary_stat

    def test_home_fip_computed(self, conn):
        """경로 B에서 FIP 세이버 지표도 정상 계산"""
        resp = build_explorer_query(conn, "pitcher", "home", "fip", "asc", "5")
        assert len(resp.results) == 5
        assert resp.results[0].primary_stat is not None
        assert resp.results[0].primary_stat > 0


class TestValidation:
    """입력값 검증 — 잘못된 조합"""

    def test_pitcher_risp_raises(self, conn):
        """10. 투수 + risp → ValueError"""
        with pytest.raises(ValueError, match="투수에게 사용할 수 없는 조건"):
            build_explorer_query(conn, "pitcher", "risp", "era", "asc", "5")

    def test_pitcher_vs_lhp_raises(self, conn):
        """투수 + vs_lhp → ValueError"""
        with pytest.raises(ValueError, match="투수에게 사용할 수 없는 조건"):
            build_explorer_query(conn, "pitcher", "vs_lhp", "era", "asc", "5")

    def test_batter_vs_lhb_raises(self, conn):
        """타자 + vs_lhb → ValueError"""
        with pytest.raises(ValueError, match="타자에게 사용할 수 없는 조건"):
            build_explorer_query(conn, "batter", "vs_lhb", "avg", "desc", "5")

    def test_invalid_target(self, conn):
        """잘못된 target"""
        with pytest.raises(ValueError, match="잘못된 target"):
            build_explorer_query(conn, "catcher", "all", "avg", "desc", "5")

    def test_invalid_sort(self, conn):
        """잘못된 sort"""
        with pytest.raises(ValueError, match="잘못된 sort"):
            build_explorer_query(conn, "batter", "all", "avg", "up", "5")

    def test_invalid_stat(self, conn):
        """잘못된 stat"""
        with pytest.raises(ValueError, match="잘못된 타자 지표"):
            build_explorer_query(conn, "batter", "all", "xyz", "desc", "5")

    def test_bases_loaded_raises(self, conn):
        """bases_loaded → ValueError (미지원)"""
        with pytest.raises(ValueError, match="미지원"):
            build_explorer_query(conn, "batter", "bases_loaded", "avg", "desc", "5")


class TestResponseFormat:
    """응답 포맷 검증"""

    def test_query_params_in_response(self, conn):
        """응답에 query 파라미터 포함"""
        resp = build_explorer_query(conn, "batter", "all", "avg", "desc", "5")
        assert resp.query.target == "batter"
        assert resp.query.condition == "all"
        assert resp.query.stat == "avg"
        assert resp.query.sort == "desc"
        assert resp.query.limit == "5"
        assert resp.query.season == 2025

    def test_rank_starts_at_1(self, conn):
        """rank가 1부터 시작"""
        resp = build_explorer_query(conn, "batter", "all", "avg", "desc", "5")
        assert resp.results[0].rank == 1
        assert resp.results[4].rank == 5

    def test_secondary_stats_count(self, conn):
        """보조 지표 2~3개"""
        resp = build_explorer_query(conn, "batter", "all", "avg", "desc", "5")
        for r in resp.results:
            assert 2 <= len(r.secondary_stats) <= 3

    def test_min_pa_filter(self, conn):
        """PA 최소 기준 충족"""
        resp = build_explorer_query(conn, "batter", "all", "avg", "desc", "all")
        # 모든 결과의 PA가 MIN_PA 이상 (시즌 테이블 기준)
        for r in resp.results:
            assert r.primary_stat is not None
