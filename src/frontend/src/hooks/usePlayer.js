import { useState, useEffect } from "react";
import { API_BASE, CURRENT_SEASON } from "../utils/constants";

function useFetch(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!url) return;
    setLoading(true);
    setError(null);
    let cancelled = false;

    fetch(url)
      .then((r) => {
        if (!r.ok) return r.json().then((e) => Promise.reject(e.detail || "오류가 발생했습니다."));
        return r.json();
      })
      .then((json) => { if (!cancelled) setData(json); })
      .catch((err) => { if (!cancelled) setError(typeof err === "string" ? err : "데이터를 불러오지 못했습니다."); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [url]);

  return { data, loading, error };
}

export function usePlayerProfile(playerId) {
  return useFetch(playerId ? `${API_BASE}/players/${playerId}` : null);
}

export function usePlayerClassic(playerId, season = CURRENT_SEASON) {
  return useFetch(playerId && season != null ? `${API_BASE}/players/${playerId}/classic?season=${season}` : null);
}

export function usePlayerSaber(playerId, season = CURRENT_SEASON) {
  return useFetch(playerId && season != null ? `${API_BASE}/players/${playerId}/sabermetrics?season=${season}` : null);
}

export function usePlayerSplits(playerId, season = CURRENT_SEASON) {
  return useFetch(playerId && season != null ? `${API_BASE}/players/${playerId}/splits?season=${season}` : null);
}

// 검색 훅 — query는 이미 디바운스된 값을 받음
export function usePlayerSearch(debouncedQuery) {
  const url =
    debouncedQuery && debouncedQuery.length >= 2
      ? `${API_BASE}/players/search?q=${encodeURIComponent(debouncedQuery)}`
      : null;

  const { data, loading } = useFetch(url);
  return { results: data?.results ?? [], loading };
}
