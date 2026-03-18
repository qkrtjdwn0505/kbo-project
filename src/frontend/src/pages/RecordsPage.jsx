import { useState, useEffect } from "react";
import { useSeasons } from "../hooks/useSeasons";
import { useRecords } from "../hooks/useRecords";
import RecordsFilter from "../components/records/RecordsFilter";
import RecordsTable from "../components/records/RecordsTable";
import Pagination from "../components/records/Pagination";
import LoadingSpinner from "../components/common/LoadingSpinner";
import SaberDisclaimer from "../components/common/SaberDisclaimer";
import "./RecordsPage.css";

const DEFAULT_PARAMS = {
  type: "batter",
  season: 2025,
  team: "",
  sort: "war",
  order: "desc",
  page: 1,
  per_page: 20,
  min_pa: 30,
  min_ip: 10,
  view: "classic",
};

export default function RecordsPage() {
  const { seasons, currentSeason } = useSeasons();
  const [params, setParams] = useState(DEFAULT_PARAMS);

  useEffect(() => {
    if (currentSeason && params.season !== currentSeason) {
      setParams((p) => ({ ...p, season: currentSeason }));
    }
  }, [currentSeason]); // eslint-disable-line react-hooks/exhaustive-deps

  function setParam(key, value) {
    setParams((p) => ({
      ...p,
      [key]: value,
      // 뷰 전환은 페이지 리셋 없이, 나머지 필터 변경 시 1페이지로
      ...(key !== "page" && key !== "view" ? { page: 1 } : {}),
    }));
  }

  function handleSort(col) {
    setParams((p) => ({
      ...p,
      sort: col,
      order: p.sort === col && p.order === "desc" ? "asc" : "desc",
      page: 1,
    }));
  }

  const { data, loading } = useRecords(params);
  const players = data?.players ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="records-page">
      <h1>기록 조회</h1>

      <div className="card records-filter-card">
        <RecordsFilter params={params} setParam={setParam} seasons={seasons} />
      </div>

      {loading && (
        <div className="records-loading">
          <LoadingSpinner />
        </div>
      )}

      {!loading && data && (
        <>
          <div className="records-meta">
            <span className="records-total">
              {total}명 ({data.season}시즌)
            </span>
          </div>

          {params.view === "saber" && <SaberDisclaimer />}
          <div className="card mt-4">
            <RecordsTable
              players={players}
              type={params.type}
              view={params.view}
              sort={params.sort}
              order={params.order}
              onSort={handleSort}
            />
          </div>

          <Pagination
            page={params.page}
            total={total}
            perPage={params.per_page}
            onChange={(p) => setParam("page", p)}
          />
        </>
      )}
    </div>
  );
}
