import { useGameLineups } from "../../hooks/useSchedule";
import LoadingSpinner from "../common/LoadingSpinner";
import BatterLineup from "./BatterLineup";
import PitcherLineup from "./PitcherLineup";

export default function LineupTab({ gameId }) {
  const { lineup, loading } = useGameLineups(gameId);

  if (loading) return <LoadingSpinner />;
  if (!lineup) return <p className="games-empty">라인업 정보를 불러올 수 없습니다.</p>;

  return (
    <div className="lineup-tab">
      <BatterLineup batters={lineup.away_batters} teamName={lineup.away_team.short_name} />
      <PitcherLineup pitchers={lineup.away_pitchers} teamName={lineup.away_team.short_name} />
      <BatterLineup batters={lineup.home_batters} teamName={lineup.home_team.short_name} />
      <PitcherLineup pitchers={lineup.home_pitchers} teamName={lineup.home_team.short_name} />
    </div>
  );
}
