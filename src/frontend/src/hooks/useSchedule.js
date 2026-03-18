import { useState, useEffect } from "react";
import { API_BASE } from "../utils/constants";

export function useGameDates(month) {
  const [dates, setDates] = useState([]);
  useEffect(() => {
    if (!month) return;
    fetch(`${API_BASE}/games/dates?month=${month}`)
      .then((r) => r.json())
      .then((d) => setDates(d.dates ?? []))
      .catch(() => {});
  }, [month]);
  return dates;
}

export function useSchedule(date) {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!date) return;
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
