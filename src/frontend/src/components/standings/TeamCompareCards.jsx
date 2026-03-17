import { formatStat } from "../../utils/formatStat";
import { TEAM_COLORS } from "../../utils/constants";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import "./TeamCompareCards.css";

function formatCardValue(statName, value) {
  // "team_ops" → "ops" etc.
  const key = statName.replace("team_", "");
  return formatStat(key, value);
}

function CompareCard({ card }) {
  const leaderColor = TEAM_COLORS[card.leader_team] ?? "var(--color-primary)";

  return (
    <div className="compare-card card">
      <h3 className="compare-card-title">{card.category}</h3>
      {/* 1위 강조 */}
      <div className="compare-leader" style={{ borderLeftColor: leaderColor }}>
        <span className="compare-leader-team" style={{ color: leaderColor }}>
          {card.leader_team}
        </span>
        <span className="compare-leader-value">
          {formatCardValue(card.stat_name, card.leader_value)}
        </span>
      </div>
      {/* 2위~ */}
      <ol className="compare-list">
        {card.rankings.slice(1).map((item) => (
          <li key={item.team_id} className="compare-list-item">
            <span className="compare-list-rank">{item.rank}.</span>
            <span className="compare-list-team">{item.team_name}</span>
            <span className="compare-list-value">
              {formatCardValue(card.stat_name, item.value)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function TeamCompareCards({ cards = [], loading, error }) {
  if (loading) return <LoadingSpinner />;
  if (error)   return <ErrorMessage error={{ message: error }} />;
  if (!cards.length) return null;

  return (
    <div className="compare-cards-grid">
      {cards.map((card) => (
        <CompareCard key={card.category} card={card} />
      ))}
    </div>
  );
}
