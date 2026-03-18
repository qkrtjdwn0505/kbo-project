import { Link } from "react-router-dom";
import { TEAM_COLORS } from "../../utils/constants";
import "./RecordsTable.css";

// ── 컬럼 정의 ───────────────────────────────────────────

const BATTER_CLASSIC = [
  { key: "games", label: "G" },
  { key: "pa", label: "PA" },
  { key: "avg", label: "타율", fmt: "avg3" },
  { key: "obp", label: "출루율", fmt: "avg3" },
  { key: "slg", label: "장타율", fmt: "avg3" },
  { key: "ops", label: "OPS", fmt: "avg3" },
  { key: "hr", label: "HR" },
  { key: "rbi", label: "타점" },
  { key: "runs", label: "득점" },
  { key: "sb", label: "도루" },
  { key: "bb", label: "BB" },
  { key: "so", label: "K" },
];

const BATTER_SABER = [
  { key: "games", label: "G" },
  { key: "pa", label: "PA" },
  { key: "woba", label: "wOBA", fmt: "avg3" },
  { key: "wrc_plus", label: "wRC+", fmt: "f1" },
  { key: "war", label: "WAR", fmt: "f1" },
  { key: "babip", label: "BABIP", fmt: "avg3" },
  { key: "iso", label: "ISO", fmt: "avg3" },
  { key: "bb_pct", label: "BB%", fmt: "pct1" },
  { key: "k_pct", label: "K%", fmt: "pct1" },
];

const PITCHER_CLASSIC = [
  { key: "games", label: "G" },
  { key: "wins", label: "W" },
  { key: "losses", label: "L" },
  { key: "saves", label: "S" },
  { key: "holds", label: "H" },
  { key: "ip_display", label: "IP", sortKey: "games" },
  { key: "so_count", label: "K" },
  { key: "bb_allowed", label: "BB" },
  { key: "era", label: "ERA", fmt: "f2" },
  { key: "whip", label: "WHIP", fmt: "f2" },
];

const PITCHER_SABER = [
  { key: "games", label: "G" },
  { key: "ip_display", label: "IP", sortKey: "games" },
  { key: "era", label: "ERA", fmt: "f2" },
  { key: "fip", label: "FIP", fmt: "f2" },
  { key: "xfip", label: "xFIP", fmt: "f2" },
  { key: "war", label: "WAR", fmt: "f1" },
  { key: "babip", label: "BABIP", fmt: "avg3" },
  { key: "lob_pct", label: "LOB%", fmt: "pct1" },
  { key: "k_per_9", label: "K/9", fmt: "f2" },
  { key: "bb_per_9", label: "BB/9", fmt: "f2" },
  { key: "k_bb_ratio", label: "K/BB", fmt: "f2" },
];

function getCols(type, view) {
  if (type === "batter") return view === "saber" ? BATTER_SABER : BATTER_CLASSIC;
  return view === "saber" ? PITCHER_SABER : PITCHER_CLASSIC;
}

// ── 포맷터 ───────────────────────────────────────────────

function fmt(value, format) {
  if (value === null || value === undefined) return "-";
  switch (format) {
    case "avg3": return value.toFixed(3).replace(/^0/, "");
    case "f1": return value.toFixed(1);
    case "f2": return value.toFixed(2);
    case "pct1": return value.toFixed(1) + "%";
    default: return String(value);
  }
}

// ── 컴포넌트 ─────────────────────────────────────────────

export default function RecordsTable({ players, type, view, sort, order, onSort }) {
  const cols = getCols(type, view);

  function SortIcon({ col }) {
    const sortKey = col.sortKey ?? col.key;
    if (sortKey !== sort) return <span className="rt-sort-icon">↕</span>;
    return <span className="rt-sort-icon active">{order === "desc" ? "↓" : "↑"}</span>;
  }

  return (
    <div className="records-table-wrap">
      <table className="records-table">
        <thead>
          <tr>
            <th className="rt-rank">순위</th>
            <th className="rt-name rt-left">선수</th>
            <th className="rt-team rt-left">팀</th>
            <th className="rt-pos">포지션</th>
            {cols.map((col) => (
              <th
                key={col.key}
                className={`rt-stat${(col.sortKey ?? col.key) === sort ? " rt-sorted" : ""}`}
                onClick={() => onSort(col.sortKey ?? col.key)}
              >
                {col.label}
                <SortIcon col={col} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p) => {
            const teamColor = TEAM_COLORS[p.team] ?? "#718096";
            return (
              <tr key={p.player_id}>
                <td className="rt-rank">{p.rank}</td>
                <td className="rt-name rt-left">
                  <Link to={`/players/${p.player_id}`} className="rt-player-link">
                    {p.player_name}
                  </Link>
                </td>
                <td className="rt-team rt-left">
                  <span className="rt-team-badge" style={{ color: teamColor }}>
                    {p.team}
                  </span>
                </td>
                <td className="rt-pos">{p.position}</td>
                {cols.map((col) => (
                  <td
                    key={col.key}
                    className={`rt-stat${(col.sortKey ?? col.key) === sort ? " rt-sorted" : ""}`}
                  >
                    {fmt(p[col.key], col.fmt)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
