import pandas as pd

from libs.statarb_lab.stats.cointegration import CointegrationTester
from libs.statarb_lab.stats.hedge import HedgeRatioEstimator
from libs.statarb_lab.signal.spread import SpreadCalculator, ZScoreSignal


def cointegration(y: pd.Series, x: pd.Series) -> dict:
    coint = CointegrationTester()

    result = coint.run_full_check(y, x)

    return result


def hedge_ratio(y: pd.Series, x: pd.Series) -> dict:
    estimator = HedgeRatioEstimator()

    estimator.fit(y=y, x=x)

    return {
        "beta": float(estimator.beta),
        "alpha": float(estimator.alpha),
        "r_square": float(estimator.r_squared),
    }


def spread(y: pd.Series, x: pd.Series, beta: float, alpha: float) -> pd.Series:
    spread_calc = SpreadCalculator(
        beta=beta,
        alpha=alpha
    )

    spread = spread_calc.compute(y, x)

    return spread


def zscore(spread: pd.Series, window: int = 21) -> pd.Series:
    zscore_signal = ZScoreSignal(window=window)
    z_score = zscore_signal.compute(spread=spread)

    return z_score


def analyze_pair(
    y: pd.Series,
    x: pd.Series,
    window: int = 21,
) -> dict:
    coint_result = cointegration(
        y=y,
        x=x,
    )

    hedge_result = hedge_ratio(
        y=y,
        x=x,
    )

    spread_series = spread(
        y=y,
        x=x,
        beta=hedge_result["beta"],
        alpha=hedge_result["alpha"],
    )

    zscore_series = zscore(
        spread=spread_series,
        window=window,
    )

    return {
        "cointegration": coint_result,
        "hedge": hedge_result,
        "spread": spread_series,
        "zscore": zscore_series,
    }
