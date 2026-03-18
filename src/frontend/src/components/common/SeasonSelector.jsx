import "./SeasonSelector.css";

export default function SeasonSelector({ season, setSeason, seasons }) {
  if (!seasons || seasons.length <= 1) return null;
  return (
    <select
      className="season-selector"
      value={season}
      onChange={(e) => setSeason(Number(e.target.value))}
    >
      {seasons.map((s) => (
        <option key={s} value={s}>
          {s}시즌
        </option>
      ))}
    </select>
  );
}
