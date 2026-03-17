import { useState } from "react";
import { formatStat } from "../../utils/formatStat";
import PlayerLink from "./PlayerLink";
import "./StatTable.css";

/**
 * StatTable — 공용 정렬 가능 테이블
 *
 * Props:
 *   columns  : [{ key, label, format }]  — format은 formatStat의 statName
 *   data     : [{ player_id, player_name, team_name, ...stats }]
 *   onPlayerClick : (playerId) => void  (선택)
 *   sortable : boolean (기본 true)
 */
function StatTable({ columns = [], data = [], onPlayerClick, sortable = true }) {
  const [sortKey, setSortKey] = useState(columns[0]?.key ?? "");
  const [sortDir, setSortDir] = useState("desc");

  function handleSort(key) {
    if (!sortable) return;
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sorted = sortable && sortKey
    ? [...data].sort((a, b) => {
        const av = a[sortKey] ?? (sortDir === "desc" ? -Infinity : Infinity);
        const bv = b[sortKey] ?? (sortDir === "desc" ? -Infinity : Infinity);
        return sortDir === "desc" ? bv - av : av - bv;
      })
    : data;

  if (!data.length) {
    return <p className="table-empty">데이터가 없습니다.</p>;
  }

  return (
    <div className="stat-table-wrapper">
      <table className="stat-table">
        <thead>
          <tr>
            <th className="col-rank">#</th>
            <th className="col-player">선수</th>
            <th className="col-team">팀</th>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`col-stat${sortable ? " sortable" : ""}${sortKey === col.key ? " sorted" : ""}`}
                onClick={() => handleSort(col.key)}
                title={sortable ? "클릭하여 정렬" : undefined}
              >
                {col.label}
                {sortable && sortKey === col.key && (
                  <span className="sort-icon">{sortDir === "desc" ? " ▼" : " ▲"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, idx) => (
            <tr key={row.player_id ?? idx}>
              <td className="col-rank">{idx + 1}</td>
              <td className="col-player">
                {onPlayerClick ? (
                  <button
                    className="player-btn"
                    onClick={() => onPlayerClick(row.player_id)}
                  >
                    {row.player_name}
                  </button>
                ) : (
                  <PlayerLink playerId={row.player_id} name={row.player_name} />
                )}
              </td>
              <td className="col-team">{row.team_name}</td>
              {columns.map((col) => (
                <td key={col.key} className="col-stat">
                  {formatStat(col.format ?? col.key, row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default StatTable;
