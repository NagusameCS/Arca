"""
Chart Service
Generates stock-chart style visualizations of market data
"""

import io
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.market import CirculationStatus, MarketSnapshot


class ChartService:
    """
    Service for generating market charts and visualizations
    Features professional stock-style charts with technical indicators
    """

    # Color scheme (dark theme for professional look)
    COLORS = {
        "background": "#1a1a2e",
        "grid": "#2d2d44",
        "text": "#e0e0e0",
        "text_secondary": "#a0a0a0",
        "price_up": "#00d26a",
        "price_down": "#ff4757",
        "price_line": "#4ecdc4",
        "volume": "#667eea",
        "average": "#feca57",
        "frozen": "#ff6b6b",
        "healthy": "#00d26a",
        "warning": "#feca57",
        "critical": "#ff4757",
        "ma_short": "#f39c12",
        "ma_long": "#9b59b6",
        "bollinger_band": "#3498db",
        "rsi_line": "#e74c3c",
        "rsi_overbought": "#27ae60",
        "rsi_oversold": "#e74c3c",
    }

    def __init__(self, db: Session):
        self.db = db

    def generate_market_chart(
        self,
        days: int = 7,
        width: int = 800,
        height: int = 400,
        show_volume: bool = True,
        chart_type: str = "line",  # 'line' or 'candlestick'
    ) -> bytes:
        """
        Generate a market chart image
        Returns PNG bytes
        """
        try:
            import matplotlib

            matplotlib.use("Agg")  # Non-interactive backend
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.patches import Rectangle
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        # Get data
        snapshots = self._get_snapshots(days)

        if not snapshots:
            return self._generate_no_data_chart(width, height)

        # Prepare data
        timestamps = [s.snapshot_time for s in snapshots]
        prices = [float(s.close_price) for s in snapshots]
        volumes = [float(s.volume) for s in snapshots]
        indices = [float(s.index_value) for s in snapshots]
        delayed_avg = [float(s.delayed_average) for s in snapshots]

        # Create figure
        fig, axes = plt.subplots(
            2 if show_volume else 1,
            1,
            figsize=(width / 100, height / 100),
            gridspec_kw={"height_ratios": [3, 1] if show_volume else [1]},
            facecolor=self.COLORS["background"],
        )

        if not show_volume:
            axes = [axes]

        # Price chart
        ax_price = axes[0]
        ax_price.set_facecolor(self.COLORS["background"])

        if chart_type == "candlestick":
            self._draw_candlestick(ax_price, snapshots)
        else:
            # Line chart
            ax_price.plot(
                timestamps,
                prices,
                color=self.COLORS["price_line"],
                linewidth=2,
                label="Carat Price",
            )
            ax_price.plot(
                timestamps,
                delayed_avg,
                color=self.COLORS["average"],
                linewidth=1,
                linestyle="--",
                alpha=0.7,
                label="Delayed Avg",
            )

            # Fill area under price
            ax_price.fill_between(timestamps, prices, alpha=0.2, color=self.COLORS["price_line"])

        # Styling
        ax_price.set_ylabel("Price (Diamonds)", color=self.COLORS["text"])
        ax_price.tick_params(colors=self.COLORS["text"])
        ax_price.grid(True, color=self.COLORS["grid"], alpha=0.3)
        ax_price.legend(
            loc="upper left", facecolor=self.COLORS["background"], labelcolor=self.COLORS["text"]
        )
        ax_price.spines["bottom"].set_color(self.COLORS["grid"])
        ax_price.spines["top"].set_color(self.COLORS["grid"])
        ax_price.spines["left"].set_color(self.COLORS["grid"])
        ax_price.spines["right"].set_color(self.COLORS["grid"])

        # Mark frozen periods
        self._mark_frozen_periods(ax_price, snapshots)

        # Volume chart
        if show_volume:
            ax_volume = axes[1]
            ax_volume.set_facecolor(self.COLORS["background"])
            ax_volume.bar(timestamps, volumes, color=self.COLORS["volume"], alpha=0.7, width=0.02)
            ax_volume.set_ylabel("Volume", color=self.COLORS["text"])
            ax_volume.tick_params(colors=self.COLORS["text"])
            ax_volume.grid(True, color=self.COLORS["grid"], alpha=0.3)
            ax_volume.spines["bottom"].set_color(self.COLORS["grid"])
            ax_volume.spines["top"].set_color(self.COLORS["grid"])
            ax_volume.spines["left"].set_color(self.COLORS["grid"])
            ax_volume.spines["right"].set_color(self.COLORS["grid"])

        # Format x-axis
        ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax_price.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 7)))
        plt.xticks(rotation=45)

        # Title
        latest_price = prices[-1] if prices else 0
        price_change = (
            ((prices[-1] - prices[0]) / prices[0] * 100)
            if len(prices) > 1 and prices[0] != 0
            else 0
        )
        change_color = self.COLORS["price_up"] if price_change >= 0 else self.COLORS["price_down"]

        title = f"Arca Market - {days}D Chart | Price: {latest_price:.4f}◆ | "
        title += f"Change: {price_change:+.2f}%"
        ax_price.set_title(title, color=self.COLORS["text"], fontsize=12, fontweight="bold")

        plt.tight_layout()

        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(
            buf, format="png", facecolor=self.COLORS["background"], edgecolor="none", dpi=100
        )
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()

    def _calculate_moving_average(self, data: List[float], window: int) -> List[Optional[float]]:
        """Calculate simple moving average"""
        result = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(None)
            else:
                avg = sum(data[i - window + 1 : i + 1]) / window
                result.append(avg)
        return result

    def _calculate_bollinger_bands(
        self, data: List[float], window: int = 20, num_std: float = 2.0
    ) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """Calculate Bollinger Bands (middle, upper, lower)"""
        import math

        middle = self._calculate_moving_average(data, window)
        upper = []
        lower = []

        for i in range(len(data)):
            if i < window - 1:
                upper.append(None)
                lower.append(None)
            else:
                window_data = data[i - window + 1 : i + 1]
                mean = sum(window_data) / window
                variance = sum((x - mean) ** 2 for x in window_data) / window
                std = math.sqrt(variance)
                upper.append(mean + num_std * std)
                lower.append(mean - num_std * std)

        return middle, upper, lower

    def _calculate_rsi(self, data: List[float], period: int = 14) -> List[Optional[float]]:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return [None] * len(data)

        result = [None] * period

        # Calculate price changes
        changes = [data[i] - data[i - 1] for i in range(1, len(data))]

        # Initial averages
        gains = [max(0, c) for c in changes[:period]]
        losses = [abs(min(0, c)) for c in changes[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        for i in range(period, len(changes)):
            change = changes[i]
            gain = max(0, change)
            loss = abs(min(0, change))

            # Smoothed averages
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            result.append(rsi)

        return result

    def generate_advanced_chart(
        self,
        days: int = 30,
        width: int = 1000,
        height: int = 700,
        show_volume: bool = True,
        show_rsi: bool = True,
        show_bollinger: bool = True,
        show_ma: bool = True,
        chart_type: str = "candlestick",
    ) -> bytes:
        """
        Generate an advanced stock-style chart with technical indicators

        Features:
        - Candlestick or line chart
        - Moving averages (7-day, 21-day)
        - Bollinger Bands
        - RSI indicator
        - Volume bars
        - Price annotations
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.patches import Rectangle
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        # Get data
        snapshots = self._get_snapshots(days)

        if not snapshots:
            return self._generate_no_data_chart(width, height)

        # Prepare data
        timestamps = [s.snapshot_time for s in snapshots]
        prices = [float(s.close_price) for s in snapshots]
        opens = [float(s.open_price) for s in snapshots]
        highs = [float(s.high_price) for s in snapshots]
        lows = [float(s.low_price) for s in snapshots]
        volumes = [float(s.volume) for s in snapshots]

        # Calculate number of subplots
        num_plots = 1
        if show_volume:
            num_plots += 1
        if show_rsi:
            num_plots += 1

        # Calculate height ratios
        if num_plots == 1:
            height_ratios = [1]
        elif num_plots == 2:
            height_ratios = [3, 1]
        else:
            height_ratios = [3, 1, 1]

        # Create figure
        fig, axes = plt.subplots(
            num_plots,
            1,
            figsize=(width / 100, height / 100),
            gridspec_kw={"height_ratios": height_ratios, "hspace": 0.05},
            facecolor=self.COLORS["background"],
        )

        if num_plots == 1:
            axes = [axes]

        ax_price = axes[0]
        ax_price.set_facecolor(self.COLORS["background"])

        # Draw price chart
        if chart_type == "candlestick":
            self._draw_candlestick(ax_price, snapshots)
        else:
            ax_price.plot(
                timestamps, prices, color=self.COLORS["price_line"], linewidth=2, label="Price"
            )
            ax_price.fill_between(timestamps, prices, alpha=0.1, color=self.COLORS["price_line"])

        # Moving Averages
        if show_ma:
            ma7 = self._calculate_moving_average(prices, 7)
            ma21 = self._calculate_moving_average(prices, 21)

            # Filter None values for plotting
            valid_ma7 = [(t, m) for t, m in zip(timestamps, ma7) if m is not None]
            valid_ma21 = [(t, m) for t, m in zip(timestamps, ma21) if m is not None]

            if valid_ma7:
                ax_price.plot(
                    [x[0] for x in valid_ma7],
                    [x[1] for x in valid_ma7],
                    color=self.COLORS["ma_short"],
                    linewidth=1,
                    label="MA-7",
                    alpha=0.8,
                )
            if valid_ma21:
                ax_price.plot(
                    [x[0] for x in valid_ma21],
                    [x[1] for x in valid_ma21],
                    color=self.COLORS["ma_long"],
                    linewidth=1,
                    label="MA-21",
                    alpha=0.8,
                )

        # Bollinger Bands
        if show_bollinger:
            middle, upper, lower = self._calculate_bollinger_bands(prices)
            valid_upper = [(t, u) for t, u in zip(timestamps, upper) if u is not None]
            valid_lower = [(t, l) for t, l in zip(timestamps, lower) if l is not None]

            if valid_upper and valid_lower:
                upper_times = [x[0] for x in valid_upper]
                upper_vals = [x[1] for x in valid_upper]
                lower_vals = [x[1] for x in valid_lower]

                ax_price.plot(
                    upper_times,
                    upper_vals,
                    color=self.COLORS["bollinger_band"],
                    linewidth=0.8,
                    linestyle="--",
                    alpha=0.6,
                )
                ax_price.plot(
                    upper_times,
                    lower_vals,
                    color=self.COLORS["bollinger_band"],
                    linewidth=0.8,
                    linestyle="--",
                    alpha=0.6,
                )
                ax_price.fill_between(
                    upper_times,
                    upper_vals,
                    lower_vals,
                    alpha=0.05,
                    color=self.COLORS["bollinger_band"],
                )

        # Mark frozen periods
        self._mark_frozen_periods(ax_price, snapshots)

        # Price annotations
        latest_price = prices[-1]
        highest = max(prices)
        lowest = min(prices)
        price_change = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0

        # Add current price line
        ax_price.axhline(
            y=latest_price,
            color=self.COLORS["text_secondary"],
            linestyle=":",
            alpha=0.5,
            linewidth=0.8,
        )
        ax_price.annotate(
            f"{latest_price:.4f}",
            xy=(1.01, latest_price),
            xycoords=("axes fraction", "data"),
            color=self.COLORS["text"],
            fontsize=8,
            va="center",
        )

        # Styling for price chart
        ax_price.set_ylabel("Price", color=self.COLORS["text"], fontsize=10)
        ax_price.tick_params(colors=self.COLORS["text"], labelsize=8)
        ax_price.grid(True, color=self.COLORS["grid"], alpha=0.2, linestyle="-")
        ax_price.legend(
            loc="upper left",
            facecolor=self.COLORS["background"],
            labelcolor=self.COLORS["text"],
            fontsize=8,
            framealpha=0.8,
        )
        self._style_axis(ax_price)
        ax_price.set_xlim(timestamps[0], timestamps[-1])

        # Title with stats
        change_color = self.COLORS["price_up"] if price_change >= 0 else self.COLORS["price_down"]
        title = f"Arca Market | {days}D | {latest_price:.4f}"
        ax_price.set_title(
            title, color=self.COLORS["text"], fontsize=12, fontweight="bold", loc="left"
        )

        # Add change indicator in title area
        ax_price.text(
            0.99,
            1.02,
            f"{price_change:+.2f}%",
            transform=ax_price.transAxes,
            color=change_color,
            fontsize=11,
            fontweight="bold",
            ha="right",
            va="bottom",
        )

        current_ax_idx = 1

        # Volume chart
        if show_volume and current_ax_idx < len(axes):
            ax_volume = axes[current_ax_idx]
            ax_volume.set_facecolor(self.COLORS["background"])

            # Color volume bars by price direction
            colors = []
            for i, s in enumerate(snapshots):
                if float(s.close_price) >= float(s.open_price):
                    colors.append(self.COLORS["price_up"])
                else:
                    colors.append(self.COLORS["price_down"])

            ax_volume.bar(timestamps, volumes, color=colors, alpha=0.6, width=0.8)
            ax_volume.set_ylabel("Vol", color=self.COLORS["text"], fontsize=9)
            ax_volume.tick_params(colors=self.COLORS["text"], labelsize=8)
            ax_volume.grid(True, color=self.COLORS["grid"], alpha=0.2)
            self._style_axis(ax_volume)
            ax_volume.set_xlim(timestamps[0], timestamps[-1])
            current_ax_idx += 1

        # RSI chart
        if show_rsi and current_ax_idx < len(axes):
            ax_rsi = axes[current_ax_idx]
            ax_rsi.set_facecolor(self.COLORS["background"])

            rsi = self._calculate_rsi(prices)
            valid_rsi = [(t, r) for t, r in zip(timestamps, rsi) if r is not None]

            if valid_rsi:
                rsi_times = [x[0] for x in valid_rsi]
                rsi_vals = [x[1] for x in valid_rsi]

                ax_rsi.plot(rsi_times, rsi_vals, color=self.COLORS["rsi_line"], linewidth=1.5)
                ax_rsi.axhline(
                    y=70,
                    color=self.COLORS["rsi_overbought"],
                    linestyle="--",
                    alpha=0.5,
                    linewidth=0.8,
                )
                ax_rsi.axhline(
                    y=30,
                    color=self.COLORS["rsi_oversold"],
                    linestyle="--",
                    alpha=0.5,
                    linewidth=0.8,
                )
                ax_rsi.fill_between(
                    rsi_times,
                    30,
                    rsi_vals,
                    where=[r < 30 for r in rsi_vals],
                    alpha=0.3,
                    color=self.COLORS["rsi_oversold"],
                )
                ax_rsi.fill_between(
                    rsi_times,
                    70,
                    rsi_vals,
                    where=[r > 70 for r in rsi_vals],
                    alpha=0.3,
                    color=self.COLORS["rsi_overbought"],
                )
                ax_rsi.set_ylim(0, 100)

            ax_rsi.set_ylabel("RSI", color=self.COLORS["text"], fontsize=9)
            ax_rsi.tick_params(colors=self.COLORS["text"], labelsize=8)
            ax_rsi.grid(True, color=self.COLORS["grid"], alpha=0.2)
            self._style_axis(ax_rsi)
            ax_rsi.set_xlim(timestamps[0], timestamps[-1])

        # Format x-axis on bottom chart
        bottom_ax = axes[-1]
        bottom_ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        if days <= 7:
            bottom_ax.xaxis.set_major_locator(mdates.DayLocator())
        elif days <= 30:
            bottom_ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        else:
            bottom_ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

        plt.setp(bottom_ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # Hide x labels for upper charts
        for ax in axes[:-1]:
            ax.set_xticklabels([])

        plt.tight_layout()

        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="png",
            facecolor=self.COLORS["background"],
            edgecolor="none",
            dpi=120,
            bbox_inches="tight",
        )
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()

    def _style_axis(self, ax) -> None:
        """Apply consistent styling to an axis"""
        ax.spines["bottom"].set_color(self.COLORS["grid"])
        ax.spines["top"].set_color(self.COLORS["grid"])
        ax.spines["left"].set_color(self.COLORS["grid"])
        ax.spines["right"].set_color(self.COLORS["grid"])

    def generate_multi_timeframe_chart(self, width: int = 1200, height: int = 400) -> bytes:
        """
        Generate a multi-timeframe overview showing 1D, 7D, 30D, and 90D
        Great for getting a quick overview of market trends
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        timeframes = [(1, "1D"), (7, "7D"), (30, "30D"), (90, "90D")]

        fig, axes = plt.subplots(
            1, 4, figsize=(width / 100, height / 100), facecolor=self.COLORS["background"]
        )

        for ax, (days, label) in zip(axes, timeframes):
            ax.set_facecolor(self.COLORS["background"])

            snapshots = self._get_snapshots(days)

            if not snapshots:
                ax.text(
                    0.5,
                    0.5,
                    "No Data",
                    ha="center",
                    va="center",
                    color=self.COLORS["text"],
                    fontsize=10,
                )
                ax.set_title(label, color=self.COLORS["text"], fontsize=11, fontweight="bold")
                continue

            prices = [float(s.close_price) for s in snapshots]

            # Determine color based on price change
            if len(prices) > 1 and prices[0] != 0:
                change = ((prices[-1] - prices[0]) / prices[0]) * 100
                color = self.COLORS["price_up"] if change >= 0 else self.COLORS["price_down"]
            else:
                change = 0
                color = self.COLORS["price_line"]

            # Plot
            ax.plot(range(len(prices)), prices, color=color, linewidth=2)
            ax.fill_between(range(len(prices)), prices, alpha=0.15, color=color)

            # Add min/max markers
            min_idx = prices.index(min(prices))
            max_idx = prices.index(max(prices))
            ax.scatter([min_idx], [min(prices)], color=self.COLORS["price_down"], s=20, zorder=5)
            ax.scatter([max_idx], [max(prices)], color=self.COLORS["price_up"], s=20, zorder=5)

            # Styling
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color(self.COLORS["grid"])
            ax.spines["left"].set_color(self.COLORS["grid"])

            # Title with change
            change_text = f"{change:+.1f}%" if change != 0 else "N/A"
            ax.set_title(f"{label}\n{change_text}", color=color, fontsize=11, fontweight="bold")

            # Current price annotation
            ax.annotate(
                f"{prices[-1]:.3f}",
                xy=(0.5, 0.05),
                xycoords="axes fraction",
                color=self.COLORS["text_secondary"],
                fontsize=9,
                ha="center",
            )

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="png",
            facecolor=self.COLORS["background"],
            edgecolor="none",
            dpi=100,
            bbox_inches="tight",
        )
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()
        """Draw candlestick chart"""
        import matplotlib.patches as patches

        for i, s in enumerate(snapshots):
            open_p = float(s.open_price)
            close_p = float(s.close_price)
            high_p = float(s.high_price)
            low_p = float(s.low_price)

            color = self.COLORS["price_up"] if close_p >= open_p else self.COLORS["price_down"]

            # Wick
            ax.plot([i, i], [low_p, high_p], color=color, linewidth=1)

            # Body
            body_bottom = min(open_p, close_p)
            body_height = abs(close_p - open_p)
            rect = patches.Rectangle(
                (i - 0.3, body_bottom), 0.6, body_height, facecolor=color, edgecolor=color
            )
            ax.add_patch(rect)

    def _mark_frozen_periods(self, ax, snapshots: List[MarketSnapshot]) -> None:
        """Mark periods when price was frozen"""
        frozen_periods = []
        in_frozen = False
        start_idx = 0

        for i, s in enumerate(snapshots):
            if s.circulation_status == CirculationStatus.FROZEN and not in_frozen:
                in_frozen = True
                start_idx = i
            elif s.circulation_status != CirculationStatus.FROZEN and in_frozen:
                in_frozen = False
                frozen_periods.append((start_idx, i))

        if in_frozen:
            frozen_periods.append((start_idx, len(snapshots) - 1))

        for start, end in frozen_periods:
            ax.axvspan(
                snapshots[start].snapshot_time,
                snapshots[end].snapshot_time,
                alpha=0.2,
                color=self.COLORS["frozen"],
                label="Price Frozen",
            )

    def _get_snapshots(self, days: int) -> List[MarketSnapshot]:
        """Get market snapshots for the given period"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(MarketSnapshot)
            .filter(MarketSnapshot.snapshot_time >= cutoff)
            .order_by(MarketSnapshot.snapshot_time)
            .all()
        )

    def _generate_no_data_chart(self, width: int, height: int) -> bytes:
        """Generate a chart indicating no data available"""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        fig, ax = plt.subplots(
            figsize=(width / 100, height / 100), facecolor=self.COLORS["background"]
        )
        ax.set_facecolor(self.COLORS["background"])
        ax.text(
            0.5,
            0.5,
            "No Market Data Available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            color=self.COLORS["text"],
            fontsize=16,
        )
        ax.set_xticks([])
        ax.set_yticks([])

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=self.COLORS["background"])
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()

    def generate_treasury_chart(self, days: int = 30, width: int = 800, height: int = 400) -> bytes:
        """Generate a treasury health chart"""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        from ..models.treasury import TreasurySnapshot

        cutoff = datetime.utcnow() - timedelta(days=days)
        snapshots = (
            self.db.query(TreasurySnapshot)
            .filter(TreasurySnapshot.snapshot_time >= cutoff)
            .order_by(TreasurySnapshot.snapshot_time)
            .all()
        )

        if not snapshots:
            return self._generate_no_data_chart(width, height)

        timestamps = [s.snapshot_time for s in snapshots]
        book_values = [float(s.book_value) for s in snapshots]
        reserve_ratios = [float(s.reserve_ratio) * 100 for s in snapshots]
        circulations = [float(s.total_circulation) for s in snapshots]

        fig, axes = plt.subplots(
            3, 1, figsize=(width / 100, height / 100), facecolor=self.COLORS["background"]
        )

        # Book Value
        axes[0].plot(timestamps, book_values, color=self.COLORS["price_line"], linewidth=2)
        axes[0].axhline(y=1.0, color=self.COLORS["average"], linestyle="--", alpha=0.7)
        axes[0].set_ylabel("Book Value", color=self.COLORS["text"])
        axes[0].set_title("Treasury Health Overview", color=self.COLORS["text"], fontweight="bold")

        # Reserve Ratio
        axes[1].fill_between(timestamps, reserve_ratios, alpha=0.5, color=self.COLORS["volume"])
        axes[1].set_ylabel("Reserve %", color=self.COLORS["text"])

        # Circulation
        axes[2].plot(timestamps, circulations, color=self.COLORS["healthy"], linewidth=2)
        axes[2].set_ylabel("Circulation", color=self.COLORS["text"])

        for ax in axes:
            ax.set_facecolor(self.COLORS["background"])
            ax.tick_params(colors=self.COLORS["text"])
            ax.grid(True, color=self.COLORS["grid"], alpha=0.3)
            ax.spines["bottom"].set_color(self.COLORS["grid"])
            ax.spines["top"].set_color(self.COLORS["grid"])
            ax.spines["left"].set_color(self.COLORS["grid"])
            ax.spines["right"].set_color(self.COLORS["grid"])

        axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=self.COLORS["background"])
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()

    def generate_mini_sparkline(self, days: int = 7, width: int = 200, height: int = 50) -> bytes:
        """Generate a small sparkline chart for embedding"""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            raise RuntimeError("matplotlib is required for chart generation")

        snapshots = self._get_snapshots(days)

        if not snapshots:
            return self._generate_no_data_chart(width, height)

        prices = [float(s.close_price) for s in snapshots]

        fig, ax = plt.subplots(
            figsize=(width / 100, height / 100), facecolor=self.COLORS["background"]
        )
        ax.set_facecolor(self.COLORS["background"])

        color = self.COLORS["price_up"] if prices[-1] >= prices[0] else self.COLORS["price_down"]
        ax.plot(prices, color=color, linewidth=1.5)
        ax.fill_between(range(len(prices)), prices, alpha=0.2, color=color)

        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        plt.tight_layout(pad=0)

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="png",
            facecolor=self.COLORS["background"],
            bbox_inches="tight",
            pad_inches=0,
        )
        plt.close(fig)
        buf.seek(0)

        return buf.getvalue()
