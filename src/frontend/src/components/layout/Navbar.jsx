import { NavLink } from "react-router-dom";
import "./Navbar.css";

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          ⚾ KBO 데이터 대시보드
        </NavLink>
        <ul className="navbar-links">
          <li>
            <NavLink
              to="/"
              end
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              홈
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/explorer"
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              탐색기
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/standings"
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              순위
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/schedule"
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              일정
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/records"
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              기록
            </NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export default Navbar;
