import { useState, useEffect, useCallback } from "react";
import { API_BASE, CURRENT_SEASON } from "../utils/constants";

const DEFAULT_PARAMS = {
  target: "batter",
  condition: "all",
  stat: "avg",
  sort: "desc",
  limit: "10",
  season: String(CURRENT_SEASON),
};

export function useExplorer() {
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchResults = useCallback((p) => {
    setLoading(true);
    setError(null);
    const qs = new URLSearchParams(p).toString();
    let cancelled = false;

    fetch(`${API_BASE}/explorer?${qs}`)
      .then((r) => {
        if (!r.ok) return r.json().then((e) => Promise.reject(e.detail || "오류가 발생했습니다."));
        return r.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(typeof err === "string" ? err : "데이터를 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const cancel = fetchResults(params);
    return cancel;
  }, [params, fetchResults]);

  const setParam = useCallback((key, value) => {
    setParams((prev) => {
      const next = { ...prev, [key]: value };
      // target 변경 시 stat을 해당 타겟의 첫 번째 stat으로 초기화
      if (key === "target") {
        next.stat = ""; // options 로드 후 useExplorerOptions가 처리
      }
      return next;
    });
  }, []);

  return { params, setParam, data, loading, error };
}

export function useExplorerOptions(target) {
  const [options, setOptions] = useState({ stats: [], conditions: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!target) return;
    setLoading(true);
    let cancelled = false;

    fetch(`${API_BASE}/explorer/options?target=${target}`)
      .then((r) => r.json())
      .then((json) => {
        if (!cancelled) setOptions(json);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [target]);

  return { options, loading };
}
