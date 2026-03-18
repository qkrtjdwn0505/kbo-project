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

export function useStandings(season = CURRENT_SEASON) {
  return useFetch(season != null ? `${API_BASE}/teams/standings?season=${season}` : null);
}

export function useTeamComparison(season = CURRENT_SEASON) {
  return useFetch(season != null ? `${API_BASE}/teams/comparison?season=${season}` : null);
}

export function useTopRankings(stat, limit = 5, season = CURRENT_SEASON) {
  return useFetch(
    stat && season != null
      ? `${API_BASE}/rankings/top?stat=${stat}&limit=${limit}&season=${season}`
      : null
  );
}
