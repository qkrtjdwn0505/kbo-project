import { formatStat } from "../../utils/formatStat";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import "./StatGrid.css";

function StatCell({ label, value, statKey, large = false }) {
  const formatted = statKey === "ip_display"
    ? (value ?? "-")
    : formatStat(statKey, value);
  return (
    <div className={`stat-cell${large ? " stat-cell--large" : ""}`}>
      <span className="stat-cell-value">{formatted}</span>
      <span className="stat-cell-label">{label}</span>
    </div>
  );
}

function BatterClassic({ stats }) {
  return (
    <div className="stat-grid-section">
      <div className="stat-row">
        <StatCell label="경기" value={stats.games}   statKey="games" />
        <StatCell label="타석" value={stats.pa}      statKey="pa" />
        <StatCell label="타수" value={stats.ab}      statKey="ab" />
        <StatCell label="안타" value={stats.hits}    statKey="hits" />
        <StatCell label="2루타" value={stats.doubles} statKey="doubles" />
        <StatCell label="3루타" value={stats.triples} statKey="triples" />
        <StatCell label="홈런" value={stats.hr}      statKey="hr" />
        <StatCell label="타점" value={stats.rbi}     statKey="rbi" />
      </div>
      <div className="stat-row">
        <StatCell label="득점" value={stats.runs}    statKey="runs" />
        <StatCell label="도루" value={stats.sb}      statKey="sb" />
        <StatCell label="도실" value={stats.cs}      statKey="cs" />
        <StatCell label="볼넷" value={stats.bb}      statKey="bb" />
        <StatCell label="사구" value={stats.hbp}     statKey="hbp" />
        <StatCell label="삼진" value={stats.so}      statKey="so" />
        <StatCell label="병살" value={stats.gdp}     statKey="gdp" />
      </div>
      <div className="stat-row stat-row--ratio">
        <StatCell label="타율"   value={stats.avg}  statKey="avg"  large />
        <StatCell label="출루율" value={stats.obp}  statKey="obp"  large />
        <StatCell label="장타율" value={stats.slg}  statKey="slg"  large />
        <StatCell label="OPS"    value={stats.ops}  statKey="ops"  large />
      </div>
    </div>
  );
}

function PitcherClassic({ stats }) {
  return (
    <div className="stat-grid-section">
      <div className="stat-row">
        <StatCell label="경기"   value={stats.games}        statKey="games" />
        <StatCell label="승"     value={stats.wins}         statKey="wins" />
        <StatCell label="패"     value={stats.losses}       statKey="losses" />
        <StatCell label="세이브" value={stats.saves}        statKey="saves" />
        <StatCell label="홀드"   value={stats.holds}        statKey="holds" />
        <StatCell label="이닝"   value={stats.ip_display}   statKey="ip_display" />
        <StatCell label="피안타" value={stats.hits_allowed} statKey="hits_allowed" />
        <StatCell label="피홈런" value={stats.hr_allowed}   statKey="hr_allowed" />
      </div>
      <div className="stat-row">
        <StatCell label="볼넷"   value={stats.bb_allowed}   statKey="bb_allowed" />
        <StatCell label="탈삼진" value={stats.so_count}     statKey="so_count" />
        <StatCell label="자책점" value={stats.er}           statKey="er" />
      </div>
      <div className="stat-row stat-row--ratio">
        <StatCell label="ERA"  value={stats.era}  statKey="era"  large />
        <StatCell label="WHIP" value={stats.whip} statKey="whip" large />
      </div>
    </div>
  );
}

export default function ClassicTab({ data, loading, error }) {
  if (loading) return <LoadingSpinner />;
  if (error)   return <ErrorMessage error={{ message: error }} />;
  if (!data)   return null;

  const { player_type, stats } = data;

  return (
    <div className="classic-tab">
      <div className="tab-season-badge">{stats.season}시즌</div>
      {player_type === "batter"
        ? <BatterClassic stats={stats} />
        : <PitcherClassic stats={stats} />
      }
    </div>
  );
}
