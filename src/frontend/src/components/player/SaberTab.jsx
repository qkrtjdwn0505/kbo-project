import { formatStat } from "../../utils/formatStat";
import { STAT_TOOLTIPS } from "../../utils/constants";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import SaberDisclaimer from "../common/SaberDisclaimer";
import "./StatGrid.css";
import "./SplitsTab.css";

function TooltipCell({ label, statKey, value }) {
  const formatted = formatStat(statKey, value);
  const tip = STAT_TOOLTIPS[statKey] ?? STAT_TOOLTIPS[statKey + "_p"] ?? null;

  return (
    <div className={`stat-cell-with-tip${tip ? "" : ""}`}>
      <div className={`stat-cell stat-cell--large${tip ? " stat-cell--tip" : ""}`}>
        <span className="stat-cell-value">{formatted}</span>
        <span className="stat-cell-label">{label}</span>
      </div>
      {tip && <span className="tip-text">{tip}</span>}
    </div>
  );
}

function BatterSaber({ stats }) {
  return (
    <div className="stat-grid-section">
      <div className="stat-row stat-row--ratio">
        <TooltipCell label="wOBA"   statKey="woba"     value={stats.woba} />
        <TooltipCell label="wRC+"   statKey="wrc_plus" value={stats.wrc_plus} />
        <TooltipCell label="WAR"    statKey="war"      value={stats.war} />
        <TooltipCell label="BABIP"  statKey="babip"    value={stats.babip} />
      </div>
      <div className="stat-row stat-row--ratio">
        <TooltipCell label="ISO"    statKey="iso"      value={stats.iso} />
        <TooltipCell label="BB%"    statKey="bb_pct"   value={stats.bb_pct} />
        <TooltipCell label="K%"     statKey="k_pct"    value={stats.k_pct} />
      </div>
    </div>
  );
}

function PitcherSaber({ stats }) {
  return (
    <div className="stat-grid-section">
      <div className="stat-row stat-row--ratio">
        <TooltipCell label="FIP"    statKey="fip"      value={stats.fip} />
        <TooltipCell label="xFIP"   statKey="xfip"     value={stats.xfip} />
        <TooltipCell label="WAR"    statKey="war"      value={stats.war} />
        <TooltipCell label="BABIP"  statKey="babip"    value={stats.babip} />
      </div>
      <div className="stat-row stat-row--ratio">
        <TooltipCell label="K/9"    statKey="k_per_9"   value={stats.k_per_9} />
        <TooltipCell label="BB/9"   statKey="bb_per_9"  value={stats.bb_per_9} />
        <TooltipCell label="HR/9"   statKey="hr_per_9"  value={stats.hr_per_9} />
        <TooltipCell label="K/BB"   statKey="k_bb_ratio" value={stats.k_bb_ratio} />
      </div>
      <div className="stat-row stat-row--ratio">
        <TooltipCell label="LOB%"   statKey="lob_pct"  value={stats.lob_pct} />
      </div>
    </div>
  );
}

export default function SaberTab({ data, loading, error }) {
  if (loading) return <LoadingSpinner />;
  if (error)   return <ErrorMessage error={{ message: error }} />;
  if (!data)   return null;

  const { player_type, stats } = data;

  return (
    <div className="saber-tab">
      <div className="tab-season-badge">{stats.season}시즌</div>
      <SaberDisclaimer />
      <p className="saber-hint">지표 위에 마우스를 올리면 설명이 표시됩니다.</p>
      {player_type === "batter"
        ? <BatterSaber stats={stats} />
        : <PitcherSaber stats={stats} />
      }
    </div>
  );
}
