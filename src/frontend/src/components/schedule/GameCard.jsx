import { TEAM_COLORS } from "../../utils/constants";
import "./GameCard.css";

function TeamScore({ name, score, isWinner }) {
  const color = TEAM_COLORS[name] ?? "#1a365d";
  return (
    <div className={`team-score${isWinner ? " team-score--winner" : ""}`}>
      <span className="team-badge" style={{ borderColor: color, color }}>
        {name}
      </span>
      <span className="score-num">{score ?? "-"}</span>
    </div>
  );
}

export default function GameCard({ game, onClick }) {
  const homeWin = (game.home_score ?? 0) > (game.away_score ?? 0);
  const awayWin = (game.away_score ?? 0) > (game.home_score ?? 0);
  const isFinal = game.status === "final";

  return (
    <div className="game-card card" onClick={() => onClick?.(game.id)}>
      <div className="game-card-body">
        <TeamScore name={game.away_team.short_name} score={game.away_score} isWinner={awayWin && isFinal} />
        <div className="vs-area">
          <span className="vs-colon">:</span>
          <span className={`game-status ${isFinal ? "status-final" : "status-scheduled"}`}>
            {isFinal ? "종료" : game.time ?? "예정"}
          </span>
        </div>
        <TeamScore name={game.home_team.short_name} score={game.home_score} isWinner={homeWin && isFinal} />
      </div>
      {isFinal && (game.winning_pitcher || game.losing_pitcher) && (
        <div className="game-card-pitchers">
          {game.winning_pitcher && <span className="pitcher-win">승 {game.winning_pitcher}</span>}
          {game.losing_pitcher  && <span className="pitcher-lose">패 {game.losing_pitcher}</span>}
        </div>
      )}
      {game.stadium && (
        <div className="game-card-meta">{game.stadium}</div>
      )}
    </div>
  );
}
