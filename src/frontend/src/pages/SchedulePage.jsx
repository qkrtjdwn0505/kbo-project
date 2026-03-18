import { useState, useEffect } from "react";
import { useGameDates, useSchedule } from "../hooks/useSchedule";
import MiniCalendar from "../components/schedule/MiniCalendar";
import GameCard from "../components/schedule/GameCard";
import GameDetail from "../components/schedule/GameDetail";
import LoadingSpinner from "../components/common/LoadingSpinner";
import "./SchedulePage.css";

function getLatestGameDate(dates) {
  if (!dates.length) return null;
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
  const [viewMonth, setViewMonth] = useState("2025-09");
  const [selectedDate, setSelectedDate] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  const { dates: gameDates, loading: datesLoading } = useGameDates(viewMonth);
  const { games, loading: gamesLoading } = useSchedule(selectedDate);

  // gameDates가 새로 로드되면 가장 최근 경기일 자동 선택
  useEffect(() => {
    if (gameDates.length > 0) {
      setSelectedDate(getLatestGameDate(gameDates));
    }
  }, [gameDates]); // eslint-disable-line react-hooks/exhaustive-deps

  // 월 이동: 날짜 선택 초기화 (games도 useSchedule에서 자동 비워짐)
  function handleMonthChange(month) {
    setViewMonth(month);
    setSelectedDate(null);
  }

  const noGamesThisMonth = !datesLoading && gameDates.length === 0;

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
          {/* 날짜 헤더 */}
          {selectedDate && (
            <h2 className="games-date-title">{formatDateKo(selectedDate)} 경기 결과</h2>
          )}

          {/* 이 달에 경기 없음 */}
          {noGamesThisMonth && (
            <p className="games-empty">이 달에는 경기가 없습니다.</p>
          )}

          {/* gameDates 로딩 중 */}
          {datesLoading && <LoadingSpinner />}

          {/* 날짜 선택 후 경기 로딩 */}
          {!datesLoading && gamesLoading && <LoadingSpinner />}

          {/* 경기 없는 날짜 */}
          {!datesLoading && !gamesLoading && selectedDate && games.length === 0 && (
            <p className="games-empty">해당 날짜에 경기가 없습니다.</p>
          )}

          {/* 경기 목록 */}
          {!gamesLoading && games.length > 0 && (
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

          {/* 날짜 미선택 (경기 있는 달인데 아직 auto-select 전) */}
          {!datesLoading && !noGamesThisMonth && !selectedDate && (
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
