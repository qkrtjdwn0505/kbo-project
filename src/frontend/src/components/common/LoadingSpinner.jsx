import "./LoadingSpinner.css";

function LoadingSpinner({ message = "로딩 중..." }) {
  return (
    <div className="spinner-wrapper">
      <div className="spinner" />
      <p className="spinner-text">{message}</p>
    </div>
  );
}

export default LoadingSpinner;
