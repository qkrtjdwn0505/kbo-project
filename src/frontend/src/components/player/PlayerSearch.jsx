import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayerSearch } from "../../hooks/usePlayer";
import "./PlayerSearch.css";

export default function PlayerSearch({ placeholder = "선수 검색 (2글자 이상)" }) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // 300ms 디바운스
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { results, loading } = usePlayerSearch(debouncedQuery);

  // 결과가 생기면 드롭다운 열기
  useEffect(() => {
    setOpen(debouncedQuery.length >= 2);
  }, [debouncedQuery, results]);

  function handleSelect(player) {
    setQuery("");
    setOpen(false);
    navigate(`/players/${player.id}`);
  }

  function handleKeyDown(e) {
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  // 드롭다운 아이템 클릭 시 blur 이전에 처리되도록 mousedown 사용
  function handleItemMouseDown(e, player) {
    e.preventDefault(); // blur 방지
    handleSelect(player);
  }

  return (
    <div className="player-search">
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          ref={inputRef}
          type="text"
          className="search-input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => debouncedQuery.length >= 2 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        {loading && <span className="search-spinner" />}
      </div>

      {open && (
        <ul className="search-dropdown">
          {results.length === 0 ? (
            <li className="search-no-result">검색 결과가 없습니다.</li>
          ) : (
            results.map((player) => (
              <li
                key={player.id}
                className="search-item"
                onMouseDown={(e) => handleItemMouseDown(e, player)}
              >
                <span className="search-item-name">{player.name}</span>
                <span className="search-item-meta">
                  {player.team_name} · {player.position}
                  {player.back_number != null && ` · #${player.back_number}`}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
