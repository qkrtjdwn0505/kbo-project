import { useEffect } from "react";
import { useExplorer, useExplorerOptions } from "../hooks/useExplorer";
import DropdownBar from "../components/explorer/DropdownBar";
import ResultTable from "../components/explorer/ResultTable";
import ResultChart from "../components/explorer/ResultChart";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import {
  TARGET_LABELS,
  CONDITION_LABELS,
  STAT_LABELS,
} from "../utils/constants";
import "./ExplorerPage.css";

function buildQuerySummary(params) {
  const target = TARGET_LABELS[params.target] ?? params.target;
  const condition = CONDITION_LABELS[params.condition] ?? params.condition;
  const stat = STAT_LABELS[params.stat] ?? params.stat;
  const sort = params.sort === "desc" ? "높은 순" : "낮은 순";
  const limit = params.limit === "all" ? "전체" : `상위 ${params.limit}명`;
  return `${params.season}시즌 · ${target} · ${condition} · ${stat} ${sort} · ${limit}`;
}

export default function ExplorerPage() {
  const { params, setParam, data, loading, error } = useExplorer();
  const { options } = useExplorerOptions(params.target);

  // target 변경 시 stat을 해당 타겟의 첫 번째 스탯으로 초기화
  useEffect(() => {
    if (options.stats.length > 0 && !options.stats.includes(params.stat)) {
      setParam("stat", options.stats[0]);
    }
  }, [options.stats, params.stat, setParam]);

  const results = data?.results ?? [];

  return (
    <div className="explorer-page">
      <div className="explorer-header">
        <h1>탐색기</h1>
        <p className="text-secondary">
          홈/원정, vs 좌투/우투 등 복합 조건으로 선수 순위를 조회합니다.
        </p>
      </div>

      <div className="card">
        <DropdownBar
          params={params}
          setParam={setParam}
          availableStats={options.stats}
          availableConditions={options.conditions}
        />
      </div>

      <div className="query-summary mt-8">
        <span className="query-summary-label">조회 조건</span>
        <span className="query-summary-text">{buildQuerySummary(params)}</span>
      </div>

      {loading && (
        <div className="explorer-loading mt-8">
          <LoadingSpinner />
        </div>
      )}

      {error && !loading && (
        <div className="mt-8">
          <ErrorMessage error={{ message: error }} />
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className="explorer-result-meta mt-8">
            <span className="result-count">
              {results.length > 0
                ? `${results.length}명 조회됨`
                : "결과가 없습니다."}
            </span>
          </div>

          {results.length > 0 && (
            <div className="card mt-4">
              <ResultTable results={results} stat={params.stat} />
            </div>
          )}

          <ResultChart
            results={results}
            stat={params.stat}
            limit={params.limit}
          />
        </>
      )}
    </div>
  );
}
