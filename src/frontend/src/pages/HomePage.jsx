import { Link } from "react-router-dom";
import { useStandings } from "../hooks/useStandings";
import { CURRENT_SEASON } from "../utils/constants";
import TeamRankTable from "../components/standings/TeamRankTable";
import PlayerRankings from "../components/standings/PlayerRankings";
import "./HomePage.css";

const MINI_RANKING_STATS = [
  { stat: "avg",  label: "타율" },
  { stat: "hr",   label: "홈런" },
  { stat: "era",  label: "ERA"  },
];

export default function HomePage() {
  const { data: standingsData, loading: standingsLoading, error: standingsError } =
    useStandings(CURRENT_SEASON);
  const standings = standingsData?.standings ?? [];

  return (
    <div className="home-page">
      {/* 히어로 */}
      <section className="hero-section">
        <div className="hero-inner">
          <h1 className="hero-title">⚾ KBO 데이터 대시보드</h1>
          <p className="hero-sub">
            네이버가 못 하는 복합 조건 질의를 드롭다운으로.
            <br />
            세이버메트릭스 · 스플릿 · 핫&콜드 한 곳에서.
          </p>
          <div className="hero-actions">
            <Link to="/explorer" className="btn btn-hero-primary">
              탐색기 시작하기 →
            </Link>
            <Link to="/standings" className="btn btn-hero-secondary">
              순위 보기 →
            </Link>
          </div>
        </div>
      </section>

      {/* 팀 순위 미니 */}
      <section className="card mt-8">
        <div className="section-header">
          <h2 className="section-title-sm">팀 순위</h2>
          <Link to="/standings" className="section-link">전체 보기 →</Link>
        </div>
        <TeamRankTable
          standings={standings}
          loading={standingsLoading}
          error={standingsError}
          limit={5}
          showViewAll={false}
        />
      </section>

      {/* 선수 랭킹 미니 */}
      <section className="mt-8">
        <div className="section-header">
          <h2 className="section-title-sm">주요 지표 TOP3</h2>
          <Link to="/standings" className="section-link">더보기 →</Link>
        </div>
        <PlayerRankings limit={3} season={CURRENT_SEASON} stats={MINI_RANKING_STATS} />
      </section>
    </div>
  );
}
