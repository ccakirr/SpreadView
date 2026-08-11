import yfinance as yf
import pandas as pd
import numpy as np


class PairDataLoader:
    def __init__(
        self,
        ticker_y: str,
        ticker_x: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> None:
        self.ticker_y = ticker_y
        self.ticker_x = ticker_x
        self.start = start
        self.end = end
        self.interval = interval

        self.y_data: pd.DataFrame | None = None
        self.x_data: pd.DataFrame | None = None
        self._prices: pd.DataFrame | None = None

    def load(self) -> None:
        """
        Download and align the price series.

        Raises:
            ValueError: If data cannot be downloaded or fewer than
                252 common observations remain.
        """
        self.y_data = yf.download(
            self.ticker_y,
            start=self.start,
            end=self.end,
            progress=False,
            interval=self.interval,
            auto_adjust=True
        )
        self.x_data = yf.download(
            self.ticker_x,
            start=self.start,
            end=self.end,
            progress=False,
            interval=self.interval,
            auto_adjust=True
        )

        if self.y_data.empty or self.x_data.empty:
            raise ValueError(
                "Ticker datas cannot loaded."
            )

        self._prices = pd.DataFrame({
            "Y": self.y_data["Close"].squeeze(),
            "X": self.x_data["Close"].squeeze()
        }).dropna()

        if len(self._prices) < 252:
            raise ValueError(
                "Dataset is too small."
                f"Required: >=252, your dataset: {len(self._prices)}."
            )

    @property
    def prices(self) -> pd.DataFrame:
        """
        Return aligned price series.

        Returns:
            pd.DataFrame: Price data with Y and X columns.

        Raises:
            RuntimeError: If load() has not been called.
        """
        if self._prices is None:
            raise RuntimeError("Call load() before accessing prices.")
        return self._prices

    @property
    def returns(self) -> pd.DataFrame:
        """
        Calculate logarithmic returns.

        Returns:
            pd.DataFrame: Log returns with Y and X columns.
        """
        log_returns = np.log(self._prices / self._prices.shift(1))
        return log_returns.dropna()

    def __repr__(self) -> str:
        loaded = self._prices is not None
        rows = len(self._prices) if loaded else 0

        return (
            f"{self.__class__.__name__}("
            f"ticker_y={self.ticker_y!r}, "
            f"ticker_x={self.ticker_x!r}, "
            f"start={self.start!r}, "
            f"end={self.end!r}, "
            f"loaded={loaded}, "
            f"rows={rows})"
        )
