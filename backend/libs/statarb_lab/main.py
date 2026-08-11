from __future__ import annotations

import time
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import yfinance as yf

from backtest_engine.events.types import EventQueue, SignalEvent
from backtest_engine.strategy.base import Strategy

from statarb_lab.data.loader import PairDataLoader
from statarb_lab.data.spread_feed import SpreadFeed
from statarb_lab.report.visualizer import PairsVisualizer
from statarb_lab.signal.spread import SpreadCalculator, ZScoreSignal
from statarb_lab.stats.cointegration import CointegrationTester
from statarb_lab.stats.hedge import HedgeRatioEstimator
from statarb_lab.strategy.pairs import PairsStrategy


WINDOW = 96
ENTRY = 2.0
EXIT = 0.5

INITIAL_CAPITAL = 100_000.0

TRANSACTION_COST = 0.0001

PERIODS_PER_YEAR = 252 * 96

INTERVAL = "15m"

TRAIN_START = "2026-06-03"
TRAIN_END = "2026-07-01"

TEST_START = "2026-07-01"
TEST_END = "2026-08-01"

COINTEGRATION_THRESHOLD = 0.05
MIN_R_SQUARED = 0.80

MIN_TRAIN_ROWS = WINDOW + 50
MIN_TEST_ROWS = WINDOW + 50

DOWNLOAD_CHUNK_SIZE = 8
REQUEST_DELAY_SECONDS = 0.25

TRAIN_SCAN_PATH = Path("statarb_training_scan.csv")
RESULTS_PATH = Path("statarb_oos_results.csv")
BEST_REPORT_PATH = Path("statarb_best_oos.png")


PAIR_GROUPS = {
    "USD": [
        "EURUSD=X",
        "GBPUSD=X",
        "AUDUSD=X",
        "NZDUSD=X",
    ],
    "JPY": [
        "USDJPY=X",
        "EURJPY=X",
        "GBPJPY=X",
        "AUDJPY=X",
        "NZDJPY=X",
        "CADJPY=X",
        "CHFJPY=X",
        "SGDJPY=X",
        "NOKJPY=X",
        "SEKJPY=X",
    ],
    "CHF": [
        "USDCHF=X",
        "EURCHF=X",
        "GBPCHF=X",
        "AUDCHF=X",
        "NZDCHF=X",
        "CADCHF=X",
        "SGDCHF=X",
        "NOKCHF=X",
        "SEKCHF=X",
    ],
    "CAD": [
        "USDCAD=X",
        "EURCAD=X",
        "GBPCAD=X",
        "AUDCAD=X",
        "NZDCAD=X",
        "CHFCAD=X",
        "SGDCAD=X",
        "NOKCAD=X",
        "SEKCAD=X",
    ],
    "AUD": [
        "EURAUD=X",
        "GBPAUD=X",
        "NZDAUD=X",
        "CADAUD=X",
        "CHFAUD=X",
        "SGDAUD=X",
        "NOKAUD=X",
        "SEKAUD=X",
    ],
    "NZD": [
        "EURNZD=X",
        "GBPNZD=X",
        "AUDNZD=X",
        "CADNZD=X",
        "CHFNZD=X",
        "SGDNZD=X",
        "NOKNZD=X",
        "SEKNZD=X",
    ],
    "SGD": [
        "USDSGD=X",
        "EURSGD=X",
        "GBPSGD=X",
        "AUDSGD=X",
        "NZDSGD=X",
        "CADSGD=X",
        "CHFSGD=X",
        "JPYSGD=X",
        "NOKSGD=X",
        "SEKSGD=X",
    ],
    "NOK": [
        "USDNOK=X",
        "EURNOK=X",
        "GBPNOK=X",
        "AUDNOK=X",
        "NZDNOK=X",
        "CADNOK=X",
        "CHFNOK=X",
        "JPYNOK=X",
        "SGDNOK=X",
        "SEKNOK=X",
    ],
    "SEK": [
        "USDSEK=X",
        "EURSEK=X",
        "GBPSEK=X",
        "AUDSEK=X",
        "NZDSEK=X",
        "CADSEK=X",
        "CHFSEK=X",
        "JPYSEK=X",
        "SGDSEK=X",
    ],
    "PLN": [
        "USDPLN=X",
        "EURPLN=X",
        "GBPPLN=X",
        "AUDPLN=X",
        "NZDPLN=X",
        "CADPLN=X",
        "CHFPLN=X",
        "JPYPLN=X",
        "SGDPLN=X",
        "NOKPLN=X",
        "SEKPLN=X",
    ],
    "TRY": [
        "USDTRY=X",
        "EURTRY=X",
        "GBPTRY=X",
        "AUDTRY=X",
        "NZDTRY=X",
        "CADTRY=X",
        "CHFTRY=X",
        "JPYTRY=X",
        "SGDTRY=X",
        "NOKTRY=X",
        "SEKTRY=X",
    ],
    "ZAR": [
        "USDZAR=X",
        "EURZAR=X",
        "GBPZAR=X",
        "AUDZAR=X",
        "NZDZAR=X",
        "CADZAR=X",
        "CHFZAR=X",
        "JPYZAR=X",
        "SGDZAR=X",
        "NOKZAR=X",
        "SEKZAR=X",
    ],
    "MXN": [
        "USDMXN=X",
        "EURMXN=X",
        "GBPMXN=X",
        "AUDMXN=X",
        "NZDMXN=X",
        "CADMXN=X",
        "CHFMXN=X",
        "JPYMXN=X",
        "SGDMXN=X",
        "NOKMXN=X",
        "SEKMXN=X",
    ],
}


TICKERS = sorted({
    ticker
    for group in PAIR_GROUPS.values()
    for ticker in group
})


assert issubclass(PairsStrategy, Strategy)


_PAIR_PERIOD_CACHE: dict[
    tuple[str, str, str, str],
    pd.DataFrame,
] = {}


def _chunks(
    values: list[str],
    size: int,
):
    """Split a list into fixed-size chunks."""
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _extract_close_frame(
    raw: pd.DataFrame,
    requested_tickers: list[str],
) -> pd.DataFrame:
    """
    Extract a ticker-keyed Close table from the yfinance response.
    """
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        first_level = raw.columns.get_level_values(0)

        if "Close" not in first_level:
            raise RuntimeError(
                "Yahoo response does not contain a Close field."
            )

        close = raw["Close"].copy()

        if isinstance(close, pd.Series):
            close = close.to_frame(
                name=requested_tickers[0]
            )

    else:
        if "Close" not in raw.columns:
            raise RuntimeError(
                "Yahoo response does not contain a Close column."
            )

        close = raw[["Close"]].copy()
        close.columns = [requested_tickers[0]]

    close = close.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    close = close.dropna(
        axis=1,
        how="all",
    )

    return close.sort_index()


def download_training_panel(
    tickers: list[str],
) -> pd.DataFrame:
    """
    Download every ticker close of the training period in chunks.

    A single request covers a date range shorter than 40 days. The ticker
    list is also split into small chunks to reduce the Yahoo rate-limit
    risk.
    """
    frames: list[pd.DataFrame] = []

    for chunk_number, ticker_chunk in enumerate(
        _chunks(tickers, DOWNLOAD_CHUNK_SIZE),
        start=1,
    ):
        print(
            f"DOWNLOAD | train chunk {chunk_number} | "
            f"{', '.join(ticker_chunk)}"
        )

        raw = yf.download(
            tickers=ticker_chunk,
            start=TRAIN_START,
            end=TRAIN_END,
            interval=INTERVAL,
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="column",
        )

        close = _extract_close_frame(
            raw=raw,
            requested_tickers=ticker_chunk,
        )

        if not close.empty:
            frames.append(close)

        time.sleep(REQUEST_DELAY_SECONDS)

    if not frames:
        raise RuntimeError(
            "Training panel could not be downloaded."
        )

    panel = pd.concat(
        frames,
        axis=1,
    )

    panel = panel.loc[
        :,
        ~panel.columns.duplicated(
            keep="first"
        ),
    ]

    panel = panel.sort_index()

    available = [
        ticker
        for ticker in tickers
        if ticker in panel.columns
    ]

    missing = [
        ticker
        for ticker in tickers
        if ticker not in panel.columns
    ]

    if missing:
        print(
            "MISSING TICKERS | "
            + ", ".join(missing)
        )

    if len(available) < 2:
        raise RuntimeError(
            "Fewer than two ticker series were downloaded."
        )

    return panel[available]


def load_pair_period(
    ticker_y: str,
    ticker_x: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Download a single sub-40-day period through PairDataLoader.

    If the reverse direction was already loaded, the Y and X columns are
    swapped instead of issuing a new request.
    """
    key = (
        ticker_y,
        ticker_x,
        start,
        end,
    )

    cached = _PAIR_PERIOD_CACHE.get(key)

    if cached is not None:
        return cached.copy()

    reverse_key = (
        ticker_x,
        ticker_y,
        start,
        end,
    )

    reverse_cached = _PAIR_PERIOD_CACHE.get(
        reverse_key
    )

    if reverse_cached is not None:
        swapped = pd.DataFrame(
            {
                "Y": reverse_cached["X"],
                "X": reverse_cached["Y"],
            },
            index=reverse_cached.index,
        )

        _PAIR_PERIOD_CACHE[key] = swapped.copy()

        return swapped

    loader = PairDataLoader(
        ticker_y=ticker_y,
        ticker_x=ticker_x,
        start=start,
        end=end,
        interval=INTERVAL,
    )

    loader.load()

    prices = (
        loader.prices[["Y", "X"]]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
        .sort_index()
        .copy()
    )

    if prices.empty:
        raise RuntimeError(
            f"No aligned data for {ticker_y} ~ {ticker_x} "
            f"between {start} and {end}."
        )

    _PAIR_PERIOD_CACHE[key] = prices.copy()

    _PAIR_PERIOD_CACHE[reverse_key] = pd.DataFrame(
        {
            "Y": prices["X"],
            "X": prices["Y"],
        },
        index=prices.index,
    )

    return prices


def scan_training_pairs(
    panel: pd.DataFrame,
) -> pd.DataFrame:
    """
    Scan every directed pair combination over the training period.

    Acceptance conditions:
    - Both raw series must be non-stationary.
    - The Engle-Granger p-value must be below the threshold.
    - The training spread must be stationary.
    - R-squared must be above the configured floor.
    """
    tester = CointegrationTester()
    passed: list[dict] = []

    available_tickers = list(
        panel.columns
    )

    unordered_count = (
        len(available_tickers)
        * (len(available_tickers) - 1)
        // 2
    )

    print("\nTRAINING PERIOD PAIR SCAN")
    print("=" * 135)
    print(f"Period            : {TRAIN_START} -> {TRAIN_END}")
    print(f"Interval          : {INTERVAL}")
    print(f"Available tickers : {len(available_tickers)}")
    print(f"Unordered pairs   : {unordered_count}")
    print(f"Directions        : {unordered_count * 2}")
    print(f"Coint threshold   : {COINTEGRATION_THRESHOLD}")
    print(f"Minimum R-squared : {MIN_R_SQUARED}")
    print("=" * 135)

    tested_directions = 0

    for first, second in combinations(
        available_tickers,
        2,
    ):
        aligned = pd.concat(
            [
                panel[first].rename("first"),
                panel[second].rename("second"),
            ],
            axis=1,
        ).dropna()

        if len(aligned) < MIN_TRAIN_ROWS:
            continue

        directions = [
            (
                first,
                second,
                aligned["first"],
                aligned["second"],
            ),
            (
                second,
                first,
                aligned["second"],
                aligned["first"],
            ),
        ]

        for ticker_y, ticker_x, y, x in directions:
            tested_directions += 1

            try:
                check = tester.run_full_check(
                    y,
                    x,
                )
            except (
                ValueError,
                RuntimeError,
            ):
                continue

            cointegration = check[
                "engle_granger"
            ]

            coint_p = float(
                cointegration["p_value"]
            )

            if (
                not bool(
                    cointegration["cointegrated"]
                )
                or coint_p >= COINTEGRATION_THRESHOLD
            ):
                continue

            estimator = HedgeRatioEstimator().fit(
                y,
                x,
            )

            r_squared = float(
                estimator.r_squared
            )

            if r_squared < MIN_R_SQUARED:
                print(
                    f"REJECT LOW R2 | "
                    f"{ticker_y:10} ~ {ticker_x:10} | "
                    f"coint={coint_p:.6f} | "
                    f"R2={r_squared:.4f}"
                )
                continue

            try:
                spread = SpreadCalculator(
                    beta=float(estimator.beta),
                    alpha=float(estimator.alpha),
                ).compute(
                    y,
                    x,
                )

                spread_adf = tester.adf(
                    spread,
                    name="train_spread",
                )
            except (
                ValueError,
                RuntimeError,
            ):
                continue

            if not bool(
                spread_adf["stationary"]
            ):
                continue

            record = {
                "ticker_y": ticker_y,
                "ticker_x": ticker_x,
                "rows": len(aligned),
                "coint_p": coint_p,
                "spread_adf_p": float(
                    spread_adf["p_value"]
                ),
                "alpha": float(
                    estimator.alpha
                ),
                "beta": float(
                    estimator.beta
                ),
                "r_squared": r_squared,
            }

            passed.append(record)

            print(
                f"PASS | "
                f"{ticker_y:10} ~ {ticker_x:10} | "
                f"coint={record['coint_p']:.6f} | "
                f"spreadADF={record['spread_adf_p']:.6f} | "
                f"R2={record['r_squared']:.4f}"
            )

    scan_frame = pd.DataFrame(
        passed,
        columns=[
            "ticker_y",
            "ticker_x",
            "rows",
            "coint_p",
            "spread_adf_p",
            "alpha",
            "beta",
            "r_squared",
        ],
    )

    if not scan_frame.empty:
        scan_frame = (
            scan_frame
            .sort_values(
                by=[
                    "coint_p",
                    "r_squared",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .reset_index(drop=True)
        )

    scan_frame.to_csv(
        TRAIN_SCAN_PATH,
        index=False,
    )

    print("\nTRAINING SCAN RESULT")
    print("-" * 135)
    print(f"Tested directions : {tested_directions}")
    print(f"Passed directions : {len(scan_frame)}")
    print(f"Saved             : {TRAIN_SCAN_PATH.resolve()}")

    if not scan_frame.empty:
        print(
            scan_frame[
                [
                    "ticker_y",
                    "ticker_x",
                    "coint_p",
                    "spread_adf_p",
                    "beta",
                    "r_squared",
                ]
            ].to_string(
                index=False,
                formatters={
                    "coint_p": lambda value: f"{value:.6f}",
                    "spread_adf_p": lambda value: f"{value:.6f}",
                    "beta": lambda value: f"{value:.6f}",
                    "r_squared": lambda value: f"{value:.4f}",
                },
            )
        )

    return scan_frame


def generate_target_positions(
    train_spread: pd.Series,
    test_spread: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Produce test-period target positions using PairsStrategy.

    The tail of the training spread is warm-up data for the rolling
    z-score only. No position is opened during the training period.
    """
    warmup = train_spread.tail(
        WINDOW + 1
    )

    evaluation_spread = pd.concat(
        [
            warmup,
            test_spread,
        ]
    )

    evaluation_spread = (
        evaluation_spread
        .loc[
            ~evaluation_spread.index.duplicated(
                keep="last"
            )
        ]
        .sort_index()
        .rename("spread")
    )

    events = EventQueue()

    feed = SpreadFeed(
        evaluation_spread
    )

    zscore_signal = ZScoreSignal(
        window=WINDOW
    )

    strategy = PairsStrategy(
        feed=feed,
        queue=events,
        zscore_signal=zscore_signal,
        entry=ENTRY,
        exit_thresh=EXIT,
    )

    target_positions = pd.Series(
        0,
        index=test_spread.index,
        dtype=int,
        name="target_position",
    )

    current_position = 0
    first_test_timestamp = test_spread.index[0]

    market_event = SimpleNamespace(
        ticker="SPREAD"
    )

    while feed.has_more():
        latest = feed.get_latest_bars(1)

        if latest.empty:
            continue

        timestamp = latest.index[-1]

        if timestamp < first_test_timestamp:
            continue

        strategy.on_market(
            market_event
        )

        while not events.empty():
            signal = events.get()

            if not isinstance(
                signal,
                SignalEvent,
            ):
                continue

            direction = int(
                signal.direction
            )

            if current_position == 0:
                current_position = direction

            elif direction == -current_position:
                current_position = 0

            elif direction != current_position:
                current_position = direction

        if timestamp in target_positions.index:
            target_positions.loc[
                timestamp
            ] = current_position

    test_zscore = (
        zscore_signal
        .compute(evaluation_spread)
        .reindex(test_spread.index)
        .rename("zscore")
    )

    return target_positions, test_zscore


def calculate_long_spread_return(
    test_prices: pd.DataFrame,
    beta: float,
) -> pd.Series:
    """
    Compute the long-spread return from actual Y and X price changes.

    Spread PnL:
        delta_Y - beta * delta_X

    Gross notional:
        abs(Y_previous) + abs(beta * X_previous)

    This normalization keeps large beta values from creating artificial
    leverage.
    """
    y = test_prices["Y"]
    x = test_prices["X"]

    spread_pnl = (
        y.diff()
        - beta * x.diff()
    )

    gross_notional = (
        y.shift(1).abs()
        + (
            beta * x.shift(1)
        ).abs()
    )

    long_spread_return = (
        spread_pnl
        / gross_notional
    )

    return (
        long_spread_return
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .fillna(0.0)
        .rename("long_spread_return")
    )


def build_trade_log(
    executed_position: pd.Series,
    net_returns: pd.Series,
    spread: pd.Series,
    equity: pd.Series,
) -> pd.DataFrame:
    """
    Build a round-trip trade log from executed spread positions.
    """
    columns = [
        "entry_date",
        "exit_date",
        "direction",
        "entry_price",
        "exit_price",
        "return",
        "PnL",
    ]

    records: list[dict] = []

    active_position = 0
    entry_date = None
    entry_equity = None

    equity_before_bar = (
        equity
        .shift(1)
        .fillna(INITIAL_CAPITAL)
    )

    def close_trade(
        exit_date,
    ) -> None:
        nonlocal active_position
        nonlocal entry_date
        nonlocal entry_equity

        if (
            active_position == 0
            or entry_date is None
            or entry_equity is None
        ):
            return

        trade_returns = net_returns.loc[
            entry_date:exit_date
        ]

        trade_return = float(
            (1.0 + trade_returns).prod()
            - 1.0
        )

        records.append(
            {
                "entry_date": entry_date,
                "exit_date": exit_date,
                "direction": active_position,
                "entry_price": float(
                    spread.loc[entry_date]
                ),
                "exit_price": float(
                    spread.loc[exit_date]
                ),
                "return": trade_return,
                "PnL": (
                    float(entry_equity)
                    * trade_return
                ),
            }
        )

        active_position = 0
        entry_date = None
        entry_equity = None

    for timestamp, value in executed_position.items():
        position = int(value)

        if (
            active_position == 0
            and position != 0
        ):
            active_position = position
            entry_date = timestamp
            entry_equity = float(
                equity_before_bar.loc[timestamp]
            )
            continue

        if (
            active_position != 0
            and position == 0
        ):
            close_trade(timestamp)
            continue

        if (
            active_position != 0
            and position != 0
            and position != active_position
        ):
            close_trade(timestamp)

            active_position = position
            entry_date = timestamp
            entry_equity = float(
                equity_before_bar.loc[timestamp]
            )

    if active_position != 0:
        close_trade(
            executed_position.index[-1]
        )

    return pd.DataFrame(
        records,
        columns=columns,
    )


def calculate_metrics(
    equity: pd.Series,
    net_returns: pd.Series,
    trade_log: pd.DataFrame,
    executed_position: pd.Series,
) -> dict:
    """
    Compute performance metrics from the 15-minute net return series.
    """
    returns = net_returns.dropna()

    return_std = float(
        returns.std()
    )

    if (
        returns.empty
        or return_std == 0
        or np.isnan(return_std)
    ):
        sharpe = 0.0
    else:
        sharpe = float(
            returns.mean()
            / return_std
            * np.sqrt(PERIODS_PER_YEAR)
        )

    initial_point = pd.Series(
        [INITIAL_CAPITAL],
        index=[
            equity.index[0]
            - pd.Timedelta(minutes=15)
        ],
        dtype=float,
    )

    equity_with_initial = pd.concat(
        [
            initial_point,
            equity,
        ]
    )

    running_max = equity_with_initial.cummax()

    drawdown = (
        1.0
        - equity_with_initial / running_max
    )

    max_drawdown = float(
        drawdown.max()
    )

    final_equity = float(
        equity.iloc[-1]
    )

    total_return = (
        final_equity
        / INITIAL_CAPITAL
        - 1.0
    )

    if trade_log.empty:
        n_trades = 0
        win_rate = 0.0
        average_trade = 0.0
        profit_factor = 0.0
    else:
        n_trades = len(
            trade_log
        )

        win_rate = float(
            (
                trade_log["PnL"] > 0
            ).mean()
        )

        average_trade = float(
            trade_log["return"].mean()
        )

        gross_profit = float(
            trade_log.loc[
                trade_log["PnL"] > 0,
                "PnL",
            ].sum()
        )

        gross_loss = abs(
            float(
                trade_log.loc[
                    trade_log["PnL"] < 0,
                    "PnL",
                ].sum()
            )
        )

        if gross_loss > 0:
            profit_factor = (
                gross_profit / gross_loss
            )
        elif gross_profit > 0:
            profit_factor = np.inf
        else:
            profit_factor = 0.0

    exposure = float(
        (
            executed_position != 0
        ).mean()
    )

    return {
        "initial_equity": INITIAL_CAPITAL,
        "final_equity": final_equity,
        "net_pnl": (
            final_equity
            - INITIAL_CAPITAL
        ),
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "average_trade": average_trade,
        "profit_factor": profit_factor,
        "exposure": exposure,
    }


def backtest_pair(
    ticker_y: str,
    ticker_x: str,
) -> tuple[dict, dict]:
    """
    Fit the relationship on the training period and run an out-of-sample
    backtest on the test period.
    """
    train = load_pair_period(
        ticker_y=ticker_y,
        ticker_x=ticker_x,
        start=TRAIN_START,
        end=TRAIN_END,
    )

    test = load_pair_period(
        ticker_y=ticker_y,
        ticker_x=ticker_x,
        start=TEST_START,
        end=TEST_END,
    )

    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(
            f"Not enough training rows: {len(train)}"
        )

    if len(test) < MIN_TEST_ROWS:
        raise RuntimeError(
            f"Not enough testing rows: {len(test)}"
        )

    print(
        f"DATA | train={len(train)} rows | "
        f"test={len(test)} rows"
    )

    train_y = train["Y"]
    train_x = train["X"]

    tester = CointegrationTester()

    train_check = tester.run_full_check(
        train_y,
        train_x,
    )

    train_coint = train_check[
        "engle_granger"
    ]

    if not bool(
        train_coint["cointegrated"]
    ):
        raise RuntimeError(
            "Training period is not cointegrated: "
            f"p={float(train_coint['p_value']):.6f}"
        )

    estimator = HedgeRatioEstimator().fit(
        train_y,
        train_x,
    )

    alpha = float(
        estimator.alpha
    )

    beta = float(
        estimator.beta
    )

    r_squared = float(
        estimator.r_squared
    )

    if r_squared < MIN_R_SQUARED:
        raise RuntimeError(
            "Training R-squared is too low: "
            f"{r_squared:.4f}"
        )

    train_spread = SpreadCalculator(
        beta=beta,
        alpha=alpha,
    ).compute(
        train_y,
        train_x,
    )

    train_spread_adf = tester.adf(
        train_spread,
        name="train_spread",
    )

    if not bool(
        train_spread_adf["stationary"]
    ):
        raise RuntimeError(
            "Training spread is not stationary: "
            f"p={float(train_spread_adf['p_value']):.6f}"
        )

    test_spread = (
        test["Y"]
        - beta * test["X"]
        - alpha
    ).rename("spread")

    test_spread_adf = tester.adf(
        test_spread,
        name="test_spread",
    )

    target_position, test_zscore = (
        generate_target_positions(
            train_spread=train_spread,
            test_spread=test_spread,
        )
    )

    executed_position = (
        target_position
        .shift(1)
        .fillna(0)
        .astype(int)
        .rename("executed_position")
    )

    pair_return = calculate_long_spread_return(
        test_prices=test,
        beta=beta,
    )

    gross_strategy_return = (
        executed_position
        * pair_return
    ).rename("gross_return")

    turnover = (
        executed_position
        .diff()
        .abs()
        .fillna(
            executed_position.abs()
        )
        .rename("turnover")
    )

    transaction_cost_return = (
        turnover
        * TRANSACTION_COST
    ).rename("transaction_cost")

    net_returns = (
        gross_strategy_return
        - transaction_cost_return
    ).rename("net_return")

    if int(
        executed_position.iloc[-1]
    ) != 0:
        closing_cost = (
            abs(
                int(
                    executed_position.iloc[-1]
                )
            )
            * TRANSACTION_COST
        )

        net_returns.iloc[-1] -= (
            closing_cost
        )

        transaction_cost_return.iloc[-1] += (
            closing_cost
        )

    equity = (
        INITIAL_CAPITAL
        * (
            1.0 + net_returns
        ).cumprod()
    ).rename("equity")

    trade_log = build_trade_log(
        executed_position=executed_position,
        net_returns=net_returns,
        spread=test_spread,
        equity=equity,
    )

    metrics = calculate_metrics(
        equity=equity,
        net_returns=net_returns,
        trade_log=trade_log,
        executed_position=executed_position,
    )

    equity_before_bar = (
        equity
        .shift(1)
        .fillna(INITIAL_CAPITAL)
    )

    estimated_cost_cash = float(
        (
            equity_before_bar
            * transaction_cost_return
        ).sum()
    )

    result = {
        "status": "PASS",
        "ticker_y": ticker_y,
        "ticker_x": ticker_x,
        "train_rows": len(train),
        "test_rows": len(test),
        "train_coint_p": float(
            train_coint["p_value"]
        ),
        "train_spread_adf_p": float(
            train_spread_adf["p_value"]
        ),
        "test_spread_adf_p": float(
            test_spread_adf["p_value"]
        ),
        "test_spread_stationary": bool(
            test_spread_adf["stationary"]
        ),
        "alpha": alpha,
        "beta": beta,
        "r_squared": r_squared,
        "initial_equity": metrics[
            "initial_equity"
        ],
        "final_equity": metrics[
            "final_equity"
        ],
        "net_pnl": metrics[
            "net_pnl"
        ],
        "total_return": metrics[
            "total_return"
        ],
        "sharpe": metrics[
            "sharpe"
        ],
        "max_drawdown": metrics[
            "max_drawdown"
        ],
        "n_trades": metrics[
            "n_trades"
        ],
        "win_rate": metrics[
            "win_rate"
        ],
        "average_trade": metrics[
            "average_trade"
        ],
        "profit_factor": metrics[
            "profit_factor"
        ],
        "exposure": metrics[
            "exposure"
        ],
        "estimated_cost_cash": (
            estimated_cost_cash
        ),
        "error": "",
    }

    report_data = {
        "prices": test,
        "spread": test_spread,
        "zscore": test_zscore,
        "target_position": target_position,
        "executed_position": executed_position,
        "pair_return": pair_return,
        "gross_return": gross_strategy_return,
        "transaction_cost": transaction_cost_return,
        "net_return": net_returns,
        "equity": equity,
        "trade_log": trade_log,
    }

    return result, report_data


def print_result(
    result: dict,
) -> None:
    """Print the result of a single pair."""
    stationary_label = (
        "YES"
        if result["test_spread_stationary"]
        else "NO"
    )

    print(
        f"RESULT | "
        f"{result['ticker_y']:10} ~ "
        f"{result['ticker_x']:10} | "
        f"return={result['total_return']:>8.2%} | "
        f"sharpe={result['sharpe']:>7.3f} | "
        f"maxDD={result['max_drawdown']:>7.2%} | "
        f"trades={result['n_trades']:>3} | "
        f"win={result['win_rate']:>7.2%} | "
        f"PF={result['profit_factor']:>6.2f} | "
        f"testADF={stationary_label:>3} | "
        f"cost={result['estimated_cost_cash']:>8.2f}"
    )


def error_result(
    ticker_y: str,
    ticker_x: str,
    error: Exception,
) -> dict:
    """Build an empty result record for a failed pair."""
    return {
        "status": "SKIP",
        "ticker_y": ticker_y,
        "ticker_x": ticker_x,
        "train_rows": np.nan,
        "test_rows": np.nan,
        "train_coint_p": np.nan,
        "train_spread_adf_p": np.nan,
        "test_spread_adf_p": np.nan,
        "test_spread_stationary": False,
        "alpha": np.nan,
        "beta": np.nan,
        "r_squared": np.nan,
        "initial_equity": np.nan,
        "final_equity": np.nan,
        "net_pnl": np.nan,
        "total_return": np.nan,
        "sharpe": np.nan,
        "max_drawdown": np.nan,
        "n_trades": np.nan,
        "win_rate": np.nan,
        "average_trade": np.nan,
        "profit_factor": np.nan,
        "exposure": np.nan,
        "estimated_cost_cash": np.nan,
        "error": str(error),
    }


def main() -> None:
    """
    1. Scan the whole FX universe over the training period.
    2. Select the directions that pass the training filters.
    3. Fit alpha and beta on the training period.
    4. Backtest the selected pairs on the separate test period.
    """
    print("\nSTATISTICAL ARBITRAGE PIPELINE")
    print("=" * 150)
    print(f"Training   : {TRAIN_START} -> {TRAIN_END}")
    print(f"Testing    : {TEST_START} -> {TEST_END}")
    print(f"Interval   : {INTERVAL}")
    print(f"Window     : {WINDOW} bars")
    print(f"Entry      : {ENTRY}")
    print(f"Exit       : {EXIT}")
    print(
        f"Cost       : "
        f"{TRANSACTION_COST:.4%} per turnover"
    )
    print(f"Universe   : {len(TICKERS)} tickers")
    print("=" * 150)

    training_panel = download_training_panel(
        TICKERS
    )

    scan_frame = scan_training_pairs(
        training_panel
    )

    if scan_frame.empty:
        print(
            "\nNo pair passed the configured conditions "
            "during the training period."
        )
        print(
            "The test period backtest was not executed."
        )
        return

    candidate_pairs = [
        (
            str(row.ticker_y),
            str(row.ticker_x),
        )
        for row in scan_frame.itertuples(
            index=False
        )
    ]

    print("\nOUT-OF-SAMPLE BACKTEST")
    print("=" * 150)
    print(f"Candidates : {len(candidate_pairs)}")
    print("=" * 150)

    results: list[dict] = []

    reports: dict[
        tuple[str, str],
        dict,
    ] = {}

    for index, (
        ticker_y,
        ticker_x,
    ) in enumerate(
        candidate_pairs,
        start=1,
    ):
        print(
            f"\n[{index:02}/{len(candidate_pairs):02}] "
            f"{ticker_y} ~ {ticker_x}"
        )
        print("-" * 150)

        try:
            result, report_data = backtest_pair(
                ticker_y=ticker_y,
                ticker_x=ticker_x,
            )

            results.append(result)

            reports[
                (ticker_y, ticker_x)
            ] = report_data

            print_result(result)

        except Exception as error:
            print(
                f"SKIP | "
                f"{ticker_y} ~ {ticker_x} | "
                f"{error}"
            )

            results.append(
                error_result(
                    ticker_y=ticker_y,
                    ticker_x=ticker_x,
                    error=error,
                )
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    results_frame = pd.DataFrame(
        results
    )

    results_frame.to_csv(
        RESULTS_PATH,
        index=False,
    )

    successful = (
        results_frame.loc[
            results_frame["status"] == "PASS"
        ]
        .sort_values(
            by=[
                "sharpe",
                "total_return",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    print("\n\nOUT-OF-SAMPLE RANKING")
    print("=" * 190)

    if successful.empty:
        print(
            "None of the pairs that passed the training scan "
            "completed the test backtest."
        )
        print(
            f"\nResults saved: "
            f"{RESULTS_PATH.resolve()}"
        )
        return

    ranking = successful[
        [
            "ticker_y",
            "ticker_x",
            "train_coint_p",
            "test_spread_adf_p",
            "test_spread_stationary",
            "beta",
            "r_squared",
            "total_return",
            "sharpe",
            "max_drawdown",
            "n_trades",
            "win_rate",
            "profit_factor",
            "exposure",
            "estimated_cost_cash",
        ]
    ].copy()

    ranking.insert(
        0,
        "rank",
        range(
            1,
            len(ranking) + 1,
        ),
    )

    print(
        ranking.to_string(
            index=False,
            formatters={
                "train_coint_p": lambda value: f"{value:.6f}",
                "test_spread_adf_p": lambda value: f"{value:.6f}",
                "beta": lambda value: f"{value:.6f}",
                "r_squared": lambda value: f"{value:.4f}",
                "total_return": lambda value: f"{value:.2%}",
                "sharpe": lambda value: f"{value:.3f}",
                "max_drawdown": lambda value: f"{value:.2%}",
                "win_rate": lambda value: f"{value:.2%}",
                "profit_factor": lambda value: f"{value:.2f}",
                "exposure": lambda value: f"{value:.2%}",
                "estimated_cost_cash": lambda value: f"{value:.2f}",
            },
        )
    )

    print(
        f"\nResults saved: "
        f"{RESULTS_PATH.resolve()}"
    )

    best = successful.iloc[0]

    best_pair = (
        str(best["ticker_y"]),
        str(best["ticker_x"]),
    )

    best_report = reports[
        best_pair
    ]

    visualizer = PairsVisualizer(
        best_report["prices"],
        best_report["spread"],
        best_report["zscore"],
        best_report["equity"],
        best_report["trade_log"],
    )

    visualizer.plot_all(
        str(BEST_REPORT_PATH)
    )

    print("\nBEST OUT-OF-SAMPLE PAIR")
    print("-" * 90)
    print(f"Y               : {best_pair[0]}")
    print(f"X               : {best_pair[1]}")
    print(
        f"Train coint p   : "
        f"{float(best['train_coint_p']):.6f}"
    )
    print(
        f"Test spread ADF : "
        f"{float(best['test_spread_adf_p']):.6f}"
    )
    print(
        f"Test stationary : "
        f"{bool(best['test_spread_stationary'])}"
    )
    print(
        f"Test return     : "
        f"{float(best['total_return']):.2%}"
    )
    print(
        f"Test Sharpe     : "
        f"{float(best['sharpe']):.3f}"
    )
    print(
        f"Max drawdown    : "
        f"{float(best['max_drawdown']):.2%}"
    )
    print(
        f"Win rate        : "
        f"{float(best['win_rate']):.2%}"
    )
    print(
        f"Profit factor   : "
        f"{float(best['profit_factor']):.2f}"
    )
    print(
        f"Exposure        : "
        f"{float(best['exposure']):.2%}"
    )
    print(
        f"Estimated cost  : "
        f"{float(best['estimated_cost_cash']):.2f}"
    )
    print(
        f"Report saved    : "
        f"{BEST_REPORT_PATH.resolve()}"
    )


if __name__ == "__main__":
    main()
