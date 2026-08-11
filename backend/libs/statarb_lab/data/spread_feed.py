import pandas as pd


class SpreadFeed:
    """Streams a pre-computed spread under a single cursor.

    Duck-types backtest_engine.DataFeed (get_latest_bars / has_more / cursor)
    so the existing runner accepts it unchanged — but instead of downloading a
    ticker, it replays a spread you already built (Y - beta*X - alpha). All
    pairs-specific work stays upstream; the engine only sees one instrument.
    """

    def __init__(self, spread: pd.Series) -> None:
        if spread.isna().any():
            raise ValueError("spread must be NaN-free.")
        self.data = spread.rename("spread").to_frame()
        self.cursor = 0

    def get_latest_bars(self, n: int = 1) -> pd.DataFrame:
        if n <= 0:
            raise ValueError("n must be positive.")
        return self.data.iloc[:self.cursor].tail(n)   # geleceği göstermez

    def has_more(self) -> bool:
        if self.cursor < len(self.data):
            self.cursor += 1
            return True
        return False

    def get_all_bars(self) -> pd.DataFrame:
        return self.data.copy()

    def __repr__(self) -> str:
        return f"SpreadFeed(rows={len(self.data)}, cursor={self.cursor})"
