// 타율/승률: .328 (소수점 3자리, 앞 0 없음)
export function formatAvg(value) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(3).replace(/^0/, "");
}

// ERA/FIP/WHIP: 3.45 (소수점 2자리)
export function formatEra(value) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(2);
}

// WAR/wRC+/ISO: 7.2 (소수점 1자리)
export function formatWar(value) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(1);
}

// 정수 (홈런, 타점)
export function formatInt(value) {
  if (value === null || value === undefined) return "-";
  return String(Math.round(value));
}

// 퍼센트 (BB%, K%): 12.3%
export function formatPct(value) {
  if (value === null || value === undefined) return "-";
  return (value * 100).toFixed(1) + "%";
}

const AVG_STATS  = new Set([
  "avg", "obp", "slg", "ops", "woba", "babip", "win_pct",
  "ops_vs_lhp", "ops_vs_rhp", "ops_risp", "ops_home", "ops_away",
]);
const ERA_STATS  = new Set(["era", "fip", "xfip", "whip"]);
const WAR_STATS  = new Set(["war", "wrc_plus", "iso", "k_per_9", "bb_per_9", "hr_per_9", "k_bb_ratio"]);
const PCT_STATS  = new Set(["bb_pct", "k_pct", "lob_pct"]);

// 지표명 → 자동 포맷
export function formatStat(statName, value) {
  if (AVG_STATS.has(statName)) return formatAvg(value);
  if (ERA_STATS.has(statName)) return formatEra(value);
  if (WAR_STATS.has(statName)) return formatWar(value);
  if (PCT_STATS.has(statName)) return formatPct(value);
  return formatInt(value);
}
