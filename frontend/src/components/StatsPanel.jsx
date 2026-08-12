function StatsPanel({ data }) {
  const zscore = data.current.zscore;
  const cointegrated =
    data.cointegration.engle_granger.cointegrated;

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <span className="stat-label">Z-Score</span>

        <strong className="stat-value">
          {zscore.toFixed(2)}
        </strong>
      </div>

      <div className="stat-card">
        <span className="stat-label">Cointegration</span>

        <strong
          className={
            cointegrated
              ? "stat-value success"
              : "stat-value danger"
          }
        >
          {cointegrated ? "PASS" : "FAIL"}
        </strong>

        <small>
          p ={" "}
          {data.cointegration.engle_granger.p_value.toFixed(4)}
        </small>
      </div>

      <div className="stat-card">
        <span className="stat-label">Hedge Ratio β</span>

        <strong className="stat-value">
          {data.hedge.beta.toFixed(4)}
        </strong>
      </div>

      <div className="stat-card">
        <span className="stat-label">R²</span>

        <strong className="stat-value">
          {data.hedge.r_square.toFixed(4)}
        </strong>
      </div>

      <div className="stat-card">
        <span className="stat-label">Spread</span>

        <strong className="stat-value">
          {data.current.spread.toFixed(4)}
        </strong>
      </div>

      <div className="stat-card">
        <span className="stat-label">Alpha</span>

        <strong className="stat-value">
          {data.hedge.alpha.toFixed(4)}
        </strong>
      </div>
    </div>
  );
}

export default StatsPanel;