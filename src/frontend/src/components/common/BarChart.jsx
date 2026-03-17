import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import { formatStat } from "../../utils/formatStat";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

/**
 * BarChart — 수평 막대 그래프 래퍼
 *
 * Props:
 *   labels   : string[]
 *   values   : number[]
 *   statName : string (포맷용)
 *   color    : string (기본 primary)
 *   title    : string (선택)
 */
function BarChart({
  labels = [],
  values = [],
  statName = "avg",
  color = "#1a365d",
  title,
}) {
  const data = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: color + "cc", // 80% opacity
        borderColor: color,
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const options = {
    indexAxis: "y",          // 수평 막대
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${formatStat(statName, ctx.raw)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { color: "#e2e8f0" },
        ticks: { font: { size: 12 } },
      },
      y: {
        grid: { display: false },
        ticks: { font: { size: 13 } },
      },
    },
  };

  return (
    <div className="bar-chart-wrapper">
      {title && <h3 className="chart-title">{title}</h3>}
      <div style={{ height: Math.max(labels.length * 40, 120) }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}

export default BarChart;
