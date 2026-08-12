import { useState } from "react";
import "./App.css";
import ZScoreChart from "./components/ZScoreChart";
import StatsPanel from "./components/StatsPanel";

function App() {
  const [yTicker, setYTicker] = useState("SOL-USD");
  const [xTicker, setXTicker] = useState("XRP-USD");
  const [interval, setInterval] = useState("1d");
  const [window, setWindow] = useState(21);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      y: yTicker,
      x: xTicker,
      interval: interval,
      window: window.toString(),
    });

    try {
      const response = await fetch(
        `/api/v1/analysis?${params}`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Analysis failed");
      }

      setData(result);
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <h1>SpreadView</h1>
      <p>Statistical Arbitrage Pair Analysis</p>

      <div className="analysis-form">
        <label>
          Y Ticker
          <input
            type="text"
            value={yTicker}
            onChange={(event) => setYTicker(event.target.value)}
          />
        </label>

        <label>
          X Ticker
          <input
            type="text"
            value={xTicker}
            onChange={(event) => setXTicker(event.target.value)}
          />
        </label>

        <label>
          Interval
          <select
            value={interval}
            onChange={(event) => setInterval(event.target.value)}
          >
            <option value="1m">1m</option>
            <option value="2m">2m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="30m">30m</option>
            <option value="1h">1h</option>
            <option value="1d">1d</option>
            <option value="1wk">1wk</option>
          </select>
        </label>

        <label>
          Window
          <input
            type="number"
            min="2"
            value={window}
            onChange={(event) => setWindow(Number(event.target.value))}
          />
        </label>

        <button
          type="button"
          onClick={handleAnalyze}
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {data && (
          <div className="result">
            <div className="result-header">
              <div>
                <h2>
                  {data.pair.y} / {data.pair.x}
                </h2>

                <p>
                  {data.interval} · Window {data.window}
                </p>
              </div>
            </div>

            <StatsPanel data={data} />

            <ZScoreChart data={data.series} />
          </div>
      )}
            </main>
  );
}

export default App;