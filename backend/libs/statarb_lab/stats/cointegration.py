from statsmodels.tsa.stattools import coint
from statsmodels.tsa.stattools import adfuller
import pandas as pd


class CointegrationTester:
    def adf(self, series: pd.Series, name: str = "") -> dict:
        """
        Run the Augmented Dickey-Fuller stationarity test.

        Args:
            series: Time series to test.
            name: Optional series name.

        Returns:
            Dictionary containing the ADF statistic, p-value,
            and stationarity result.
        """
        adf_result = adfuller(series)
        adf_stat = adf_result[0]
        p_val = adf_result[1]
        stationary = p_val < 0.05

        return {
            "name": name,
            "adf_stat": adf_stat,
            "p_value": p_val,
            "stationary": stationary,
        }

    def engle_granger(self, y: pd.Series, x: pd.Series) -> dict:
        """
        Run the Engle-Granger cointegration test.

        Args:
            y: Dependent price series.
            x: Independent price series.

        Returns:
            Dictionary containing the cointegration statistic,
            p-value, and cointegration result.
        """
        aligned = pd.DataFrame({
            "X": x,
            "Y": y
        }).dropna()
        eg_result = coint(aligned["Y"], aligned["X"])
        eg_stats = eg_result[0]
        p_val = eg_result[1]
        cointegrated = p_val < 0.05

        return {
            "p_value": p_val,
            "coint_stat": eg_stats,
            "cointegrated": cointegrated,
        }

    def run_full_check(self, y: pd.Series, x: pd.Series) -> dict:
        """
        Run stationarity and cointegration checks.

        Args:
            y: First price series.
            x: Second price series.

        Returns:
            Dictionary containing ADF and Engle-Granger results.

        Raises:
            ValueError: If either raw price series is stationary.
        """
        adf_y = self.adf(y)
        adf_x = self.adf(x)

        if adf_x["stationary"] or adf_y["stationary"]:
            raise ValueError(
                "Raw series must both be non-stationary "
                "before testing cointegration."
            )

        eg = self.engle_granger(y, x)

        return {
            "adf_x": adf_x,
            "adf_y": adf_y,
            "engle_granger": eg
        }
