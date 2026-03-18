import { Link } from "react-router-dom";

export default function PitcherLineup({ pitchers, teamName }) {
  return (
    <div>
      <div className="lineup-section-title">{teamName} 투수</div>
      <table className="lineup-table">
        <thead>
          <tr>
            <th className="lt-left">선수</th>
            <th>이닝</th>
            <th>피안타</th>
            <th>자책</th>
            <th>볼넷</th>
            <th>삼진</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {pitchers.map((p, i) => (
            <tr key={`${p.player_id}-${i}`} className={p.decision ? "lt-highlight" : ""}>
              <td className="lt-left">
                <Link to={`/players/${p.player_id}`} className="lt-player-link">
                  {p.player_name}
                  {p.is_starter && <span className="lt-starter-badge">선</span>}
                </Link>
              </td>
              <td>{p.ip}</td>
              <td>{p.hits_allowed}</td>
              <td>{p.er}</td>
              <td>{p.bb_allowed}</td>
              <td>{p.so_count}</td>
              <td>
                {p.decision && (
                  <span className={`lt-decision lt-dec-${p.decision}`}>{p.decision}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
