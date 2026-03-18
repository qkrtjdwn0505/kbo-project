import { useState, useEffect } from "react";
import "./MiniCalendar.css";

const DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function pad(n) { return String(n).padStart(2, "0"); }

function parseYearMonth(ym) {
  if (!ym) return null;
  const [y, m] = ym.split("-").map(Number);
  return { year: y, month: m - 1 }; // month: 0-based
}

export default function MiniCalendar({ viewMonth, selectedDate, onSelect, gameDates = [], onMonthChange }) {
  const initial = parseYearMonth(viewMonth) ?? (() => {
    const t = new Date();
    return { year: t.getFullYear(), month: t.getMonth() };
  })();

  const [year, setYear] = useState(initial.year);
  const [month, setMonth] = useState(initial.month);

  // viewMonth prop이 바뀌면 (◀▶ 또는 외부 제어) 캘린더 표시 월 동기화
  useEffect(() => {
    const parsed = parseYearMonth(viewMonth);
    if (parsed) {
      setYear(parsed.year);
      setMonth(parsed.month);
    }
  }, [viewMonth]);

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

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const monthStr = `${year}-${pad(month + 1)}`;

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

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
                hasGame ? "has-game" : "no-game",
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
