import { useGameDetail } from "../../hooks/useSchedule";
import { TEAM_COLORS } from "../../utils/constants";
import LoadingSpinner from "../common/LoadingSpinner";
import "./GameDetail.css";

function PitcherLine({ label, pitcher }) {
  if (!pitcher) return null;
  return (
    <div className="pitcher-line">
      <span className="pd-label">{label}</span>
      <span className="pd-name">{pitcher.name}</span>
      <span className="pd-team">{pitcher.team}</span>
      <span className="pd-stat">{pitcher.ip}이닝 {pitcher.er}실점 {pitcher.so}삼진</span>
    </div>
  );
}

export default function GameDetail({ gameId, onClose }) {
  const { detail, loading } = useGameDetail(gameId);

  if (loading) return (
    <div className="game-detail-overlay" onClick={onClose}>
      <div className="game-detail-panel" onClick={(e) => e.stopPropagation()}>
        <LoadingSpinner />
      </div>
    </div>
  );

  if (!detail) return null;
  const { game, top_batters, winning_pitcher, losing_pitcher, save_pitcher } = detail;
  const homeColor = TEAM_COLORS[game.home_team.short_name] ?? "#1a365d";
  const awayColor = TEAM_COLORS[game.away_team.short_name] ?? "#718096";

  return (
    <div className="game-detail-overlay" onClick={onClose}>
      <div className="game-detail-panel" onClick={(e) => e.stopPropagation()}>
        <button className="gd-close" onClick={onClose}>✕</button>

        {/* 스코어 헤더 */}
        <div className="gd-scoreline">
          <div className="gd-team" style={{ color: awayColor }}>
            {game.away_team.short_name}
            <span className="gd-score">{game.away_score}</span>
          </div>
          <div className="gd-sep">:</div>
          <div className="gd-team" style={{ color: homeColor }}>
            <span className="gd-score">{game.home_score}</span>
            {game.home_team.short_name}
          </div>
        </div>
        <div className="gd-meta">{game.date} · {game.stadium}</div>

        {/* 투수 */}
        {(winning_pitcher || losing_pitcher) && (
          <div className="gd-section">
            <h4 className="gd-section-title">투수</h4>
            <PitcherLine label="승" pitcher={winning_pitcher} />
            <PitcherLine label="패" pitcher={losing_pitcher} />
            <PitcherLine label="세" pitcher={save_pitcher} />
          </div>
        )}

        {/* 주요 타자 */}
        {top_batters.length > 0 && (
          <div className="gd-section">
            <h4 className="gd-section-title">주요 타자</h4>
            <table className="gd-batter-table">
              <thead>
                <tr>
                  <th>선수</th><th>팀</th><th>타수</th><th>안타</th><th>홈런</th><th>타점</th>
                </tr>
              </thead>
              <tbody>
                {top_batters.map((b) => (
                  <tr key={b.player_id}>
                    <td>{b.name}</td>
                    <td>{b.team}</td>
                    <td>{b.ab}</td>
                    <td>{b.hits}</td>
                    <td>{b.hr || "-"}</td>
                    <td>{b.rbi}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
