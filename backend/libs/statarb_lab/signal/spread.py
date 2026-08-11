import pandas as pd


class SpreadCalculator:
    def __init__(self, beta: float, alpha: float):
        self.beta = beta
        self.alpha = alpha

    def compute(self, y: pd.Series, x: pd.Series) -> pd.Series:
        aligned = pd.DataFrame({
            "Y": y,
            "X": x
        }).dropna()

        if aligned.empty:
            raise ValueError(
                "Y and X have no common valid observations."
            )

        spread = aligned["Y"] - self.beta * aligned["X"] - self.alpha
        spread.name = "spread"

        return spread


class ZScoreSignal:
    def __init__(self, window: int = 21):
        if window < 2:
            raise ValueError(
                "Window must be at least 2."
            )

        self.window = window

    def compute(self, spread: pd.Series) -> pd.Series:
        rolling_mean = spread.rolling(
            window=self.window
        ).mean()

        rolling_std = spread.rolling(
            window=self.window
        ).std()

        z_score = (spread - rolling_mean) / rolling_std
        z_score.name = "z_score"

        return z_score

    def __repr__(self) -> str:
        return f"ZScoreSignal(window={self.window})"
