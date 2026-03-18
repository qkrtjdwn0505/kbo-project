import { useState } from "react";
import "./MiniCalendar.css";

const DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function pad(n) { return String(n).padStart(2, "0"); }

export default function MiniCalendar({ selectedDate, onSelect, gameDates = [], onMonthChange }) {
  const today = new Date();
  const initial = selectedDate
    ? new Date(selectedDate)
    : today;

  const [year, setYear] = useState(initial.getFullYear());
  const [month, setMonth] = useState(initial.getMonth()); // 0-based

  const dateSet = new Set(gameDates);

  function prevMonth() {
    const [ny, nm] = month === 0 ? [year - 1, 11] : [year, month - 1];
    setYear(ny); setMonth(nm);
    onMonthChange?.(`${ny}-${pad(nm + 1)}`);
  }
  function nextMonth() {
    const [ny, nm] = month === 11 ? [year + 1, 0] : [year, month + 1];
    setYear(ny); setMonth(nm);
    onMonthChange?.(`${ny}-${pad(nm + 1)}`);
  }

  // 해당 월의 날짜 계산
  const firstDay = new Date(year, month, 1).getDay();  // 0=일
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const monthStr = `${year}-${pad(month + 1)}`;

  return (
    <div className="mini-calendar">
      <div className="cal-header">
        <button className="cal-nav" onClick={prevMonth}>◀</button>
        <span className="cal-title">{year}년 {month + 1}월</span>
        <button className="cal-nav" onClick={nextMonth}>▶</button>
      </div>
      <div className="cal-grid">
        {DAY_LABELS.map((d, i) => (
          <div key={d} className={`cal-day-label${i === 0 ? " sun" : i === 6 ? " sat" : ""}`}>
            {d}
          </div>
        ))}
        {cells.map((day, idx) => {
          if (!day) return <div key={`e-${idx}`} />;
          const dateStr = `${monthStr}-${pad(day)}`;
          const hasGame = dateSet.has(dateStr);
          const isSelected = dateStr === selectedDate;
          const dow = (firstDay + day - 1) % 7;
          return (
            <div
              key={dateStr}
              className={[
                "cal-cell",
                hasGame ? "has-game" : "",
                isSelected ? "selected" : "",
                dow === 0 ? "sun" : dow === 6 ? "sat" : "",
              ].filter(Boolean).join(" ")}
              onClick={() => hasGame && onSelect(dateStr)}
            >
              <span className="cal-date">{day}</span>
              {hasGame && <span className="cal-dot" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
