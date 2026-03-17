import { Link } from "react-router-dom";
import { formatStat } from "../../utils/formatStat";
import { useTopRankings } from "../../hooks/useStandings";
import LoadingSpinner from "../common/LoadingSpinner";
import "./PlayerRankings.css";

const RANKING_STATS = [
  { stat: "avg",      label: "타율",  type: "batter" },
  { stat: "hr",       label: "홈런",  type: "batter" },
  { stat: "rbi",      label: "타점",  type: "batter" },
  { stat: "era",      label: "ERA",   type: "pitcher" },
  { stat: "wins",     label: "승",    type: "pitcher" },
  { stat: "so_count", label: "탈삼진", type: "pitcher" },
];

function RankingCard({ stat, label, limit = 5, season }) {
  const { data, loading } = useTopRankings(stat, limit, season);
  const rankings = data?.rankings ?? [];

  return (
    <div className="ranking-card card">
      <h3 className="ranking-card-title">{label} TOP{limit}</h3>
      {loading && <LoadingSpinner message="" />}
      {!loading && rankings.length === 0 && (
        <p className="ranking-empty">데이터 없음</p>
      )}
      {!loading && rankings.length > 0 && (
        <ol className="ranking-list">
          {rankings.map((item) => (
            <li key={item.player_id} className="ranking-item">
              <span className="ranking-pos">{item.rank}.</span>
              <Link to={`/players/${item.player_id}`} className="ranking-name">
                {item.player_name}
              </Link>
              <span className="ranking-team">{item.team_name}</span>
              <span className="ranking-value">
                {formatStat(stat, item.value)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function PlayerRankings({ limit = 5, season, stats }) {
  const list = stats ?? RANKING_STATS;
  return (
    <div className="player-rankings-grid">
      {list.map(({ stat, label }) => (
        <RankingCard key={stat} stat={stat} label={label} limit={limit} season={season} />
      ))}
    </div>
  );
}
