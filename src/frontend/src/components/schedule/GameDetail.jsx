import { useState, useMemo } from "react";
import { useGameDetail } from "../../hooks/useSchedule";
import { TEAM_COLORS } from "../../utils/constants";
import LoadingSpinner from "../common/LoadingSpinner";
import LineupTab from "./LineupTab";
import "./GameDetail.css";

function PitcherLine({ label, pitcher }) {
  if (!pitcher) return null;
  return (
    <div className="pitcher-line">
      <span className="pd-label">{label}</span>
      <span className="pd-name">{pitcher.name}</span>
      <span className="pd-team">{pitcher.team}</span>
      <span className="pd-stat">{pitcher.ip}이닝 {pitcher.er}실점 {pitcher.so}삼진</span>
    </div>
  );
}

function InningScoreTable({ inningScores, summary, awayName, homeName }) {
  if (!inningScores) return null;
  const awayInnings = inningScores.away || [];
  const homeInnings = inningScores.home || [];
  const maxLen = Math.max(awayInnings.length, homeInnings.length, 9);
  const headers = Array.from({ length: maxLen }, (_, i) => i + 1);

  return (
    <div className="gd-section">
      <h4 className="gd-section-title">이닝별 점수</h4>
      <div className="gd-inning-wrap">
        <table className="gd-inning-table">
          <thead>
            <tr>
              <th className="gd-inn-team">팀</th>
              {headers.map((h) => <th key={h}>{h}</th>)}
              {summary && <>
                <th className="gd-inn-sum">R</th>
                <th className="gd-inn-sum">H</th>
                <th className="gd-inn-sum">E</th>
              </>}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="gd-inn-team">{awayName}</td>
              {headers.map((_, i) => (
                <td key={i}>{awayInnings[i] ?? ""}</td>
              ))}
              {summary && <>
                <td className="gd-inn-sum">{summary.away?.[0] ?? ""}</td>
                <td className="gd-inn-sum">{summary.away?.[1] ?? ""}</td>
                <td className="gd-inn-sum">{summary.away?.[2] ?? ""}</td>
              </>}
            </tr>
            <tr>
              <td className="gd-inn-team">{homeName}</td>
              {headers.map((_, i) => (
                <td key={i}>{homeInnings[i] ?? ""}</td>
              ))}
              {summary && <>
                <td className="gd-inn-sum">{summary.home?.[0] ?? ""}</td>
                <td className="gd-inn-sum">{summary.home?.[1] ?? ""}</td>
                <td className="gd-inn-sum">{summary.home?.[2] ?? ""}</td>
              </>}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LiveBattersTable({ batters, teamName }) {
  if (!batters || batters.length === 0) return null;
  return (
    <div className="gd-section">
      <h4 className="gd-section-title">{teamName} 타자</h4>
      <table className="gd-batter-table">
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>선수</th>
            <th>타수</th><th>안타</th><th>홈런</th><th>타점</th><th>타율</th>
          </tr>
        </thead>
        <tbody>
          {batters.map((b, i) => (
            <tr key={i}>
              <td style={{ textAlign: "left" }}>{b.name}</td>
              <td>{b.ab}</td><td>{b.hits}</td>
              <td>{b.hr || "-"}</td><td>{b.rbi}</td>
              <td>{b.avg || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LivePitchersTable({ pitchers, teamName }) {
  if (!pitchers || pitchers.length === 0) return null;
  return (
    <div className="gd-section">
      <h4 className="gd-section-title">{teamName} 투수</h4>
      <table className="gd-batter-table">
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>선수</th>
            <th>이닝</th><th>피안타</th><th>자책</th><th>삼진</th><th>평자</th>
          </tr>
        </thead>
        <tbody>
          {pitchers.map((p, i) => (
            <tr key={i}>
              <td style={{ textAlign: "left" }}>
                {p.name}
                {p.decision && <span className={`lt-decision lt-dec-${p.decision}`} style={{ marginLeft: 4 }}>{p.decision}</span>}
              </td>
              <td>{p.ip}</td><td>{p.hits_allowed}</td>
              <td>{p.er}</td><td>{p.so_count}</td>
              <td>{p.era}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function GameDetail({ gameId, onClose, liveBoxScores, mergedGames }) {
  const { detail, loading } = useGameDetail(gameId);
  const [activeTab, setActiveTab] = useState("summary");

  // 현재 경기의 라이브 박스스코어 찾기 (DB id → 팀명 매칭)
  const liveBox = useMemo(() => {
    if (!liveBoxScores || !mergedGames) return null;
    const game = mergedGames.find((g) => g.id === gameId);
    if (!game) return null;
    return Object.values(liveBoxScores).find(
      (b) =>
        b.home_team === game.home_team?.short_name &&
        b.away_team === game.away_team?.short_name
    ) || null;
  }, [liveBoxScores, mergedGames, gameId]);

  if (loading) return (
    <div className="game-detail-overlay" onClick={onClose}>
      <div className="game-detail-panel" onClick={(e) => e.stopPropagation()}>
        <LoadingSpinner />
      </div>
    </div>
  );

  if (!detail) return null;
  const { game, top_batters, winning_pitcher, losing_pitcher, save_pitcher } = detail;
  const homeColor = TEAM_COLORS[game.home_team.short_name] ?? "#1a365d";
  const awayColor = TEAM_COLORS[game.away_team.short_name] ?? "#718096";

  // mergedGames에서 실시간 점수/상태 가져오기
  const liveGame = mergedGames?.find((g) => g.id === gameId);
  const displayHomeScore = liveGame?.home_score ?? game.home_score;
  const displayAwayScore = liveGame?.away_score ?? game.away_score;
  const isLive = liveGame?.status === "in_progress";

  return (
    <div className="game-detail-overlay" onClick={onClose}>
      <div
        className={`game-detail-panel${activeTab === "lineup" ? " gd-wide" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="gd-close" onClick={onClose}>✕</button>

        {/* LIVE 뱃지 */}
        {isLive && (
          <div className="gd-live-badge">
            LIVE {liveGame.live_inning ? `${liveGame.live_inning}회${liveGame.live_inning_half || ""}` : ""}
          </div>
        )}

        {/* 스코어 헤더 */}
        <div className="gd-scoreline">
          <div className="gd-team" style={{ color: awayColor }}>
            {game.away_team.short_name}
            <span className="gd-score">{displayAwayScore}</span>
          </div>
          <div className="gd-sep">:</div>
          <div className="gd-team" style={{ color: homeColor }}>
            <span className="gd-score">{displayHomeScore}</span>
            {game.home_team.short_name}
          </div>
        </div>
        <div className="gd-meta">{game.date} · {game.stadium}</div>

        {/* 탭 */}
        <div className="gd-tabs">
          <button
            className={`gd-tab${activeTab === "summary" ? " active" : ""}`}
            onClick={() => setActiveTab("summary")}
          >
            요약
          </button>
          <button
            className={`gd-tab${activeTab === "lineup" ? " active" : ""}`}
            onClick={() => setActiveTab("lineup")}
          >
            라인업
          </button>
        </div>

        {/* 요약 탭 */}
        {activeTab === "summary" && (
          <>
            {/* 이닝별 점수 — 라이브 우선, 없으면 API 응답 사용 */}
            <InningScoreTable
              inningScores={liveBox?.inning_scores || detail.inning_scores}
              summary={liveBox?.summary || detail.summary}
              awayName={game.away_team.short_name}
              homeName={game.home_team.short_name}
            />

            {/* 종료 경기: 기존 승/패 투수 */}
            {(winning_pitcher || losing_pitcher) && (
              <div className="gd-section">
                <h4 className="gd-section-title">투수</h4>
                <PitcherLine label="승" pitcher={winning_pitcher} />
                <PitcherLine label="패" pitcher={losing_pitcher} />
                <PitcherLine label="세" pitcher={save_pitcher} />
              </div>
            )}

            {/* 실시간 박스스코어 타자/투수 */}
            {liveBox && (
              <>
                <LiveBattersTable batters={liveBox.away_batters} teamName={game.away_team.short_name} />
                <LivePitchersTable pitchers={liveBox.away_pitchers} teamName={game.away_team.short_name} />
                <LiveBattersTable batters={liveBox.home_batters} teamName={game.home_team.short_name} />
                <LivePitchersTable pitchers={liveBox.home_pitchers} teamName={game.home_team.short_name} />
              </>
            )}

            {/* 기존 주요 타자 (라이브 박스 없을 때) */}
            {!liveBox && top_batters.length > 0 && (
              <div className="gd-section">
                <h4 className="gd-section-title">주요 타자</h4>
                <table className="gd-batter-table">
                  <thead>
                    <tr>
                      <th>선수</th><th>팀</th><th>타수</th><th>안타</th><th>홈런</th><th>타점</th>
                    </tr>
                  </thead>
                  <tbody>
                    {top_batters.map((b, i) => (
                      <tr key={`${b.player_id}-${i}`}>
                        <td>{b.name}</td>
                        <td>{b.team}</td>
                        <td>{b.ab}</td>
                        <td>{b.hits}</td>
                        <td>{b.hr || "-"}</td>
                        <td>{b.rbi}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* 라인업 탭 */}
        {activeTab === "lineup" && <LineupTab gameId={gameId} />}
      </div>
    </div>
  );
}
