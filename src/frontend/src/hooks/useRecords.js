import { useState, useEffect } from "react";
import { API_BASE } from "../utils/constants";

export function useRecords(params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const qs = new URLSearchParams();
    qs.set("type", params.type);
    if (params.season) qs.set("season", params.season);
    if (params.team) qs.set("team", params.team);
    qs.set("sort", params.sort);
    qs.set("order", params.order);
    qs.set("page", params.page);
    qs.set("per_page", params.per_page);
    if (params.type === "batter") qs.set("min_pa", params.min_pa);
    else qs.set("min_ip", params.min_ip);

    setLoading(true);
    fetch(`${API_BASE}/players/records?${qs}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [
    params.type, params.season, params.team,
    params.sort, params.order, params.page, params.per_page,
    params.min_pa, params.min_ip,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading };
}
