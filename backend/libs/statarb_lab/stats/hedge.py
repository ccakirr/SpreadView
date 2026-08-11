from statsmodels.api import OLS
from statsmodels.api import add_constant
import pandas as pd
import sys


class HedgeRatioEstimator:
    def __init__(self):
        self.model = None

    def fit(self, y: pd.Series, x: pd.Series) -> "HedgeRatioEstimator":
        aligned = pd.DataFrame({
            "X": x,
            "Y": y
        }).dropna()

        x_with_constant = add_constant(aligned["X"])

        self.model = OLS(aligned["Y"], x_with_constant).fit()

        if self.r_squared < 0.80:
            print(
                "\033[1;33m"
                f"Low R-squared: {self.r_squared:.4f} "
                "(recommended: >= 0.80)"
                "\033[0m",
                file=sys.stderr
            )

        return self

    def _check_fitted(self) -> None:
        if self.model is None:
            raise RuntimeError(
                "Call fit() before accessing fitted parameters."
            )

    @property
    def beta(self) -> float:
        self._check_fitted()
        return self.model.params["X"]

    @property
    def alpha(self) -> float:
        self._check_fitted()
        return self.model.params["const"]

    @property
    def r_squared(self) -> float:
        self._check_fitted()
        return self.model.rsquared

    def __repr__(self) -> str:
        if self.model is None:
            return "HedgeRatioEstimator(fitted=False)"

        return (
            "HedgeRatioEstimator("
            "fitted=True, "
            f"alpha={self.alpha:.6f}, "
            f"beta={self.beta:.6f}, "
            f"r_squared={self.r_squared:.4f})"
        )
