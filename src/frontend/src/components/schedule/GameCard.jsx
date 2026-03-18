import { TEAM_COLORS } from "../../utils/constants";
import "./GameCard.css";

function TeamName({ name, align }) {
  const color = TEAM_COLORS[name] ?? "#1a365d";
  return (
    <div className={`gc-team gc-team--${align}`}>
      <span
        className="gc-team-name"
        style={{ borderColor: color, color }}
      >
        {name}
      </span>
    </div>
  );
}

export default function GameCard({ game, onClick }) {
  const isFinal      = game.status === "final";
  const isInProgress = game.status === "in_progress";
  const homeWin = isFinal && (game.home_score ?? 0) > (game.away_score ?? 0);
  const awayWin = isFinal && (game.away_score ?? 0) > (game.home_score ?? 0);

  return (
    <div className="game-card card" onClick={() => onClick?.(game.id)}>
      <div className="game-card-body">
        {/* 원정팀 */}
        <TeamName name={game.away_team.short_name} align="away" />

        {/* 중앙: 스코어 또는 시간 */}
        <div className="gc-center">
          {(isFinal || isInProgress) ? (
            <>
              <div className="gc-score">
                <span className={`gc-score-num${awayWin ? " gc-score-win" : ""}`}>
                  {game.away_score ?? 0}
                </span>
                <span className="gc-score-sep">:</span>
                <span className={`gc-score-num${homeWin ? " gc-score-win" : ""}`}>
                  {game.home_score ?? 0}
                </span>
              </div>
              <span className={`gc-badge${isInProgress ? " gc-badge--live" : " gc-badge--final"}`}>
                {isInProgress ? "진행중" : "종료"}
              </span>
            </>
          ) : (
            <span className="gc-time">{game.time ?? "예정"}</span>
          )}
        </div>

        {/* 홈팀 */}
        <TeamName name={game.home_team.short_name} align="home" />
      </div>

      {/* 승/패 투수 (종료 경기) */}
      {isFinal && (game.winning_pitcher || game.losing_pitcher) && (
        <div className="game-card-pitchers">
          {game.winning_pitcher && <span className="pitcher-win">승 {game.winning_pitcher}</span>}
          {game.losing_pitcher  && <span className="pitcher-lose">패 {game.losing_pitcher}</span>}
        </div>
      )}

      {/* 구장 */}
      {game.stadium && (
        <div className="game-card-meta">{game.stadium}</div>
      )}
    </div>
  );
}
