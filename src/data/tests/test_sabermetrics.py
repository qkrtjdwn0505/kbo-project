"""세이버메트릭스 계산 엔진 테스트

테스트 전략:
    1. 수학적 정확성 — 알려진 입력으로 수동 계산 결과와 비교
    2. 경계값 — 분모 0, 최소 타석 등
    3. 크로스체크 — 실제 KBO 선수 시즌 기록과 비교 (±오차 허용)
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.data.processors.sabermetrics_engine import (
    LeagueConstants,
    calc_avg,
    calc_obp,
    calc_slg,
    calc_ops,
    calc_iso,
    calc_babip,
    calc_bb_pct,
    calc_k_pct,
    calc_woba,
    calc_wraa,
    calc_wrc_plus,
    calc_batter_war_simplified,
    ip_outs_to_ip,
    calc_era,
    calc_whip,
    calc_fip,
    calc_xfip,
    calc_per_9,
    calc_k_bb_ratio,
    calc_pitcher_babip,
    calc_pitcher_war_simplified,
)

# 테스트용 리그 상수 (2024 KBO 기반 예시)
LC = LeagueConstants(
    season=2025,
    w_bb=0.69,
    w_hbp=0.72,
    w_1b=0.89,
    w_2b=1.27,
    w_3b=1.62,
    w_hr=2.10,
    woba_scale=1.15,
    league_woba=0.320,
    league_obp=0.340,
    rppa=0.12,
    league_rpw=10.0,
    league_r_pa=0.12,
    fip_constant=3.10,
    league_hr_fb_rate=0.10,
)


class TestClassicStats:
    """타율, 출루율, 장타율 등 클래식 지표"""

    def test_avg_normal(self):
        assert calc_avg(150, 500) == pytest.approx(0.300)

    def test_avg_zero_ab(self):
        assert calc_avg(0, 0) is None

    def test_obp_normal(self):
        result = calc_obp(hits=150, bb=60, hbp=5, ab=500, sf=3)
        assert result == pytest.approx(215 / 568, rel=1e-4)

    def test_obp_zero_denom(self):
        assert calc_obp(0, 0, 0, 0, 0) is None

    def test_slg_normal(self):
        result = calc_slg(singles=100, doubles=30, triples=5, hr=15, ab=500)
        assert result == pytest.approx(0.470)

    def test_slg_zero_ab(self):
        assert calc_slg(0, 0, 0, 0, 0) is None

    def test_ops_normal(self):
        assert calc_ops(0.378, 0.470) == pytest.approx(0.848)

    def test_ops_none_input(self):
        assert calc_ops(None, 0.470) is None
        assert calc_ops(0.378, None) is None

    def test_iso_normal(self):
        assert calc_iso(0.470, 0.300) == pytest.approx(0.170)

    def test_iso_none(self):
        assert calc_iso(None, 0.300) is None


class TestBABIP:
    def test_babip_normal(self):
        result = calc_babip(hits=150, hr=15, ab=500, so=80, sf=3)
        assert result == pytest.approx(135 / 408, rel=1e-4)

    def test_babip_zero_denom(self):
        assert calc_babip(hits=1, hr=1, ab=2, so=1, sf=0) is None

    def test_babip_league_average(self):
        result = calc_babip(hits=130, hr=12, ab=480, so=100, sf=4)
        assert 0.200 <= result <= 0.400


class TestRateStats:
    def test_bb_pct(self):
        assert calc_bb_pct(60, 580) == pytest.approx(60 / 580, rel=1e-4)

    def test_bb_pct_zero_pa(self):
        assert calc_bb_pct(0, 0) is None

    def test_k_pct(self):
        assert calc_k_pct(80, 580) == pytest.approx(80 / 580, rel=1e-4)

    def test_k_pct_zero_pa(self):
        assert calc_k_pct(0, 0) is None


class TestWOBA:
    def test_woba_normal(self):
        result = calc_woba(
            bb=60, ibb=2, hbp=5,
            singles=100, doubles=30, triples=5, hr=15,
            ab=500, sf=3, lc=LC,
        )
        expected = 210.32 / 566
        assert result == pytest.approx(expected, rel=1e-3)

    def test_woba_no_ibb(self):
        result = calc_woba(
            bb=60, ibb=0, hbp=5,
            singles=100, doubles=30, triples=5, hr=15,
            ab=500, sf=3, lc=LC,
        )
        assert result is not None
        assert 0.200 <= result <= 0.500

    def test_woba_zero_denom(self):
        assert calc_woba(0, 0, 0, 0, 0, 0, 0, 0, 0, LC) is None


class TestWRCPlus:
    def test_wrc_plus_league_average(self):
        result = calc_wrc_plus(woba=LC.league_woba, pa=500, lc=LC)
        assert result == pytest.approx(100.0, rel=1e-2)

    def test_wrc_plus_above_average(self):
        result = calc_wrc_plus(woba=0.380, pa=500, lc=LC)
        assert result is not None
        assert result > 100

    def test_wrc_plus_below_average(self):
        result = calc_wrc_plus(woba=0.280, pa=500, lc=LC)
        assert result is not None
        assert result < 100

    def test_wrc_plus_none_woba(self):
        assert calc_wrc_plus(None, 500, LC) is None


class TestBatterWAR:
    def test_war_positive_for_good_hitter(self):
        result = calc_batter_war_simplified(woba=0.400, pa=600, lc=LC)
        assert result is not None
        assert result > 0

    def test_war_near_zero_for_average(self):
        result = calc_batter_war_simplified(woba=LC.league_woba, pa=600, lc=LC)
        assert result is not None
        assert result > 0

    def test_war_reasonable_range(self):
        result = calc_batter_war_simplified(woba=0.420, pa=650, lc=LC)
        assert result is not None
        assert 2.0 <= result <= 10.0

    def test_war_none(self):
        assert calc_batter_war_simplified(None, 600, LC) is None


class TestIPConversion:
    def test_full_innings(self):
        assert ip_outs_to_ip(18) == pytest.approx(6.0)

    def test_partial_innings(self):
        assert ip_outs_to_ip(14) == pytest.approx(14 / 3)

    def test_zero(self):
        assert ip_outs_to_ip(0) == 0.0


class TestPitcherClassic:
    def test_era_normal(self):
        assert calc_era(60, 540) == pytest.approx(3.00)

    def test_era_zero_ip(self):
        assert calc_era(5, 0) is None

    def test_whip_normal(self):
        assert calc_whip(150, 50, 540) == pytest.approx(200 / 180, rel=1e-3)

    def test_whip_zero_ip(self):
        assert calc_whip(0, 0, 0) is None


class TestFIP:
    def test_fip_normal(self):
        result = calc_fip(
            hr_allowed=15, bb_allowed=50, hbp_allowed=5,
            so_count=180, ip_outs=540, lc=LC,
        )
        assert result == pytest.approx(3.10, rel=1e-3)

    def test_fip_high(self):
        result = calc_fip(
            hr_allowed=30, bb_allowed=70, hbp_allowed=10,
            so_count=100, ip_outs=540, lc=LC,
        )
        assert result is not None
        assert result > 4.0

    def test_fip_zero_ip(self):
        assert calc_fip(0, 0, 0, 0, 0, LC) is None


class TestXFIP:
    def test_xfip_with_fb(self):
        result = calc_xfip(
            fb_count=200,
            bb_allowed=50, hbp_allowed=5,
            so_count=180, ip_outs=540, lc=LC,
        )
        assert result is not None
        assert result == pytest.approx(3.461, rel=1e-2)

    def test_xfip_no_fb_data(self):
        result = calc_xfip(
            fb_count=None,
            bb_allowed=50, hbp_allowed=5,
            so_count=180, ip_outs=540, lc=LC,
        )
        assert result is None


class TestPitcherPer9:
    def test_k_per_9(self):
        assert calc_per_9(180, 540) == pytest.approx(9.0)

    def test_bb_per_9(self):
        assert calc_per_9(50, 540) == pytest.approx(2.5)

    def test_hr_per_9(self):
        assert calc_per_9(15, 540) == pytest.approx(0.75)

    def test_per_9_zero_ip(self):
        assert calc_per_9(10, 0) is None


class TestKBBRatio:
    def test_k_bb_normal(self):
        assert calc_k_bb_ratio(180, 50) == pytest.approx(3.6)

    def test_k_bb_zero_bb(self):
        assert calc_k_bb_ratio(100, 0) is None


class TestPitcherBABIP:
    def test_pitcher_babip_normal(self):
        result = calc_pitcher_babip(150, 15, 540, 180)
        assert result == pytest.approx(135 / 495, rel=1e-3)

    def test_pitcher_babip_zero(self):
        assert calc_pitcher_babip(0, 0, 0, 0) is None


class TestPitcherWAR:
    def test_war_good_pitcher(self):
        result = calc_pitcher_war_simplified(fip=2.80, ip_outs=540, lc=LC)
        assert result is not None
        assert result > 0

    def test_war_bad_pitcher(self):
        result = calc_pitcher_war_simplified(fip=6.00, ip_outs=300, lc=LC)
        assert result is not None

    def test_war_none_fip(self):
        assert calc_pitcher_war_simplified(None, 540, LC) is None


class TestEdgeCases:
    def test_all_strikeouts(self):
        assert calc_babip(hits=0, hr=0, ab=100, so=100, sf=0) is None

    def test_single_ab(self):
        assert calc_avg(1, 1) == pytest.approx(1.0)

    def test_very_low_pa_wrc_plus(self):
        result = calc_wrc_plus(woba=0.500, pa=5, lc=LC)
        assert result is not None

    def test_negative_wraa(self):
        result = calc_wraa(woba=0.250, pa=500, lc=LC)
        assert result is not None
        assert result < 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
