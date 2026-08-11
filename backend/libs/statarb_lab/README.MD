# Statistical Arbitrage Pairs Trading Lab

A cointegration-based statistical arbitrage research pipeline for FX pairs on
15-minute bars.

The pipeline scans a large FX universe over a training period, keeps only the
directed pairs that satisfy strict statistical conditions, freezes the fitted
hedge parameters, and then evaluates those pairs on a separate out-of-sample
test period.

The central question the project answers is whether a long-term relationship
found in the training window survives untouched in a later window, and whether
deviations from that relationship remain tradable after transaction costs.

## Design

The project is split into a research pipeline (`main.py`) and reusable
components under `statarb_lab/`:

```text
statarb_lab/
├── main.py                  End-to-end train/test pipeline
├── data/
│   ├── loader.py            PairDataLoader — downloads and aligns Y and X
│   └── spread_feed.py       SpreadFeed — replays a pre-computed spread
├── stats/
│   ├── cointegration.py     CointegrationTester — ADF and Engle-Granger
│   └── hedge.py             HedgeRatioEstimator — OLS alpha, beta, R-squared
├── signal/
│   └── spread.py            SpreadCalculator and ZScoreSignal
├── strategy/
│   └── pairs.py             PairsStrategy — event-driven z-score strategy
└── report/
    └── visualizer.py        PairsVisualizer — four-panel PNG report
```

`PairsStrategy` is a subclass of `backtest_engine.strategy.base.Strategy` and
consumes market events through the `backtest_engine` event queue. `SpreadFeed`
duck-types the engine's data feed so the spread can be replayed as a single
synthetic instrument, which keeps all pairs-specific logic upstream of the
engine.

## Pipeline

`main.py` runs four stages.

### 1. Training panel download

Every ticker in `PAIR_GROUPS` is downloaded for the training window. Requests
are issued in chunks of `DOWNLOAD_CHUNK_SIZE` tickers with a delay between
chunks to reduce Yahoo rate-limit pressure. Each request covers a range shorter
than 40 days, which is the limit Yahoo enforces for intraday history. Tickers
that return nothing are reported and dropped.

### 2. Training scan

Every unordered ticker combination is tested in both directions, since the
regression is not symmetric. A direction is accepted only if:

1. Both raw price series are non-stationary (ADF).
2. The Engle-Granger p-value is below `COINTEGRATION_THRESHOLD`.
3. The OLS R-squared is at least `MIN_R_SQUARED`.
4. The training spread is stationary (ADF).

Accepted directions are written to `statarb_training_scan.csv`, sorted by
cointegration p-value and then by R-squared.

### 3. Out-of-sample backtest

For each surviving direction the training checks are re-run on the pair's own
aligned data, then `alpha` and `beta` are fitted **only** on the training
window. The test spread is computed with those frozen parameters:

```text
Y     = alpha + beta * X + residual        (fitted on train)
spread = Y - beta * X - alpha              (applied to test)
```

The spread is streamed through `SpreadFeed` into `PairsStrategy`, which emits
signals from the rolling z-score:

* `z < -ENTRY`: long spread
* `z > +ENTRY`: short spread
* `abs(z) < EXIT`: close position

While a position is open, opposite entry signals are ignored; only the exit
threshold is checked. Warm-up bars come from the tail of the training spread,
so no position is ever opened inside the training window.

### 4. Ranking and report

Results for all pairs are written to `statarb_oos_results.csv`, ranked by
Sharpe and then total return. A four-panel PNG report is produced for the
top-ranked pair as `statarb_best_oos.png`.

## Execution and cost model

Look-ahead bias is avoided at two levels. `SpreadFeed.get_latest_bars` never
exposes bars beyond the cursor, and the target position is shifted by one bar
before it is applied to returns, so a decision taken on the close of bar `t`
is only traded from bar `t+1`.

Returns are computed from the actual price changes of both legs rather than
from the spread level:

```text
spread_pnl     = delta_Y - beta * delta_X
gross_notional = abs(Y_prev) + abs(beta * X_prev)
return         = spread_pnl / gross_notional
```

Normalizing by gross notional prevents large hedge ratios from producing
artificial leverage.

Transaction costs are charged on gross-notional turnover at `TRANSACTION_COST`
per unit of turnover (`0.0001` = 1 basis point). Any position still open on the
final test bar is charged a closing cost and treated as closed for the trade
log.

## Metrics

For each pair the pipeline reports:

* Final equity, net PnL, and total return
* Annualized Sharpe ratio (scaled by `PERIODS_PER_YEAR = 252 * 96`)
* Maximum drawdown, measured from initial capital
* Number of round-trip trades, win rate, and average trade return
* Profit factor and time-in-market exposure
* Estimated transaction cost in cash terms
* Training cointegration p-value, and training and test spread ADF p-values

The test spread ADF p-value is recorded but never used as a filter, so it can
be read as an honest diagnostic of whether the relationship held up
out-of-sample.

## Configuration

All parameters live at the top of `main.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `WINDOW` | `96` | Rolling z-score window in bars |
| `ENTRY` | `2.0` | Entry threshold in standard deviations |
| `EXIT` | `0.5` | Exit threshold in standard deviations |
| `INITIAL_CAPITAL` | `100_000.0` | Starting equity |
| `TRANSACTION_COST` | `0.0001` | Cost per unit of gross-notional turnover |
| `PERIODS_PER_YEAR` | `252 * 96` | Bars per year for Sharpe annualization |
| `INTERVAL` | `"15m"` | Bar interval |
| `TRAIN_START` / `TRAIN_END` | `2026-06-03` / `2026-07-01` | Training window |
| `TEST_START` / `TEST_END` | `2026-07-01` / `2026-08-01` | Test window |
| `COINTEGRATION_THRESHOLD` | `0.05` | Maximum Engle-Granger p-value |
| `MIN_R_SQUARED` | `0.80` | Minimum training R-squared |
| `DOWNLOAD_CHUNK_SIZE` | `8` | Tickers per Yahoo request |
| `REQUEST_DELAY_SECONDS` | `0.25` | Delay between requests |

The universe is defined in `PAIR_GROUPS`, keyed by quote currency: USD, JPY,
CHF, CAD, AUD, NZD, SGD, NOK, SEK, PLN, TRY, ZAR, and MXN. Tickers Yahoo does
not serve are dropped automatically during the download stage.

Because both windows must stay under Yahoo's 40-day intraday limit and 15-minute
history is only retained for roughly 60 days, the training and test dates need
to be moved forward as time passes.

## Installation

```bash
pip install -r requirements.txt
```

The pipeline also imports `backtest_engine`, a sibling project in the same
workspace whose package lives one level down at `backtest_engine/backtest_engine`.
Either install it once in editable mode:

```bash
pip install -e ../backtest_engine
```

or put it on the path when running.

## Usage

Run from the workspace root, the directory that contains both `statarb_lab` and
`backtest_engine`:

```bash
PYTHONPATH=backtest_engine python -m statarb_lab.main
```

If `backtest_engine` is installed, the plain form is enough:

```bash
python -m statarb_lab.main
```

The universe is 121 tickers across 13 quote-currency groups, so the training
scan tests several thousand directed combinations and the full run takes a
while. Progress is printed per download chunk and per accepted pair.

## Output files

| File | Contents |
| --- | --- |
| `statarb_training_scan.csv` | Directions that passed the training filters |
| `statarb_oos_results.csv` | Full out-of-sample results, including skips |
| `statarb_best_oos.png` | Four-panel report for the best-ranked pair |

The PNG report contains normalized prices for both legs, the residual spread
with its mean, the z-score with shaded entry zones and threshold lines, and the
equity curve.

## Limitations

This is a research backtest and does not model all real trading conditions.

* No bid/ask spread modeling, which matters most for the exotic quote groups
* No slippage or partial fill modeling
* No leverage, margin, or funding cost modeling
* No portfolio-level allocation across simultaneously valid pairs
* Cost is a flat per-turnover rate rather than a per-instrument estimate
* Scanning many directed pairs invites multiple-testing bias; a low
  cointegration p-value in one window is weak evidence on its own
* Hedge parameters are fitted once and never refreshed inside the test window
* Statistical relationships can break in future market regimes

## Disclaimer

This project is for educational and research purposes only. It is not financial
advice and should not be used as a live trading system without further
validation, risk management, and execution modeling.
