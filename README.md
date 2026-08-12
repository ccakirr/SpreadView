# SpreadView

Interactive statistical arbitrage pair analysis in the browser.

Enter two tickers and SpreadView downloads their price history, tests whether
they are cointegrated, fits the hedge ratio, and charts the rolling z-score of
the resulting spread. It answers one question at a glance: **is this pair
currently stretched, and is the relationship statistically sound enough to care?**

The statistical core is `statarb_lab`, a cointegration-based pairs trading
research library vendored under `backend/libs/`. SpreadView puts a FastAPI
service and a React dashboard in front of it, so the analysis can be run
per-pair on demand instead of as an offline batch scan.

## Screens

The dashboard shows a stat grid — current z-score, Engle-Granger verdict and
p-value, hedge ratio beta, R-squared, current spread level and alpha — above a
z-score chart with the entry/exit threshold bands.

## Method

For a pair of price series `Y` and `X`:

1. **Stationarity check.** Both raw series are tested with the Augmented
   Dickey-Fuller test. If either one is already stationary, the request fails —
   cointegration is only meaningful between two non-stationary series.
2. **Cointegration test.** The Engle-Granger test is run on the pair. A p-value
   below `0.05` counts as cointegrated.
3. **Hedge ratio.** An OLS regression `Y = alpha + beta * X + residual` gives
   `alpha`, `beta` and `R²`.
4. **Spread.** The residual series `spread = Y - beta * X - alpha`.
5. **Z-score.** The spread is normalized by its own rolling mean and standard
   deviation over `window` bars.

A z-score near zero means the pair sits at its historical relationship; a large
absolute z-score means the spread has diverged, which is the classic mean
reversion entry signal in pairs trading.

Note that the hedge ratio here is fitted on the **entire** downloaded window,
including the most recent bars. That is the right choice for looking at where a
pair stands today, but it is not an out-of-sample measurement — see
[Limitations](#limitations).

## Stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI, uvicorn |
| Stats | statsmodels, pandas, numpy |
| Market data | yfinance |
| Frontend | React 19, Vite, lightweight-charts |
| Delivery | Docker, nginx, Docker Compose |

## Quick start

### Docker Compose

```bash
docker compose up --build
```

* Dashboard: <http://localhost:8080>
* API docs: <http://localhost:8000/docs>

### Local development

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on <http://localhost:5173>, which is already in the
backend's CORS allowlist along with the Compose origin on port `8080`. The
frontend calls the API at `http://127.0.0.1:8000` directly.

## API

### `GET /api/v1/analysis`

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `y` | string | required | Dependent ticker (the regressand) |
| `x` | string | required | Independent ticker (the hedge leg) |
| `interval` | string | `1d` | Bar interval |
| `window` | int | `21` | Rolling z-score window in bars |

Tickers are Yahoo Finance symbols: `SOL-USD`, `AAPL`, `EURUSD=X`, and so on.
The direction matters — `y=SOL-USD&x=XRP-USD` is a different regression from
the reverse, so both are worth trying.

Supported intervals and the history each one pulls:

| Interval | Lookback |
| --- | --- |
| `1m` | 8 days |
| `2m`, `5m`, `15m`, `30m`, `90m` | 60 days |
| `60m`, `1h` | 730 days |
| `1d`, `5d`, `1wk`, `1mo`, `3mo` | full available history |

These ceilings follow Yahoo's own intraday retention limits.

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/analysis?y=SOL-USD&x=XRP-USD&interval=1d&window=21"
```

Response:

```json
{
  "pair": { "y": "SOL-USD", "x": "XRP-USD" },
  "interval": "1d",
  "window": 21,
  "cointegration": {
    "adf_y": { "name": "", "adf_stat": -1.83, "p_value": 0.36, "stationary": false },
    "adf_x": { "name": "", "adf_stat": -2.11, "p_value": 0.24, "stationary": false },
    "engle_granger": { "coint_stat": -3.62, "p_value": 0.0241, "cointegrated": true }
  },
  "hedge": { "alpha": 12.44, "beta": 61.87, "r_square": 0.8123 },
  "current": { "spread": -8.91, "zscore": -2.14 },
  "series": [
    { "time": 1735689600, "spread": -1.02, "zscore": -0.31 }
  ]
}
```

`series` is ordered oldest to newest, with UNIX second timestamps ready for
lightweight-charts, and leading bars dropped where the rolling window has not
warmed up yet.

### Errors

Every rejected request returns `400` with a `detail` message the frontend
surfaces as-is:

* Identical `y` and `x` tickers
* `window < 2`, or fewer available bars than `window`
* Unsupported interval
* Ticker that Yahoo does not serve, or fewer than 252 aligned observations
* Either raw series already stationary
* No valid spread/z-score observations after the rolling window

## Layout

```text
backend/
├── main.py                  FastAPI app and CORS setup
├── routers/analysis.py      GET /api/v1/analysis
├── services/
│   ├── analysis.py          Validation, orchestration, JSON shaping
│   ├── market.py            Interval lookback rules and data loading
│   └── statarb.py           Thin wrappers over statarb_lab
└── libs/statarb_lab/        Vendored research library

frontend/
├── src/App.jsx              Form, fetch, loading and error states
└── src/components/
    ├── StatsPanel.jsx       Stat grid
    └── ZScoreChart.jsx      Z-score chart
```

`services/statarb.py` is the seam between the two halves. The router and
services never import statsmodels directly, so the research library can be
swapped or upgraded without touching the API surface.

## Limitations

SpreadView is a research and educational tool, not a trading system.

* Hedge parameters are fitted on the whole visible window, so the chart is
  in-sample by construction. A pair that looks clean here has not been shown to
  hold up out-of-sample.
* Scanning many pairs until one passes at `p < 0.05` invites multiple-testing
  bias. A single low p-value is weak evidence on its own.
* There is no backtest, no transaction cost model, and no position sizing.
* Data quality is whatever Yahoo Finance returns, including gaps and
  survivorship effects.
* Every request downloads fresh data with no caching, so response time is bound
  by two Yahoo downloads plus the ADF and Engle-Granger tests.
* Statistical relationships break. Cointegration in the past window is not a
  promise about the next one.

## Disclaimer

This project is for educational and research purposes only. It is not financial
advice and should not be used as a live trading system without further
validation, risk management, and execution modeling.
