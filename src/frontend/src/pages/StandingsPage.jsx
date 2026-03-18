import { useState, useEffect } from "react";
import { useStandings, useTeamComparison } from "../hooks/useStandings";
import { useSeasons } from "../hooks/useSeasons";
import TeamRankTable from "../components/standings/TeamRankTable";
import TeamCompareCards from "../components/standings/TeamCompareCards";
import PlayerRankings from "../components/standings/PlayerRankings";
import SeasonSelector from "../components/common/SeasonSelector";
import "./StandingsPage.css";

export default function StandingsPage() {
  const { seasons, currentSeason } = useSeasons();
  const [season, setSeason] = useState(null);

  // 시즌 목록 로드 후 초기값 설정
  useEffect(() => {
    if (currentSeason && season === null) setSeason(currentSeason);
  }, [currentSeason, season]);

  const activeSeason = season ?? currentSeason;

  const { data: standingsData, loading: standingsLoading, error: standingsError } =
    useStandings(activeSeason);
  const { data: compareData, loading: compareLoading, error: compareError } =
    useTeamComparison(activeSeason);

  const standings = standingsData?.standings ?? [];
  const cards     = compareData?.cards ?? [];

  return (
    <div className="standings-page">
      <div className="standings-header">
        <h1>팀 순위</h1>
        <SeasonSelector season={activeSeason} setSeason={setSeason} seasons={seasons} />
      </div>

      {/* 순위 테이블 */}
      <section className="card">
        <h2 className="section-title">{activeSeason}시즌 순위표</h2>
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
        <PlayerRankings limit={5} season={activeSeason} />
      </section>
    </div>
  );
}
