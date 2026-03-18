import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  usePlayerProfile,
  usePlayerClassic,
  usePlayerSaber,
  usePlayerSplits,
} from "../hooks/usePlayer";
import { useSeasons } from "../hooks/useSeasons";
import PlayerSearch from "../components/player/PlayerSearch";
import PlayerHeader from "../components/player/PlayerHeader";
import ClassicTab from "../components/player/ClassicTab";
import SaberTab from "../components/player/SaberTab";
import SplitsTab from "../components/player/SplitsTab";
import SeasonSelector from "../components/common/SeasonSelector";
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
  const [visitedTabs, setVisitedTabs] = useState(new Set(["classic"]));

  const { seasons, currentSeason } = useSeasons();
  const [season, setSeason] = useState(null);

  useEffect(() => {
    if (currentSeason && season === null) setSeason(currentSeason);
  }, [currentSeason, season]);

  // 시즌 변경 시 방문 탭 초기화 → 전부 재로드
  function handleSeasonChange(s) {
    setSeason(s);
    setVisitedTabs(new Set([activeTab]));
  }

  function handleTabChange(tab) {
    setActiveTab(tab);
    setVisitedTabs((prev) => new Set([...prev, tab]));
  }

  const activeSeason = season ?? currentSeason;

  const { data: profile, loading: profileLoading, error: profileError } =
    usePlayerProfile(playerId);

  const classicData  = usePlayerClassic(visitedTabs.has("classic")      ? playerId : null, activeSeason);
  const saberData    = usePlayerSaber(  visitedTabs.has("sabermetrics") ? playerId : null, activeSeason);
  const splitsData   = usePlayerSplits( visitedTabs.has("splits")       ? playerId : null, activeSeason);

  return (
    <div className="player-page">
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

          {/* 시즌 셀렉터 + 탭 전환 */}
          <div className="tab-bar mt-8">
            <div className="tab-bar-tabs">
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
            <SeasonSelector
              season={activeSeason}
              setSeason={handleSeasonChange}
              seasons={seasons}
            />
          </div>

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

      {!playerId && !profileLoading && (
        <div className="player-empty">
          <p>위 검색창에서 선수를 검색해 주세요.</p>
        </div>
      )}
    </div>
  );
}
