import { useStandings, useTeamComparison } from "../hooks/useStandings";
import { CURRENT_SEASON } from "../utils/constants";
import TeamRankTable from "../components/standings/TeamRankTable";
import TeamCompareCards from "../components/standings/TeamCompareCards";
import PlayerRankings from "../components/standings/PlayerRankings";
import "./StandingsPage.css";

export default function StandingsPage() {
  const { data: standingsData, loading: standingsLoading, error: standingsError } =
    useStandings(CURRENT_SEASON);
  const { data: compareData, loading: compareLoading, error: compareError } =
    useTeamComparison(CURRENT_SEASON);

  const standings = standingsData?.standings ?? [];
  const cards     = compareData?.cards ?? [];

  return (
    <div className="standings-page">
      <h1>팀 순위</h1>

      {/* 순위 테이블 */}
      <section className="card">
        <h2 className="section-title">{CURRENT_SEASON}시즌 순위표</h2>
        <TeamRankTable
          standings={standings}
          loading={standingsLoading}
          error={standingsError}
        />
      </section>

      {/* 팀스탯 비교 */}
      <section className="mt-8">
        <h2 className="section-title">팀스탯 비교</h2>
        <TeamCompareCards
          cards={cards}
          loading={compareLoading}
          error={compareError}
        />
      </section>

      {/* 선수 TOP5 랭킹 */}
      <section className="mt-8">
        <h2 className="section-title">주요 지표 TOP5</h2>
        <PlayerRankings limit={5} season={CURRENT_SEASON} />
      </section>
    </div>
  );
}
