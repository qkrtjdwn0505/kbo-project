import StatTable from "../common/StatTable";
import { STAT_LABELS } from "../../utils/constants";

/**
 * Explorer 결과 테이블
 * API 결과(results)를 StatTable에 맞는 형태로 변환
 */
export default function ResultTable({ results = [], stat }) {
  if (!results.length) return null;

  // primary_stat + secondary_stats(hr, rbi, ops 또는 era, whip, so_count)를 flat하게 펼침
  const flatData = results.map((row) => ({
    player_id: row.player_id,
    player_name: row.player_name,
    team_name: row.team_name,
    [stat]: row.primary_stat,
    ...row.secondary_stats,
  }));

  // primary stat column
  const primaryCol = { key: stat, label: STAT_LABELS[stat] ?? stat, format: stat };

  // secondary stat columns
  const secondaryCols = Object.keys(results[0]?.secondary_stats ?? {}).map((k) => ({
    key: k,
    label: STAT_LABELS[k] ?? k,
    format: k,
  }));

  const columns = [primaryCol, ...secondaryCols];

  return <StatTable columns={columns} data={flatData} sortable={false} />;
}
