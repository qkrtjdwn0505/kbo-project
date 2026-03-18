import { useState } from "react";
import { NavLink } from "react-router-dom";
import "./Navbar.css";

const NAV_ITEMS = [
  { to: "/",          label: "홈",    end: true },
  { to: "/explorer",  label: "탐색기" },
  { to: "/standings", label: "순위"   },
  { to: "/schedule",  label: "일정"   },
  { to: "/records",   label: "기록"   },
];

function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand" onClick={() => setOpen(false)}>
          ⚾ KBO 데이터 대시보드
        </NavLink>

        {/* 데스크톱 메뉴 */}
        <ul className="navbar-links">
          {NAV_ITEMS.map(({ to, label, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
              >
                {label}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* 햄버거 버튼 (모바일) */}
        <button
          className="navbar-hamburger"
          onClick={() => setOpen((o) => !o)}
          aria-label="메뉴"
          aria-expanded={open}
        >
          {open ? "✕" : "☰"}
        </button>
      </div>

      {/* 모바일 드롭다운 */}
      {open && (
        <div className="navbar-dropdown">
          {NAV_ITEMS.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                isActive ? "navbar-dropdown-link active" : "navbar-dropdown-link"
              }
              onClick={() => setOpen(false)}
            >
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </nav>
  );
}

export default Navbar;
