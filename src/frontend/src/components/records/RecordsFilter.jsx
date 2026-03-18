import { TEAM_NAMES } from "../../utils/constants";
import SeasonSelector from "../common/SeasonSelector";
import "./RecordsFilter.css";

const TEAM_OPTIONS = [
  { value: "", label: "전체팀" },
  ...Object.entries(TEAM_NAMES).map(([id, name]) => ({ value: id, label: name })),
];

const DEFAULT_SORTS = {
  batter: "war",
  pitcher: "war",
};

export default function RecordsFilter({ params, setParam, seasons }) {
  function handleTypeChange(type) {
    setParam("type", type);
    setParam("sort", DEFAULT_SORTS[type]);
  }

  return (
    <div className="records-filter">
      {/* 타자/투수 토글 */}
      <div className="rf-toggle">
        <button
          className={`rf-btn${params.type === "batter" ? " active" : ""}`}
          onClick={() => handleTypeChange("batter")}
        >
          타자
        </button>
        <button
          className={`rf-btn${params.type === "pitcher" ? " active" : ""}`}
          onClick={() => handleTypeChange("pitcher")}
        >
          투수
        </button>
      </div>

      {/* 팀 필터 */}
      <select
        className="rf-select"
        value={params.team}
        onChange={(e) => setParam("team", e.target.value)}
      >
        {TEAM_OPTIONS.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>

      {/* 클래식/세이버 토글 */}
      <div className="rf-toggle">
        <button
          className={`rf-btn${params.view === "classic" ? " active" : ""}`}
          onClick={() => setParam("view", "classic")}
        >
          클래식
        </button>
        <button
          className={`rf-btn${params.view === "saber" ? " active" : ""}`}
          onClick={() => setParam("view", "saber")}
        >
          세이버
        </button>
      </div>

      {/* 최소 타석/이닝 */}
      <label className="rf-min-label">
        최소 {params.type === "batter" ? "타석" : "이닝"}
        <input
          type="number"
          className="rf-min-input"
          min={0}
          value={params.type === "batter" ? params.min_pa : params.min_ip}
          onChange={(e) => {
            const key = params.type === "batter" ? "min_pa" : "min_ip";
            setParam(key, Number(e.target.value));
          }}
        />
      </label>

      {/* 시즌 선택 */}
      <SeasonSelector
        season={params.season}
        setSeason={(s) => setParam("season", s)}
        seasons={seasons}
      />
    </div>
  );
}
