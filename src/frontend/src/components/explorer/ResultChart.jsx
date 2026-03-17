import BarChart from "../common/BarChart";
import { STAT_LABELS } from "../../utils/constants";
import "./ResultChart.css";

/**
 * Explorer 결과 차트
 * limit="all" 이거나 결과 없으면 숨김
 */
export default function ResultChart({ results = [], stat, limit }) {
  if (limit === "all" || results.length === 0) return null;

  const labels = results.map((r) => `${r.player_name} (${r.team_name})`);
  const values = results.map((r) => r.primary_stat);
  const statLabel = STAT_LABELS[stat] ?? stat;

  return (
    <div className="result-chart card mt-8">
      <h3 className="result-chart-title">{statLabel} 시각화</h3>
      <BarChart
        labels={labels}
        values={values}
        statName={stat}
        color="#1a365d"
      />
    </div>
  );
}
