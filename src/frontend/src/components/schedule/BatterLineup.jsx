import { Link } from "react-router-dom";

export default function BatterLineup({ batters, teamName }) {
  const active = batters.filter((b) => b.ab > 0);
  return (
    <div>
      <div className="lineup-section-title">{teamName} 타자</div>
      <table className="lineup-table">
        <thead>
          <tr>
            <th className="lt-left">선수</th>
            <th>포지션</th>
            <th>타수</th>
            <th>안타</th>
            <th>홈런</th>
            <th>타점</th>
            <th>삼진</th>
          </tr>
        </thead>
        <tbody>
          {active.map((b, i) => (
            <tr key={`${b.player_id}-${i}`} className={b.hr > 0 ? "lt-highlight" : ""}>
              <td className="lt-left">
                <Link to={`/players/${b.player_id}`} className="lt-player-link">
                  {b.player_name}
                </Link>
              </td>
              <td>{b.position ?? "-"}</td>
              <td>{b.ab}</td>
              <td>{b.hits}</td>
              <td>{b.hr || "-"}</td>
              <td>{b.rbi}</td>
              <td>{b.so}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
