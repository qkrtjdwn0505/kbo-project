import { useState } from "react";
import { useParams } from "react-router-dom";
import { CURRENT_SEASON } from "../utils/constants";
import {
  usePlayerProfile,
  usePlayerClassic,
  usePlayerSaber,
  usePlayerSplits,
} from "../hooks/usePlayer";
import PlayerSearch from "../components/player/PlayerSearch";
import PlayerHeader from "../components/player/PlayerHeader";
import ClassicTab from "../components/player/ClassicTab";
import SaberTab from "../components/player/SaberTab";
import SplitsTab from "../components/player/SplitsTab";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import "./PlayerPage.css";

const TABS = [
  { key: "classic",      label: "클래식" },
  { key: "sabermetrics", label: "세이버메트릭스" },
  { key: "splits",       label: "스플릿" },
];

export default function PlayerPage() {
  const { id } = useParams();
  const playerId = id ? Number(id) : null;

  const [activeTab, setActiveTab] = useState("classic");
  // 방문한 탭만 데이터 로드 (lazy)
  const [visitedTabs, setVisitedTabs] = useState(new Set(["classic"]));

  function handleTabChange(tab) {
    setActiveTab(tab);
    setVisitedTabs((prev) => new Set([...prev, tab]));
  }

  const { data: profile, loading: profileLoading, error: profileError } =
    usePlayerProfile(playerId);

  const classicData  = usePlayerClassic(visitedTabs.has("classic")      ? playerId : null, CURRENT_SEASON);
  const saberData    = usePlayerSaber(  visitedTabs.has("sabermetrics") ? playerId : null, CURRENT_SEASON);
  const splitsData   = usePlayerSplits( visitedTabs.has("splits")       ? playerId : null, CURRENT_SEASON);

  return (
    <div className="player-page">
      {/* 항상 표시되는 검색창 */}
      <div className="player-search-bar">
        <PlayerSearch placeholder="다른 선수 검색..." />
      </div>

      {profileLoading && <LoadingSpinner />}
      {profileError && !profileLoading && (
        <ErrorMessage error={{ message: profileError }} />
      )}

      {!profileLoading && profile && (
        <>
          <PlayerHeader profile={profile} />

          {/* 탭 전환 */}
          <div className="tab-bar mt-8">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`tab-btn${activeTab === tab.key ? " tab-btn--active" : ""}`}
                onClick={() => handleTabChange(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 탭 콘텐츠 */}
          <div className="tab-content card mt-4">
            {activeTab === "classic" && (
              <ClassicTab
                data={classicData.data}
                loading={classicData.loading}
                error={classicData.error}
              />
            )}
            {activeTab === "sabermetrics" && (
              <SaberTab
                data={saberData.data}
                loading={saberData.loading}
                error={saberData.error}
              />
            )}
            {activeTab === "splits" && (
              <SplitsTab
                data={splitsData.data}
                loading={splitsData.loading}
                error={splitsData.error}
              />
            )}
          </div>
        </>
      )}

      {/* id 없이 접근 시 안내 */}
      {!playerId && !profileLoading && (
        <div className="player-empty">
          <p>위 검색창에서 선수를 검색해 주세요.</p>
        </div>
      )}
    </div>
  );
}
