import { Link } from "react-router-dom";
import "./PlayerLink.css";

function PlayerLink({ playerId, name }) {
  return (
    <Link to={`/players/${playerId}`} className="player-link">
      {name}
    </Link>
  );
}

export default PlayerLink;
