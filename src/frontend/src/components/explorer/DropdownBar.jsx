import {
  TARGET_LABELS,
  CONDITION_LABELS,
  STAT_LABELS,
  LIMIT_OPTIONS,
  SORT_OPTIONS,
} from "../../utils/constants";
import "./DropdownBar.css";

function Select({ label, value, onChange, options }) {
  return (
    <label className="dropdown-item">
      <span className="dropdown-label">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function DropdownBar({ params, setParam, availableStats, availableConditions }) {
  const targetOptions = Object.entries(TARGET_LABELS).map(([v, l]) => ({ value: v, label: l }));

  const statOptions = availableStats.map((s) => ({
    value: s,
    label: STAT_LABELS[s] ?? s,
  }));

  const conditionOptions = availableConditions.map((c) => ({
    value: c,
    label: CONDITION_LABELS[c] ?? c,
  }));

  return (
    <div className="dropdown-bar">
      <Select
        label="대상"
        value={params.target}
        onChange={(v) => setParam("target", v)}
        options={targetOptions}
      />
      <Select
        label="조건"
        value={params.condition}
        onChange={(v) => setParam("condition", v)}
        options={conditionOptions}
      />
      <Select
        label="기준 스탯"
        value={params.stat}
        onChange={(v) => setParam("stat", v)}
        options={statOptions}
      />
      <Select
        label="정렬"
        value={params.sort}
        onChange={(v) => setParam("sort", v)}
        options={SORT_OPTIONS}
      />
      <Select
        label="표시 수"
        value={params.limit}
        onChange={(v) => setParam("limit", v)}
        options={LIMIT_OPTIONS}
      />
    </div>
  );
}
