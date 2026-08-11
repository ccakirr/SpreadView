import pandas as pd

from backtest_engine.events.types import MarketEvent
from backtest_engine.strategy.base import Strategy
from statarb_lab.signal.spread import ZScoreSignal


class PairsStrategy(Strategy):
    def __init__(
        self,
        feed,
        queue,
        zscore_signal: ZScoreSignal,
        entry: float = 2.0,
        exit_thresh: float = 0.5,
    ) -> None:
        super().__init__(feed, queue)

        if entry <= 0:
            raise ValueError("entry must be positive.")

        if not 0 <= exit_thresh < entry:
            raise ValueError(
                "exit_thresh must be between 0 and entry."
            )

        self.zscore_signal = zscore_signal
        self.entry = entry
        self.exit_thresh = exit_thresh

        self._position = 0

    def _target_from_z(self, z: float) -> int:
        """
        Return the desired spread position for the current z-score.

        Flatken entry threshold kontrol edilir. Pozisyon açıkken ters
        entry sinyalleri yok sayılır ve yalnızca exit threshold kontrol edilir.
        """

        if self._position == 0:
            if z < -self.entry:
                return 1

            if z > self.entry:
                return -1

            return 0

        if abs(z) < self.exit_thresh:
            return 0

        return self._position

    def on_market(self, event: MarketEvent) -> None:
        """
        Recalculate the latest z-score and emit an entry or exit signal.
        """

        required_bars = self.zscore_signal.window + 1

        bars = self.feed.get_latest_bars(required_bars)

        if len(bars) < required_bars:
            return

        spread = bars["spread"]

        if isinstance(spread, pd.DataFrame):
            spread = spread.iloc[:, 0]

        zscore = self.zscore_signal.compute(spread)
        latest_z = zscore.iloc[-1]

        if pd.isna(latest_z):
            return

        target = self._target_from_z(float(latest_z))

        if target == self._position:
            return

        if self._position == 0:
            self._emit_signal(
                ticker=event.ticker,
                direction=target,
                strength=1.0,
            )

        else:
            self._emit_signal(
                ticker=event.ticker,
                direction=-self._position,
                strength=1.0,
            )

        self._position = target

    def __repr__(self) -> str:
        return (
            f"PairsStrategy("
            f"entry={self.entry}, "
            f"exit_thresh={self.exit_thresh}, "
            f"window={self.zscore_signal.window}, "
            f"position={self._position}"
            f")"
        )
