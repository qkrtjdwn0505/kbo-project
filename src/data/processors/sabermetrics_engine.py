"""KBO 세이버메트릭스 계산 엔진

design.md 섹션 5의 공식을 구현합니다.
모든 함수는 순수 함수(pure function)로, DB 접근 없이 입력값만으로 계산합니다.

리그 상수:
    wOBA, wRC+ 계산에는 시즌별 KBO 리그 상수가 필요합니다.
    league_constants 테이블에서 가져와 인자로 전달합니다.

주의:
    - 분모가 0인 경우 None을 반환 (0이 아닌 None — "계산 불가"와 "값이 0"을 구분)
    - ip_outs(아웃 카운트)를 이닝으로 변환: ip = ip_outs / 3
    - WAR는 간소화 버전 (수비/구장 보정 제외, 주석으로 명시)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LeagueConstants:
    """시즌별 KBO 리그 상수

    KBReport STAT Dic 또는 자체 계산에서 가져옴.
    """

    season: int
    # wOBA 가중치
    w_bb: float = 0.69
    w_hbp: float = 0.72
    w_1b: float = 0.89
    w_2b: float = 1.27
    w_3b: float = 1.62
    w_hr: float = 2.10
    # 리그 평균
    woba_scale: float = 1.15
    league_woba: float = 0.320
    league_obp: float = 0.340
    # wRC+ 관련
    rppa: float = 0.12          # runs per plate appearance
    league_rpw: float = 10.0    # runs per win
    league_r_pa: float = 0.12   # 리그 평균 R/PA (wRC+ 분모용)
    # FIP/xFIP 관련
    fip_constant: float = 3.10
    league_hr_fb_rate: float = 0.10  # 리그 평균 HR/FB 비율


# ═══════════════════════════════════════════════════════
#  타자 지표
# ═══════════════════════════════════════════════════════


def calc_avg(hits: int, ab: int) -> Optional[float]:
    """타율 (AVG) = H / AB"""
    if ab == 0:
        return None
    return hits / ab


def calc_obp(
    hits: int, bb: int, hbp: int,
    ab: int, sf: int,
) -> Optional[float]:
    """출루율 (OBP) = (H + BB + HBP) / (AB + BB + HBP + SF)"""
    denom = ab + bb + hbp + sf
    if denom == 0:
        return None
    return (hits + bb + hbp) / denom


def calc_slg(
    singles: int, doubles: int, triples: int, hr: int, ab: int,
) -> Optional[float]:
    """장타율 (SLG) = TB / AB"""
    if ab == 0:
        return None
    tb = singles + 2 * doubles + 3 * triples + 4 * hr
    return tb / ab


def calc_ops(obp: Optional[float], slg: Optional[float]) -> Optional[float]:
    """OPS = OBP + SLG"""
    if obp is None or slg is None:
        return None
    return obp + slg


def calc_iso(slg: Optional[float], avg: Optional[float]) -> Optional[float]:
    """순장타율 (ISO) = SLG - AVG"""
    if slg is None or avg is None:
        return None
    return slg - avg


def calc_babip(
    hits: int, hr: int, ab: int, so: int, sf: int,
) -> Optional[float]:
    """BABIP = (H - HR) / (AB - SO - HR + SF)"""
    denom = ab - so - hr + sf
    if denom == 0:
        return None
    return (hits - hr) / denom


def calc_bb_pct(bb: int, pa: int) -> Optional[float]:
    """볼넷% (BB%) = BB / PA"""
    if pa == 0:
        return None
    return bb / pa


def calc_k_pct(so: int, pa: int) -> Optional[float]:
    """삼진% (K%) = SO / PA"""
    if pa == 0:
        return None
    return so / pa


def calc_woba(
    bb: int, ibb: int, hbp: int,
    singles: int, doubles: int, triples: int, hr: int,
    ab: int, sf: int,
    lc: LeagueConstants,
) -> Optional[float]:
    """wOBA (Weighted On-Base Average)

    wOBA = (w_BB*(BB-IBB) + w_HBP*HBP + w_1B*1B + w_2B*2B + w_3B*3B + w_HR*HR)
           / (AB + BB - IBB + SF + HBP)

    IBB가 없는 경우(ibb=0) 분모에서 차감하지 않음.
    """
    denom = ab + bb - ibb + sf + hbp
    if denom == 0:
        return None
    numer = (
        lc.w_bb * (bb - ibb)
        + lc.w_hbp * hbp
        + lc.w_1b * singles
        + lc.w_2b * doubles
        + lc.w_3b * triples
        + lc.w_hr * hr
    )
    return numer / denom


def calc_wraa(
    woba: Optional[float], pa: int, lc: LeagueConstants,
) -> Optional[float]:
    """wRAA (Weighted Runs Above Average)

    wRAA = ((wOBA - lgwOBA) / wOBA_scale) * PA
    """
    if woba is None or pa == 0:
        return None
    return ((woba - lc.league_woba) / lc.woba_scale) * pa


def calc_wrc_plus(
    woba: Optional[float], pa: int, lc: LeagueConstants,
) -> Optional[float]:
    """wRC+ (Weighted Runs Created Plus)

    wRC+ = (((wOBA - lgwOBA) / wOBA_scale + R/PA) / lg_R/PA) * 100

    100 = 리그 평균. >100 평균 이상, <100 평균 이하.
    """
    if woba is None or pa == 0 or lc.league_r_pa == 0:
        return None
    runs_per_pa = (woba - lc.league_woba) / lc.woba_scale + lc.rppa
    return (runs_per_pa / lc.league_r_pa) * 100


def calc_batter_war_simplified(
    woba: Optional[float], pa: int, lc: LeagueConstants,
) -> Optional[float]:
    """타자 WAR 간소화 버전 (fWAR 기반, 수비/구장 보정 제외)

    ⚠️ 이 WAR는 공격 기여도만 반영합니다.
    정확한 WAR 계산에는 UZR(수비지표), 포지션 보정, 구장 보정이
    필요하나 현재 데이터에 없어 제외했습니다.
    UI에 "공격 WAR (수비 미포함)" 등으로 표시 권장.

    계산: wRAA / RPW
        RPW = Runs Per Win (보통 10 내외)
    """
    wraa = calc_wraa(woba, pa, lc)
    if wraa is None or lc.league_rpw == 0:
        return None
    # 대체 수준(replacement level) 보정: 약 20 runs/600PA
    replacement_runs = (20.0 / 600.0) * pa
    return (wraa + replacement_runs) / lc.league_rpw


# ═══════════════════════════════════════════════════════
#  투수 지표
# ═══════════════════════════════════════════════════════


def ip_outs_to_ip(ip_outs: int) -> float:
    """아웃 카운트를 이닝으로 변환 (18 → 6.0, 14 → 4.667)"""
    return ip_outs / 3.0


def calc_era(er: int, ip_outs: int) -> Optional[float]:
    """ERA = (ER * 9) / IP"""
    ip = ip_outs_to_ip(ip_outs)
    if ip == 0:
        return None
    return (er * 9) / ip


def calc_whip(
    hits_allowed: int, bb_allowed: int, ip_outs: int,
) -> Optional[float]:
    """WHIP = (H + BB) / IP"""
    ip = ip_outs_to_ip(ip_outs)
    if ip == 0:
        return None
    return (hits_allowed + bb_allowed) / ip


def calc_fip(
    hr_allowed: int, bb_allowed: int, hbp_allowed: int,
    so_count: int, ip_outs: int,
    lc: LeagueConstants,
) -> Optional[float]:
    """FIP (Fielding Independent Pitching)

    FIP = ((13*HR + 3*(BB+HBP) - 2*SO) / IP) + FIP_constant
    """
    ip = ip_outs_to_ip(ip_outs)
    if ip == 0:
        return None
    return (
        (13 * hr_allowed + 3 * (bb_allowed + hbp_allowed) - 2 * so_count)
        / ip
        + lc.fip_constant
    )


def calc_xfip(
    fb_count: Optional[int],
    bb_allowed: int, hbp_allowed: int,
    so_count: int, ip_outs: int,
    lc: LeagueConstants,
) -> Optional[float]:
    """xFIP (Expected FIP)

    xFIP = ((13 * (FB * lg_HR/FB) + 3*(BB+HBP) - 2*SO) / IP) + FIP_constant

    FB(플라이볼) 데이터가 없으면 None 반환.
    현재 KBO 수집 데이터에 FB 카운트가 없으므로 MVP에서는 None.
    """
    if fb_count is None:
        return None
    ip = ip_outs_to_ip(ip_outs)
    if ip == 0:
        return None
    expected_hr = fb_count * lc.league_hr_fb_rate
    return (
        (13 * expected_hr + 3 * (bb_allowed + hbp_allowed) - 2 * so_count)
        / ip
        + lc.fip_constant
    )


def calc_per_9(count: int, ip_outs: int) -> Optional[float]:
    """K/9, BB/9, HR/9 등 per-9-innings 지표

    = (count * 9) / IP
    """
    ip = ip_outs_to_ip(ip_outs)
    if ip == 0:
        return None
    return (count * 9) / ip


def calc_k_bb_ratio(so_count: int, bb_allowed: int) -> Optional[float]:
    """K/BB 비율"""
    if bb_allowed == 0:
        return None
    return so_count / bb_allowed


def calc_pitcher_babip(
    hits_allowed: int, hr_allowed: int,
    ip_outs: int, so_count: int,
) -> Optional[float]:
    """투수 BABIP = (H - HR) / (BFP - SO - HR - BB - HBP)

    정확한 BFP(대면 타자 수)가 없으므로 근사값 사용:
    BFP ≈ IP*3 + H + BB (간이 공식)
    여기서는 (IP_outs + H_allowed - HR_allowed) 를 분모로 근사.

    근사 공식: (H - HR) / (IP_outs + H - HR - SO) * (outs per BIP 보정)
    → 정확도 한계가 있으므로 BFP 데이터 확보 후 개선 필요.
    """
    # 간이 분모: 인플레이 타구 = 아웃(IP*3에서 삼진 제외) + 안타 - 홈런
    bip = (ip_outs - so_count) + (hits_allowed - hr_allowed)
    if bip == 0:
        return None
    return (hits_allowed - hr_allowed) / bip


def calc_pitcher_war_simplified(
    fip: Optional[float], ip_outs: int, lc: LeagueConstants,
) -> Optional[float]:
    """투수 WAR 간소화 버전 (FIP 기반, 구장 보정 제외)

    ⚠️ 구장 보정(Park Factor) 제외된 간소화 버전입니다.
    UI에 "FIP 기반 WAR (구장 미보정)" 등으로 표시 권장.

    계산:
        FIP_runs_above_replacement = ((lg_FIP - FIP) / 9) * IP + replacement
        WAR = runs / RPW
    여기서 lg_FIP ≈ ERA 리그 평균으로 근사 (fip_constant + 리그 평균 차이)
    """
    if fip is None or ip_outs == 0 or lc.league_rpw == 0:
        return None
    ip = ip_outs_to_ip(ip_outs)
    # 리그 평균 FIP ≈ fip_constant + 0.0 (정의상 fip_constant가 보정값)
    # → 리그 평균 ERA를 FIP로 근사: ~4.50 (KBO 평균)
    lg_fip = 4.50
    runs_above_avg = ((lg_fip - fip) / 9.0) * ip
    replacement_runs = (20.0 / 600.0) * ip * 3  # 대체 수준 보정
    return (runs_above_avg + replacement_runs) / lc.league_rpw
