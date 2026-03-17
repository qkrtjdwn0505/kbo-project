import { Link } from "react-router-dom";
import { formatAvg } from "../../utils/formatStat";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import "./TeamRankTable.css";

function Recent5({ recent5 }) {
  return (
    <span className="recent5">
      {recent5.map((r, i) => {
        let cls = "r5-dot";
        if (r === "W") cls += " r5-win";
        else if (r === "L") cls += " r5-loss";
        else cls += " r5-draw";
        const symbol = r === "W" ? "●" : r === "L" ? "○" : "△";
        return (
          <span key={i} className={cls} title={r}>
            {symbol}
          </span>
        );
      })}
    </span>
  );
}

/** limit=0은 전체 표시 */
export default function TeamRankTable({
  standings = [],
  loading,
  error,
  limit = 0,
  showViewAll = false,
}) {
  if (loading) return <LoadingSpinner />;
  if (error)   return <ErrorMessage error={{ message: error }} />;
  if (!standings.length) return null;

  const rows = limit > 0 ? standings.slice(0, limit) : standings;

  return (
    <div className="rank-table-wrapper">
      <table className="rank-table">
        <thead>
          <tr>
            <th className="col-rank">순위</th>
            <th className="col-team">팀</th>
            <th className="col-num">경기</th>
            <th className="col-num">승</th>
            <th className="col-num">패</th>
            <th className="col-num">무</th>
            <th className="col-pct">승률</th>
            <th className="col-gb">게임차</th>
            <th className="col-recent">최근5</th>
            <th className="col-streak">흐름</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.team_id} className={row.rank === 1 ? "row-first" : ""}>
              <td className="col-rank">{row.rank}</td>
              <td className="col-team team-name">{row.team_name}</td>
              <td className="col-num">{row.games}</td>
              <td className="col-num">{row.wins}</td>
              <td className="col-num">{row.losses}</td>
              <td className="col-num">{row.draws}</td>
              <td className="col-pct">{formatAvg(row.win_pct)}</td>
              <td className="col-gb">{row.games_behind === 0 ? "−" : row.games_behind.toFixed(1)}</td>
              <td className="col-recent">
                <Recent5 recent5={row.recent_5} />
              </td>
              <td className="col-streak">
                <span className={`streak${row.streak.includes("연승") ? " streak-win" : row.streak.includes("연패") ? " streak-loss" : ""}`}>
                  {row.streak}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {showViewAll && (
        <div className="view-all-row">
          <Link to="/standings" className="view-all-link">
            전체 순위 보기 →
          </Link>
        </div>
      )}
    </div>
  );
}
