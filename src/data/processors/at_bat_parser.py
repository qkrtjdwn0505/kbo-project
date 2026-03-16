"""KBO 박스스코어 table2 타석 결과 코드 파서

KBO 게임센터 박스스코어의 이닝별 타석 결과(table2)를 파싱하여
세이버메트릭스 계산에 필요한 상세 기록을 추출합니다.

코드 체계:
    [위치][결과]
    위치: 좌, 우, 중, 좌중, 우중, 유, 1, 2, 3, 투, 포
    결과: 안(1B), 2(2B), 3(3B), 홈(HR), 비(플라이), 땅(그라운드),
          파(파울플라이), 직(라인드라이브), 병(병살), 희비(희생플라이),
          희번(희생번트), 실(실책)

복합 타석: "<br />/ " 구분자로 대타/교체 시 복수 결과가 연결됨.
    예: "4구<br />/ 투땅" → 첫 번째 결과(4구)만 해당 타자 기록.

참고: 2025 시즌 35경기 2,737 타석에서 103개 고유 코드 확인.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AtBatResult:
    """단일 타석의 파싱된 결과"""

    pa: int = 0        # 타석
    ab: int = 0        # 타수
    hit: int = 0       # 안타 (1B+2B+3B+HR)
    single: int = 0    # 1루타
    double: int = 0    # 2루타
    triple: int = 0    # 3루타
    hr: int = 0        # 홈런
    bb: int = 0        # 볼넷 (고의사구 포함)
    ibb: int = 0       # 고의사구
    hbp: int = 0       # 사구 (몸에 맞는 공)
    so: int = 0        # 삼진
    sf: int = 0        # 희생플라이
    sh: int = 0        # 희생번트
    gdp: int = 0       # 병살타
    sb: int = 0        # 도루
    cs: int = 0        # 도루실패
    fc: int = 0        # 야수선택
    error: int = 0     # 실책 출루 (상대 실책)


@dataclass
class PlayerGameStats:
    """한 경기에서 한 선수의 table2 기반 누적 기록"""

    pa: int = 0
    ab: int = 0
    hits: int = 0
    singles: int = 0
    doubles: int = 0
    triples: int = 0
    hr: int = 0
    rbi: int = 0       # table3에서 가져옴
    runs: int = 0      # table3에서 가져옴
    bb: int = 0
    ibb: int = 0
    hbp: int = 0
    so: int = 0
    sf: int = 0
    sh: int = 0
    gdp: int = 0
    sb: int = 0
    cs: int = 0

    def add(self, result: AtBatResult) -> None:
        """타석 결과를 누적"""
        self.pa += result.pa
        self.ab += result.ab
        self.hits += result.hit
        self.singles += result.single
        self.doubles += result.double
        self.triples += result.triple
        self.hr += result.hr
        self.bb += result.bb
        self.ibb += result.ibb
        self.hbp += result.hbp
        self.so += result.so
        self.sf += result.sf
        self.sh += result.sh
        self.gdp += result.gdp
        self.sb += result.sb
        self.cs += result.cs


# ─── 코드 분류 패턴 ──────────────────────────────────────

# 홈런: *홈 (좌홈, 우홈, 중홈, 우중홈, 좌중홈)
_HR_PATTERN = re.compile(r"홈$")

# 3루타: 방향 + "3" (우3, 좌3, 우중3, 좌중3) — 숫자 포지션(3루수)과 구분 필요
_TRIPLE_PATTERN = re.compile(r"^(좌|우|중|좌중|우중)3$")

# 2루타: 방향 + "2" (우2, 좌2, 중2, 우중2, 좌중2) — "22" 같은 것도 포함
_DOUBLE_PATTERN = re.compile(r"^(좌|우|중|좌중|우중)2$")

# 안타: *안 (좌안, 우안, 중안, 유안, 투안, 1안, 2안, 3안 등)
# 복합: 투유안, 투우안, 투1안, 투3안, 3좌안, 1우안, 유중안
_SINGLE_PATTERN = re.compile(r"안")

# 볼넷: 4구
# 고의사구: 고4
_BB_EXACT = {"4구"}
_IBB_EXACT = {"고4"}

# 사구(HBP)
_HBP_EXACT = {"사구"}

# 삼진: 삼진, 스낫(스트라이크 낫아웃)
_SO_EXACT = {"삼진", "스낫"}

# 희생플라이: *희비
_SF_PATTERN = re.compile(r"희비$")

# 희생번트: *희번, *희선(희생번트 상황 야수선택)
_SH_PATTERN = re.compile(r"희번$|희선$")

# 병살: *병
_GDP_PATTERN = re.compile(r"병$")

# 야수선택: 야선
_FC_EXACT = {"야선"}

# 도루: 코드에 "도루" 포함 (실제 table2에서는 거의 안 나옴)
_SB_EXACT = {"도루"}
_CS_EXACT = {"도실"}

# 범타/아웃 패턴: *땅, *비, *파, *직, *플, *번, *실
_OUT_PATTERN = re.compile(r"(땅|비|파|직|플|번|실)$")


def parse_at_bat_code(code: str) -> AtBatResult:
    """단일 타석 결과 코드를 파싱

    Args:
        code: KBO table2 셀 값 (예: "좌안", "삼진", "우중2", "4구")

    Returns:
        AtBatResult: 해당 타석의 분류된 결과

    복합 타석 처리:
        "4구<br />/ 투땅" 같은 코드는 첫 번째 결과만 해당 타자 것.
        두 번째는 대타/교체 후 타자의 결과이므로 무시.
    """
    if not code or code in ("&nbsp;", "TOTAL", ""):
        return AtBatResult()

    # 복합 타석: 첫 번째 결과만 사용
    if "<br />" in code:
        code = code.split("<br />")[0].strip()
        # "/" 뒤의 공백도 제거
        if code.endswith("/"):
            code = code[:-1].strip()

    code = code.strip()
    if not code:
        return AtBatResult()

    result = AtBatResult(pa=1)

    # === 타수에 포함되지 않는 결과 먼저 체크 ===

    # 볼넷 (BB) — 타수 미포함
    if code in _BB_EXACT:
        result.bb = 1
        return result

    # 고의사구 (IBB) — 타수 미포함, BB에도 포함
    if code in _IBB_EXACT:
        result.bb = 1
        result.ibb = 1
        return result

    # 사구 (HBP) — 타수 미포함
    if code in _HBP_EXACT:
        result.hbp = 1
        return result

    # 희생번트 (SH) — 타석은 카운트하지만 타수 미포함
    if _SH_PATTERN.search(code):
        result.sh = 1
        return result

    # 희생플라이 (SF) — 타수 미포함
    if _SF_PATTERN.search(code):
        result.sf = 1
        return result

    # === 여기서부터 타수(AB)에 포함 ===
    result.ab = 1

    # 홈런 (HR)
    if _HR_PATTERN.search(code):
        result.hr = 1
        result.hit = 1
        return result

    # 3루타 (3B) — 방향+3 패턴만 (3루수 관련 코드와 구분)
    if _TRIPLE_PATTERN.match(code):
        result.triple = 1
        result.hit = 1
        return result

    # 2루타 (2B) — 방향+2 패턴, "22" 특수 케이스 포함
    if _DOUBLE_PATTERN.match(code) or code == "22":
        result.double = 1
        result.hit = 1
        return result

    # 안타 (1B) — "안" 포함
    if _SINGLE_PATTERN.search(code):
        result.single = 1
        result.hit = 1
        return result

    # 삼진 (SO)
    if code in _SO_EXACT:
        result.so = 1
        return result

    # 병살 (GDP)
    if _GDP_PATTERN.search(code):
        result.gdp = 1
        return result

    # 야수선택 (FC) — 타수 소모, 안타 아님
    if code in _FC_EXACT:
        result.fc = 1
        return result

    # 나머지: 범타/아웃 (땅볼, 플라이, 파울플라이, 라인아웃 등)
    # 실책 출루도 여기에 포함 (타수 소모, 안타 아님)
    return result


def parse_player_innings(
    inning_cells: list[str],
) -> PlayerGameStats:
    """한 선수의 전 이닝 table2 결과를 합산

    Args:
        inning_cells: table2의 한 행 — 이닝별 타석 결과 리스트
            예: ["삼진", "&nbsp;", "삼진", "포파", "&nbsp;", ...]

    Returns:
        PlayerGameStats: 해당 경기 누적 기록
    """
    stats = PlayerGameStats()
    for cell in inning_cells:
        cell = cell.strip()
        if not cell or cell in ("&nbsp;", "TOTAL", ""):
            continue
        result = parse_at_bat_code(cell)
        stats.add(result)
    return stats
