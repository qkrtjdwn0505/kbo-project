import { useState, useEffect } from "react";

const API_BASE = "/api/v1";

export function useApi(endpoint, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // params를 문자열로 직렬화해서 의존성 배열에 넣음 (깊은 비교)
  const paramsKey = JSON.stringify(params);

  useEffect(() => {
    if (!endpoint) return;

    const url = new URL(API_BASE + endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined) url.searchParams.set(k, v);
    });

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(url)
      .then((res) => {
        if (!res.ok) return res.json().then((err) => Promise.reject(err));
        return res.json();
      })
      .then((json) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [endpoint, paramsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error };
}
