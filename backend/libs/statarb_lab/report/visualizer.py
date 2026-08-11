import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")


class PairsVisualizer:
    """Composes a 4-panel diagnostic report for a pairs-trading backtest.

    Each panel is an independent method taking an Axes, so callers can build
    custom layouts.

    plot_all() arranges the standard 4-panel figure and saves it.
    """

    def __init__(self, prices, spread, zscore, equity_curve, trade_log,
                 entry: float = 2.0, exit_thresh: float = 0.5) -> None:
        """Store the series to be plotted.

        Args:
            prices: DataFrame with columns Y and X (aligned close prices).
            spread: Series of the spread (Y - beta*X - alpha).
            zscore: Series of the rolling z-score of the spread.
            equity_curve: Series of portfolio equity over time.
            trade_log: Record of executed trades (available for annotation).
            entry: Entry threshold used when composing the z-score panel.
            exit_thresh: Exit threshold used when composing the z-score panel.

        Returns:
            None.
        """
        self.prices = prices
        self.spread = spread
        self.zscore = zscore
        self.equity_curve = equity_curve
        self.trade_log = trade_log
        self.entry = entry
        self.exit_thresh = exit_thresh

    def plot_prices(self, ax) -> None:
        """Draw the two price series rebased to 100 at the first observation.

        Args:
            ax: Matplotlib Axes to draw on.

        Returns:
            None.
        """
        normalized = self.prices / self.prices.iloc[0] * 100.0
        ax.plot(normalized.index, normalized["Y"], label="Y", linewidth=1.2)
        ax.plot(normalized.index, normalized["X"], label="X", linewidth=1.2)
        ax.set_title("Normalized prices (rebased to 100)")
        ax.set_ylabel("Index")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)

    def plot_spread(self, ax) -> None:
        """Draw the spread with a horizontal line at its full-sample mean.

        The mean line is descriptive only; trading signals use the causal
        rolling z-score, not this line.

        Args:
            ax: Matplotlib Axes to draw on.

        Returns:
            None.
        """
        ax.plot(
                self.spread.index,
                self.spread.values,
                label="spread",
                linewidth=1.0
            )
        ax.axhline(self.spread.mean(), color="black", linestyle="--",
                   linewidth=1.0, label="mean")
        ax.set_title("Spread")
        ax.set_ylabel("Y - beta*X - alpha")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)

    def plot_zscore(self, ax, entry: float, exit_thresh: float) -> None:
        """Draw the z-score with shaded entry zones and threshold lines.

        Green shading marks the long-spread zone (z < -entry); red marks the
        short-spread zone (z > +entry). Exit thresholds are dotted lines.

        Args:
            ax: Matplotlib Axes to draw on.
            entry: Entry threshold (positive).
            exit_thresh: Exit threshold (positive).

        Returns:
            None.
        """
        ax.plot(
                self.zscore.index,
                self.zscore.values,
                label="z-score",
                linewidth=1.0
            )
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.axhline(entry, color="grey", linestyle="--", linewidth=0.8)
        ax.axhline(-entry, color="grey", linestyle="--", linewidth=0.8)
        ax.axhline(exit_thresh, color="grey", linestyle=":", linewidth=0.8)
        ax.axhline(-exit_thresh, color="grey", linestyle=":", linewidth=0.8)

        ymin, ymax = ax.get_ylim()
        ax.axhspan(entry, ymax, color="red", alpha=0.10)
        ax.axhspan(ymin, -entry, color="green", alpha=0.10)
        ax.set_ylim(ymin, ymax)

        ax.set_title(f"Z-score (entry={entry}, exit={exit_thresh})")
        ax.set_ylabel("z")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)

    def plot_equity(self, ax) -> None:
        """Draw the cumulative equity curve.

        Args:
            ax: Matplotlib Axes to draw on.

        Returns:
            None.
        """
        ax.plot(self.equity_curve.index, self.equity_curve.values,
                label="equity", linewidth=1.2)
        ax.set_title("Equity curve")
        ax.set_ylabel("Equity")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)

    def plot_all(self, path: str = "statarb_report.png") -> None:
        """
        Arrange all four panels vertically (shared time axis) and save to path.

        Args:
            path: Output PNG path.

        Returns:
            None.
        """
        fig, axes = plt.subplots(4, 1, figsize=(12, 16), sharex=True)
        self.plot_prices(axes[0])
        self.plot_spread(axes[1])
        self.plot_zscore(axes[2], self.entry, self.exit_thresh)
        self.plot_equity(axes[3])
        axes[-1].set_xlabel("Date")
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)

    def __repr__(self) -> str:
        return (
            f"PairsVisualizer("
            f"prices={len(self.prices)}, "
            f"spread={len(self.spread)}, "
            f"zscore={len(self.zscore)}, "
            f"equity={len(self.equity_curve)})"
        )
