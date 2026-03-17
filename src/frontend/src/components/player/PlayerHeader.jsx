import { TEAM_COLORS } from "../../utils/constants";
import "./PlayerHeader.css";

function InitialAvatar({ teamName }) {
  const color = TEAM_COLORS[teamName] ?? "#1a365d";
  const initial = teamName ? teamName[0] : "?";
  return (
    <div className="player-avatar" style={{ backgroundColor: color }}>
      {initial}
    </div>
  );
}

export default function PlayerHeader({ profile }) {
  if (!profile) return null;

  const {
    name,
    team_name,
    position,
    back_number,
    bat_hand,
    throw_hand,
    height,
    weight,
    instagram_url,
    youtube_url,
  } = profile;

  const handInfo = [bat_hand, throw_hand].filter(Boolean).join(" / ");
  const bodyInfo = [
    height ? `${height}cm` : null,
    weight ? `${weight}kg` : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="player-header card">
      <InitialAvatar teamName={team_name} />

      <div className="player-info">
        <div className="player-name-row">
          <h1 className="player-name">{name}</h1>
          {back_number != null && (
            <span className="player-number">#{back_number}</span>
          )}
        </div>
        <div className="player-sub">
          <span className="player-team">{team_name}</span>
          <span className="dot">·</span>
          <span>{position}</span>
        </div>
        {(handInfo || bodyInfo) && (
          <div className="player-detail">
            {handInfo && <span>{handInfo}</span>}
            {handInfo && bodyInfo && <span className="dot">|</span>}
            {bodyInfo && <span>{bodyInfo}</span>}
          </div>
        )}
        {(instagram_url || youtube_url) && (
          <div className="player-sns">
            {instagram_url && (
              <a
                href={instagram_url}
                target="_blank"
                rel="noreferrer"
                className="sns-link"
                title="Instagram"
              >
                📷 Instagram
              </a>
            )}
            {youtube_url && (
              <a
                href={youtube_url}
                target="_blank"
                rel="noreferrer"
                className="sns-link"
                title="YouTube"
              >
                ▶ YouTube
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
