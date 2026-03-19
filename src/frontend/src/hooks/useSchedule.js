import { useState, useEffect, useRef, useCallback } from "react";
import { API_BASE } from "../utils/constants";

/**
 * 실시간 스코어 SSE 훅 — 진행 중 경기가 있을 때만 연결
 * @param {string|null} selectedDate - 현재 선택된 날짜 (YYYY-MM-DD)
 * @param {Array} games - 현재 표시 중인 경기 목록
 * @returns {{ liveData: Object|null }} game_id → live score 맵
 */
export function useLiveScores(selectedDate, games) {
  const [liveData, setLiveData] = useState(null);
  const esRef = useRef(null);

  const cleanup = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => {
    // 오늘 날짜인지 확인
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

    if (selectedDate !== todayStr) {
      cleanup();
      setLiveData(null);
      return;
    }

    // 진행중(in_progress) 또는 예정(scheduled) 경기가 있는지 확인
    const hasLiveOrScheduled = games.some(
      (g) => g.status === "in_progress" || g.status === "scheduled"
    );
    if (!hasLiveOrScheduled) {
      cleanup();
      return;
    }

    // SSE 연결
    cleanup();
    const es = new EventSource(`${API_BASE}/games/live`);
    esRef.current = es;

    es.addEventListener("scores", (e) => {
      try {
        const scores = JSON.parse(e.data);
        const map = {};
        let allDone = true;
        for (const s of scores) {
          map[s.game_id] = s;
          if (s.status_code !== "3") allDone = false;
        }
        setLiveData(map);
        // 모든 경기 종료 시 SSE 닫기
        if (allDone && scores.length > 0) {
          cleanup();
        }
      } catch { /* ignore parse errors */ }
    });

    es.onerror = () => {
      // EventSource는 자동 재연결함
      console.log("SSE 연결 끊김, 재연결 시도 중...");
    };

    return cleanup;
  }, [selectedDate, games, cleanup]);

  return { liveData };
}

export function useGameDates(month) {
  const [dates, setDates] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!month) { setDates([]); return; }
    setLoading(true);
    fetch(`${API_BASE}/games/dates?month=${month}`)
      .then((r) => r.json())
      .then((d) => setDates(d.dates ?? []))
      .catch(() => setDates([]))
      .finally(() => setLoading(false));
  }, [month]);
  return { dates, loading };
}

export function useSchedule(date) {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!date) { setGames([]); return; }
    setLoading(true);
    fetch(`${API_BASE}/games/schedule?date=${date}`)
      .then((r) => r.json())
      .then((d) => setGames(d.games ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [date]);
  return { games, loading };
}

export function useGameDetail(gameId) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!gameId) { setDetail(null); return; }
    setLoading(true);
    fetch(`${API_BASE}/games/${gameId}/detail`)
      .then((r) => r.json())
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [gameId]);
  return { detail, loading };
}

export function useGameLineups(gameId) {
  const [lineup, setLineup] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!gameId) { setLineup(null); return; }
    setLoading(true);
    fetch(`${API_BASE}/games/${gameId}/lineups`)
      .then((r) => r.json())
      .then(setLineup)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [gameId]);
  return { lineup, loading };
}
