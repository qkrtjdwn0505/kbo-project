import "./Pagination.css";

export default function Pagination({ page, total, perPage, onChange }) {
  const totalPages = Math.ceil(total / perPage);
  if (totalPages <= 1) return null;

  // 최대 7개 페이지 버튼 표시 (현재 페이지 중심)
  function buildPages() {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages = [];
    const around = 2;
    let start = Math.max(2, page - around);
    let end = Math.min(totalPages - 1, page + around);

    pages.push(1);
    if (start > 2) pages.push("...");
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push("...");
    pages.push(totalPages);
    return pages;
  }

  const pages = buildPages();

  return (
    <div className="pagination">
      <button
        className="pg-btn"
        disabled={page === 1}
        onClick={() => onChange(page - 1)}
      >
        ◀
      </button>

      {pages.map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="pg-ellipsis">…</span>
        ) : (
          <button
            key={p}
            className={`pg-btn${p === page ? " active" : ""}`}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        )
      )}

      <button
        className="pg-btn"
        disabled={page === totalPages}
        onClick={() => onChange(page + 1)}
      >
        ▶
      </button>
    </div>
  );
}
