from libs.statarb_lab.data.loader import PairDataLoader
from datetime import datetime, timedelta

MAX_LOOKBACK = {
        "1m": timedelta(days=8),

        "2m": timedelta(days=60),
        "5m": timedelta(days=60),
        "15m": timedelta(days=60),
        "30m": timedelta(days=60),
        "90m": timedelta(days=60),

        "60m": timedelta(days=730),
        "1h": timedelta(days=730),

        "1d": timedelta(days=365 * 99),
        "5d": timedelta(days=365 * 99),
        "1wk": timedelta(days=365 * 99),
        "1mo": timedelta(days=365 * 99),
        "3mo": timedelta(days=365 * 99),
    }


def market_data_loader(y: str, x: str, interval: str):
    interval = interval.lower()

    if interval not in MAX_LOOKBACK:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(MAX_LOOKBACK.keys())}"
        )

    end = datetime.now()
    start = end - MAX_LOOKBACK[interval]

    loader = PairDataLoader(
        ticker_y=y,
        ticker_x=x,
        start=start,
        end=end,
        interval=interval,
    )

    loader.load()

    return loader.prices
