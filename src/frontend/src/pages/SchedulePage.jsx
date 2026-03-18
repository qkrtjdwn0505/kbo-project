import { useState, useEffect } from "react";
import { useGameDates, useSchedule } from "../hooks/useSchedule";
import MiniCalendar from "../components/schedule/MiniCalendar";
import GameCard from "../components/schedule/GameCard";
import GameDetail from "../components/schedule/GameDetail";
import LoadingSpinner from "../components/common/LoadingSpinner";
import "./SchedulePage.css";

// 가장 최근 경기 날짜 구하기 (오늘 기준, 없으면 2025-09-30)
function getLatestGameDate(dates) {
  if (!dates.length) return "2025-09-30";
  const today = new Date().toISOString().slice(0, 10);
  const past = dates.filter((d) => d <= today);
  return past.length ? past[past.length - 1] : dates[dates.length - 1];
}

function formatDateKo(dateStr) {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-");
  return `${y}.${m}.${d}`;
}

export default function SchedulePage() {
  // 초기 월: 2025-09 (최근 경기 있는 마지막 월)
  const [viewMonth, setViewMonth] = useState("2025-09");
  const [selectedDate, setSelectedDate] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  const gameDates = useGameDates(viewMonth);
  const { games, loading } = useSchedule(selectedDate);

  // gameDates가 새로 로드되면 해당 월 최근 경기일 자동 선택
  // selectedDate를 의존 배열에서 제외: selectedDate가 null로 바뀔 때 구 gameDates로
  // 이전 달 날짜가 재선택되는 문제 방지
  useEffect(() => {
    if (gameDates.length > 0) {
      setSelectedDate(getLatestGameDate(gameDates));
    }
  }, [gameDates]); // eslint-disable-line react-hooks/exhaustive-deps

  // 월 이동 시 가장 최근 날짜 자동 선택
  function handleMonthChange(month) {
    setViewMonth(month);
    setSelectedDate(null);
  }

  // MiniCalendar에 viewMonth prop 필요 → 내부에서 year/month state 관리하므로
  // selectedDate 기반으로 캘린더 포커스 이동은 MiniCalendar에서 처리

  return (
    <div className="schedule-page">
      <h1>일정 / 결과</h1>

      <div className="schedule-layout">
        {/* 왼쪽: 캘린더 */}
        <aside className="schedule-calendar">
          <MiniCalendar
            selectedDate={selectedDate}
            onSelect={setSelectedDate}
            gameDates={gameDates}
            onMonthChange={handleMonthChange}
          />
        </aside>

        {/* 오른쪽: 경기 리스트 */}
        <section className="schedule-games">
          {selectedDate && (
            <h2 className="games-date-title">{formatDateKo(selectedDate)} 경기 결과</h2>
          )}

          {loading && <LoadingSpinner />}

          {!loading && selectedDate && games.length === 0 && (
            <p className="games-empty">해당 날짜에 경기가 없습니다.</p>
          )}

          {!loading && games.length > 0 && (
            <div className="games-list">
              {games.map((game) => (
                <GameCard
                  key={game.id}
                  game={game}
                  onClick={setActiveGameId}
                />
              ))}
            </div>
          )}

          {!selectedDate && (
            <p className="games-empty">날짜를 선택하세요.</p>
          )}
        </section>
      </div>

      {activeGameId && (
        <GameDetail
          gameId={activeGameId}
          onClose={() => setActiveGameId(null)}
        />
      )}
    </div>
  );
}
