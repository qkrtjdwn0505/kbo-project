export const API_BASE = "/api/v1";

export const CURRENT_SEASON = 2025;

export const TEAM_NAMES = {
  1: "KIA", 2: "삼성", 3: "LG", 4: "두산", 5: "KT",
  6: "SSG", 7: "롯데", 8: "한화", 9: "NC", 10: "키움",
};

export const STAT_LABELS = {
  avg: "타율", obp: "출루율", slg: "장타율", ops: "OPS",
  hr: "홈런", rbi: "타점", runs: "득점", sb: "도루",
  bb: "볼넷", so: "삼진", hits: "안타", pa: "타석",
  woba: "wOBA", wrc_plus: "wRC+", war: "WAR", babip: "BABIP",
  iso: "ISO", bb_pct: "BB%", k_pct: "K%", ops_risp: "OPS(RISP)",
  era: "ERA", fip: "FIP", xfip: "xFIP", whip: "WHIP",
  wins: "승", losses: "패", saves: "세이브", holds: "홀드",
  so_count: "삼진", k_per_9: "K/9", bb_per_9: "BB/9",
  hr_per_9: "HR/9", k_bb_ratio: "K/BB",
};

export const CONDITION_LABELS = {
  all: "전체",
  vs_lhp: "vs 좌투",
  vs_rhp: "vs 우투",
  risp: "득점권",
  bases_loaded: "만루",
  no_runners: "주자없음",
  inning_1_3: "1~3이닝",
  inning_4_6: "4~6이닝",
  inning_7_9: "7~9이닝",
  home: "홈경기",
  away: "원정경기",
  weekday: "주중",
  weekend: "주말",
  night: "야간",
  day: "주간",
  leading: "리드시",
  tied: "동점시",
  trailing: "뒤질때",
};

export const TARGET_LABELS = {
  batter: "타자",
  pitcher: "투수 (전체)",
  pitcher_starter: "선발투수",
  pitcher_bullpen: "불펜투수",
};

export const LIMIT_OPTIONS = [
  { value: "5",  label: "상위 5명" },
  { value: "10", label: "상위 10명" },
  { value: "20", label: "상위 20명" },
  { value: "all", label: "전체" },
];

export const SORT_OPTIONS = [
  { value: "desc", label: "내림차순" },
  { value: "asc",  label: "오름차순" },
];

export const TEAM_COLORS = {
  "KIA":  "#e3002c",
  "삼성": "#074ca1",
  "LG":   "#c30452",
  "두산": "#131230",
  "KT":   "#000000",
  "SSG":  "#ce0e2d",
  "롯데": "#041e42",
  "한화": "#ff6600",
  "NC":   "#315288",
  "키움": "#820024",
};

export const STAT_TOOLTIPS = {
  woba:      "가중 출루율 — 타석 결과에 가중치를 부여한 종합 출루 지표",
  wrc_plus:  "조정 득점 기여 — 리그·구장 보정. 100이 평균, 높을수록 좋음",
  war:       "대체 선수 대비 승리 기여 (간소화 WAR)",
  babip:     "인플레이 타구 안타율 — .300 이하면 불운, 이상이면 행운 가능성",
  iso:       "순장타율 (SLG − AVG) — 장타력 지표",
  bb_pct:    "볼넷 비율 — 선구안·타석 장악력",
  k_pct:     "삼진 비율 — 낮을수록 컨택 능력 우수",
  fip:       "수비 무관 투구 — 투수 본인 책임 지표만 반영 (HR, BB, K)",
  xfip:      "기대 FIP — 홈런을 리그 평균 FB 비율로 보정 (FB 미수집으로 현재 미계산)",
  babip_p:   "인플레이 피안타율 — .290 이하면 투수 행운 가능성",
  lob_pct:   "잔루 비율 — 높을수록 위기 탈출 능력 우수",
  k_per_9:   "9이닝당 탈삼진",
  bb_per_9:  "9이닝당 볼넷",
  hr_per_9:  "9이닝당 피홈런",
  k_bb_ratio: "삼진/볼넷 비율 — 높을수록 지배력 강함",
};
