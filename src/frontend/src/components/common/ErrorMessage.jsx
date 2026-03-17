import "./ErrorMessage.css";

function ErrorMessage({ error, onRetry }) {
  const message =
    error?.detail ||
    error?.error?.message ||
    error?.message ||
    "알 수 없는 오류가 발생했습니다.";

  return (
    <div className="error-box">
      <span className="error-icon">⚠️</span>
      <p className="error-message">{message}</p>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  );
}

export default ErrorMessage;
