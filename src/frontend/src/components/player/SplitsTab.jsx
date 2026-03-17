import { formatStat } from "../../utils/formatStat";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import "./SplitsTab.css";

function formatSplitValue(statName, value) {
  if (value === null || value === undefined || value === 0) return "—";
  return formatStat(statName, value);
}

/**
 * 타자(OPS): 높을수록 좋음 → max 강조
 * 투수(ERA): 낮을수록 좋음 (단, 0.0은 미계산) → 둘 다 유효할 때 min 강조
 */
function isBetter(playerType, a, b) {
  if (a === 0 || b === 0) return false;
  return playerType === "batter" ? a > b : a < b;
}

/** splits flat list를 [{ title, items: [label, value][] }] 구조로 묶기 */
function groupSplits(splits, playerType) {
  if (playerType === "batter") {
    return [
      {
        title: "vs 투수 유형",
        stat: "ops",
        items: splits.filter((s) => s.label === "vs 좌투" || s.label === "vs 우투"),
      },
      {
        title: "홈 / 원정",
        stat: "ops",
        items: splits.filter((s) => s.label === "홈" || s.label === "원정"),
      },
      {
        title: "득점권",
        stat: "ops",
        items: splits.filter((s) => s.label === "득점권"),
      },
    ];
  } else {
    return [
      {
        title: "vs 타자 유형",
        stat: "era",
        items: splits.filter((s) => s.label === "vs 좌타" || s.label === "vs 우타"),
      },
      {
        title: "홈 / 원정",
        stat: "era",
        items: splits.filter((s) => s.label === "홈" || s.label === "원정"),
      },
    ];
  }
}

function SplitSection({ title, stat, items, playerType }) {
  if (items.length === 0) return null;

  if (items.length === 1) {
    // 득점권처럼 단독 값
    const item = items[0];
    return (
      <div className="split-section">
        <h4 className="split-section-title">{title}</h4>
        <table className="split-table">
          <thead>
            <tr>
              <th className="split-th-stat">{stat.toUpperCase()}</th>
              <th>{item.label}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="split-stat-label">{stat.toUpperCase()}</td>
              <td className="split-value">{formatSplitValue(stat, item.value)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  // 2-item pair
  const [left, right] = items;
  const leftBetter  = isBetter(playerType, left.value,  right.value);
  const rightBetter = isBetter(playerType, right.value, left.value);

  return (
    <div className="split-section">
      <h4 className="split-section-title">{title}</h4>
      <table className="split-table">
        <thead>
          <tr>
            <th className="split-th-stat"></th>
            <th>{left.label}</th>
            <th>{right.label}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="split-stat-label">{stat.toUpperCase()}</td>
            <td className={`split-value${leftBetter  ? " split-value--best" : ""}`}>
              {formatSplitValue(stat, left.value)}
            </td>
            <td className={`split-value${rightBetter ? " split-value--best" : ""}`}>
              {formatSplitValue(stat, right.value)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function SplitsTab({ data, loading, error }) {
  if (loading) return <LoadingSpinner />;
  if (error)   return <ErrorMessage error={{ message: error }} />;
  if (!data)   return null;

  const { player_type, splits, season } = data;
  const groups = groupSplits(splits, player_type);

  return (
    <div className="splits-tab">
      <div className="tab-season-badge">{season}시즌</div>
      <p className="splits-hint">
        {player_type === "batter"
          ? "— 은 데이터 미계산. 강조 색상 = 높은 OPS."
          : "— 은 데이터 미계산. 강조 색상 = 낮은 ERA."}
      </p>
      <div className="splits-sections">
        {groups.map((g) => (
          <SplitSection
            key={g.title}
            title={g.title}
            stat={g.stat}
            items={g.items}
            playerType={player_type}
          />
        ))}
      </div>
    </div>
  );
}
