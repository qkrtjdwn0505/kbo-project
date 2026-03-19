import { useGameDates, useSchedule, useLiveScores } from "../hooks/useSchedule";
import MiniCalendar from "../components/schedule/MiniCalendar";
import GameCard from "../components/schedule/GameCard";
import GameDetail from "../components/schedule/GameDetail";
import LoadingSpinner from "../components/common/LoadingSpinner";
import { useState, useEffect, useMemo } from "react";
import "./SchedulePage.css";

function formatDateKo(dateStr) {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-");
  return `${y}.${m}.${d}`;
}

function todayStr() {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

export default function SchedulePage() {
  const today = todayStr();
  const initialMonth = today.slice(0, 7);
  const [viewMonth, setViewMonth] = useState(initialMonth);
  const [selectedDate, setSelectedDate] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  const { dates: gameDates, loading: datesLoading } = useGameDates(viewMonth);
  const { games, loading: gamesLoading } = useSchedule(selectedDate);
  const { liveData, liveBoxScores } = useLiveScores(selectedDate, games);

  // SSE 데이터로 경기 목록 머지
  const mergedGames = useMemo(() => {
    if (!liveData) return games;
    return games.map((game) => {
      // game_id를 KBO 형식으로 매칭하기 위해 liveData를 팀명으로 검색
      const live = Object.values(liveData).find(
        (l) =>
          l.home_team === game.home_team?.short_name &&
          l.away_team === game.away_team?.short_name
      );
      if (!live) return game;
      const statusMap = { "1": "scheduled", "2": "in_progress", "3": "final" };
      return {
        ...game,
        home_score: live.home_score,
        away_score: live.away_score,
        status: statusMap[live.status_code] || game.status,
        live_inning: live.inning,
        live_inning_half: live.inning_half,
      };
    });
  }, [games, liveData]);

  // 오늘 달의 경기 날짜 목록 로드 완료 시, 오늘 경기가 있으면 자동 선택
  useEffect(() => {
    if (!datesLoading && viewMonth === today.slice(0, 7) && selectedDate === null) {
      if (gameDates.includes(today)) {
        setSelectedDate(today);
      }
    }
  }, [gameDates, datesLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  // 월 이동: 날짜 초기화 (games는 useSchedule에서 자동 비워짐)
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
            viewMonth={viewMonth}
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

          {/* gameDates 로딩 중 */}
          {datesLoading && <LoadingSpinner />}

          {/* 이 달에 경기 없음 */}
          {noGamesThisMonth && (
            <p className="games-empty">이 달에는 경기가 없습니다.</p>
          )}

          {/* 날짜 미선택 */}
          {!datesLoading && !noGamesThisMonth && !selectedDate && (
            <p className="games-empty">날짜를 선택하세요.</p>
          )}

          {/* 경기 로딩 중 */}
          {!datesLoading && gamesLoading && <LoadingSpinner />}

          {/* 선택 날짜에 경기 없음 */}
          {!datesLoading && !gamesLoading && selectedDate && mergedGames.length === 0 && (
            <p className="games-empty">해당 날짜에 경기가 없습니다.</p>
          )}

          {/* 경기 목록 */}
          {!gamesLoading && mergedGames.length > 0 && (
            <div className="games-list">
              {mergedGames.map((game) => (
                <GameCard key={game.id} game={game} onClick={setActiveGameId} />
              ))}
            </div>
          )}
        </section>
      </div>

      {activeGameId && (
        <GameDetail
          gameId={activeGameId}
          onClose={() => setActiveGameId(null)}
          liveBoxScores={liveBoxScores}
          mergedGames={mergedGames}
        />
      )}
    </div>
  );
}
