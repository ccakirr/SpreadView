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
    prices = market_data_loader(
        y=y,
        x=x,
        interval=interval,
    )

    y_prices = prices[y]
    x_prices = prices[x]

    result = analyze_pair(
        y=y_prices,
        x=x_prices,
        window=window,
    )

    spread_series = result["spread"]
    zscore_series = result["zscore"]

    series = pd.DataFrame({
        "spread": spread_series,
        "zscore": zscore_series,
    }).dropna()

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
