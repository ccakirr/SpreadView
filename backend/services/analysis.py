import numpy as np
import pandas as pd

from services.market import market_data_loader
from services.statarb import analyze_pair


def _json_safe(value):
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, pd.Timestamp):
        return int(value.timestamp())

    if isinstance(value, dict):
        return {
            key: _json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return value


def analyze(
    y: str,
    x: str,
    interval: str,
    window: int,
) -> dict:
    if y == x:
        raise ValueError("Y and X tickers must be different")

    if window < 2:
        raise ValueError("Window must be at least 2")

    try:
        prices = market_data_loader(
            y=y,
            x=x,
            interval=interval,
        )
    except Exception as e:
        raise ValueError(f"Dataset cannot load: {e}") from e

    if prices.empty:
        raise ValueError("Dataset is empty")

    if "Y" not in prices.columns or "X" not in prices.columns:
        raise ValueError(
            f"Invalid dataset columns: {list(prices.columns)}"
        )

    if len(prices) < window:
        raise ValueError(
            f"Not enough data for window={window}. "
            f"Available observations: {len(prices)}"
        )

    y_prices = prices["Y"]
    x_prices = prices["X"]

    result = analyze_pair(
        y=y_prices,
        x=x_prices,
        window=window,
    )

    series = pd.DataFrame({
        "spread": result["spread"],
        "zscore": result["zscore"],
    }).dropna()

    if series.empty:
        raise ValueError(
            "Analysis produced no valid spread/z-score observations"
        )

    chart_data = [
        {
            "time": int(timestamp.timestamp()),
            "spread": float(row["spread"]),
            "zscore": float(row["zscore"]),
        }
        for timestamp, row in series.iterrows()
    ]

    response = {
        "pair": {
            "y": y,
            "x": x,
        },
        "interval": interval,
        "window": window,
        "cointegration": result["cointegration"],
        "hedge": result["hedge"],
        "current": {
            "spread": float(series["spread"].iloc[-1]),
            "zscore": float(series["zscore"].iloc[-1]),
        },
        "series": chart_data,
    }

    return _json_safe(response)
