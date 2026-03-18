import { useState, useEffect } from "react";
import { API_BASE } from "../utils/constants";

export function useSeasons() {
  const [seasons, setSeasons] = useState([]);
  const [currentSeason, setCurrentSeason] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/seasons`)
      .then((r) => r.json())
      .then((data) => {
        setSeasons(data.seasons);
        setCurrentSeason(data.current);
      })
      .catch(() => {});
  }, []);

  return { seasons, currentSeason };
}
