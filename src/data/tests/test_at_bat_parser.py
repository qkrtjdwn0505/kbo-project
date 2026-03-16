"""table2 타석 결과 코드 파서 테스트

35경기 2,737 타석에서 발견된 103개 코드를 기반으로 테스트.
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.data.processors.at_bat_parser import (
    AtBatResult,
    PlayerGameStats,
    parse_at_bat_code,
    parse_player_innings,
)


class TestParseAtBatCode:
    """개별 타석 코드 파싱 테스트"""

    # ─── 홈런 ───────────────────────────────────

    @pytest.mark.parametrize("code", ["좌홈", "우홈", "중홈", "우중홈", "좌중홈"])
    def test_home_run(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.hr == 1
        assert r.hit == 1
        assert r.bb == 0

    # ─── 3루타 ──────────────────────────────────

    @pytest.mark.parametrize("code", ["우3", "좌3", "우중3", "좌중3"])
    def test_triple(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.triple == 1
        assert r.hit == 1

    # ─── 2루타 ──────────────────────────────────

    @pytest.mark.parametrize("code", ["우2", "좌2", "중2", "우중2", "좌중2"])
    def test_double(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.double == 1
        assert r.hit == 1

    def test_double_special_22(self):
        """22 코드 (2루수 방향 2루타)"""
        r = parse_at_bat_code("22")
        assert r.double == 1
        assert r.hit == 1

    # ─── 안타 (1B) ──────────────────────────────

    @pytest.mark.parametrize("code", [
        "좌안", "우안", "중안", "유안", "투안",
        "우중안", "좌중안", "1안", "2안", "3안",
        "투유안", "투우안", "투1안", "투3안",
        "3좌안", "1우안", "유중안", "포안",
    ])
    def test_single(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.single == 1
        assert r.hit == 1

    # ─── 볼넷 ───────────────────────────────────

    def test_walk(self):
        r = parse_at_bat_code("4구")
        assert r.pa == 1
        assert r.ab == 0  # 타수 미포함
        assert r.bb == 1
        assert r.ibb == 0

    def test_intentional_walk(self):
        r = parse_at_bat_code("고4")
        assert r.pa == 1
        assert r.ab == 0
        assert r.bb == 1
        assert r.ibb == 1

    # ─── 사구 ───────────────────────────────────

    def test_hit_by_pitch(self):
        r = parse_at_bat_code("사구")
        assert r.pa == 1
        assert r.ab == 0
        assert r.hbp == 1

    # ─── 삼진 ───────────────────────────────────

    def test_strikeout(self):
        r = parse_at_bat_code("삼진")
        assert r.pa == 1
        assert r.ab == 1
        assert r.so == 1
        assert r.hit == 0

    def test_strikeout_swinging(self):
        """스트라이크 낫아웃"""
        r = parse_at_bat_code("스낫")
        assert r.so == 1
        assert r.ab == 1

    # ─── 희생번트 ───────────────────────────────

    @pytest.mark.parametrize("code", [
        "투희번", "3희번", "포희번", "1희번",
    ])
    def test_sacrifice_bunt(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 0  # 타수 미포함
        assert r.sh == 1

    @pytest.mark.parametrize("code", ["투희선", "포희선"])
    def test_sacrifice_fielders_choice(self, code: str):
        """희생 상황 야수선택 — SH로 분류"""
        r = parse_at_bat_code(code)
        assert r.sh == 1
        assert r.ab == 0

    # ─── 희생플라이 ─────────────────────────────

    @pytest.mark.parametrize("code", ["우희비", "좌희비", "중희비", "유희비"])
    def test_sacrifice_fly(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 0
        assert r.sf == 1

    # ─── 병살 ───────────────────────────────────

    @pytest.mark.parametrize("code", [
        "유병", "2병", "3병", "1병", "투병",
    ])
    def test_double_play(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.gdp == 1

    # ─── 야수선택 ───────────────────────────────

    def test_fielders_choice(self):
        r = parse_at_bat_code("야선")
        assert r.pa == 1
        assert r.ab == 1
        assert r.fc == 1
        assert r.hit == 0

    # ─── 범타/아웃 ──────────────────────────────

    @pytest.mark.parametrize("code", [
        "2땅", "유땅", "1땅", "3땅", "투땅", "포땅",
        "좌비", "우비", "중비", "유비", "1비", "2비", "3비", "투비", "포비",
        "3파", "1파", "포파", "유파", "좌파", "우파",
        "유직", "2직", "3직", "1직", "우직",
        "유실", "1실", "2실", "3실", "좌실", "중실", "투실",
        "투번", "1번", "3번", "포번",
    ])
    def test_outs(self, code: str):
        r = parse_at_bat_code(code)
        assert r.pa == 1
        assert r.ab == 1
        assert r.hit == 0
        assert r.bb == 0

    # ─── 빈 값 / 특수 ──────────────────────────

    @pytest.mark.parametrize("code", ["", "&nbsp;", "TOTAL", None])
    def test_empty_or_special(self, code):
        r = parse_at_bat_code(code)
        assert r.pa == 0
        assert r.ab == 0

    # ─── 복합 타석 (대타 교체) ──────────────────

    def test_compound_walk_then_out(self):
        """4구<br />/ 투땅 → 첫 타자: 4구"""
        r = parse_at_bat_code("4구<br />/ 투땅")
        assert r.bb == 1
        assert r.ab == 0

    def test_compound_single_then_strikeout(self):
        """좌중안<br />/ 삼진 → 첫 타자: 안타"""
        r = parse_at_bat_code("좌중안<br />/ 삼진")
        assert r.single == 1
        assert r.hit == 1
        assert r.so == 0

    def test_compound_single_then_ground(self):
        """투안<br />/ 투땅 → 첫 타자: 안타"""
        r = parse_at_bat_code("투안<br />/ 투땅")
        assert r.single == 1
        assert r.ab == 1

    def test_compound_sac_bunt_then_fly(self):
        """투희실<br />/ 우비 → 첫 타자: 투희실(범타)"""
        r = parse_at_bat_code("투희실<br />/ 우비")
        # 투희실 = 투수 앞 희생번트 실책 → 실책 출루, AB 소모
        assert r.pa == 1

    # ─── 3루수 관련 코드 구분 ───────────────────

    def test_3_fielder_not_triple(self):
        """3땅, 3파, 3직 등은 3루수 관련 아웃 (3루타 아님)"""
        r = parse_at_bat_code("3땅")
        assert r.triple == 0
        assert r.ab == 1
        assert r.hit == 0

    def test_3_safe_hit(self):
        """3안은 3루수 방향 안타 (3루타 아님, 1루타)"""
        r = parse_at_bat_code("3안")
        assert r.single == 1
        assert r.triple == 0


class TestParsePlayerInnings:
    """전 이닝 합산 테스트"""

    def test_typical_game(self):
        """일반적인 경기: 4타수 1안타 1볼넷"""
        cells = ["삼진", "&nbsp;", "좌안", "4구", "&nbsp;", "유땅", "2비", "&nbsp;"]
        stats = parse_player_innings(cells)
        assert stats.pa == 5
        assert stats.ab == 4   # 4구 제외
        assert stats.hits == 1
        assert stats.singles == 1
        assert stats.bb == 1
        assert stats.so == 1

    def test_multi_hit_game(self):
        """멀티히트: 홈런 + 2루타 + 안타"""
        cells = ["좌홈", "&nbsp;", "우중2", "&nbsp;", "중안", "&nbsp;"]
        stats = parse_player_innings(cells)
        assert stats.pa == 3
        assert stats.ab == 3
        assert stats.hits == 3
        assert stats.hr == 1
        assert stats.doubles == 1
        assert stats.singles == 1

    def test_all_empty(self):
        """전 이닝 결석"""
        cells = ["&nbsp;", "&nbsp;", "&nbsp;"]
        stats = parse_player_innings(cells)
        assert stats.pa == 0
        assert stats.ab == 0

    def test_sacrifice_fly_excluded_from_ab(self):
        """희생플라이는 타수에서 제외"""
        cells = ["우희비", "좌안", "삼진"]
        stats = parse_player_innings(cells)
        assert stats.pa == 3
        assert stats.ab == 2  # 희비 제외
        assert stats.sf == 1
        assert stats.hits == 1

    def test_real_game_hongchanggi(self):
        """실제 데이터: 홍창기 (3/22 LG vs 롯데)
        table2: ['2땅', '사구', '우중2', '&nbsp;', '4구', '&nbsp;', '좌안', '&nbsp;', '&nbsp;']
        table3: [3, 2, 2, 0, 0.667]  (AB=3, H=2, RBI=2, R=0)
        """
        cells = ["2땅", "사구", "우중2", "&nbsp;", "4구", "&nbsp;", "좌안", "&nbsp;", "&nbsp;"]
        stats = parse_player_innings(cells)
        assert stats.pa == 5
        assert stats.ab == 3   # 사구, 4구 제외
        assert stats.hits == 2  # 우중2 + 좌안
        assert stats.doubles == 1
        assert stats.singles == 1
        assert stats.hbp == 1
        assert stats.bb == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
