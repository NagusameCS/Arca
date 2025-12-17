"""
Market Model
Tracks market index, price history, and circulation status
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, Numeric, String

from .base import Base


class CirculationStatus(Enum):
    """Market circulation status"""

    HEALTHY = "healthy"  # Normal operation
    LOW = "low"  # Below threshold, monitoring
    FROZEN = "frozen"  # Price frozen due to low circulation
    CRITICAL = "critical"  # Severe circulation issues


class MarketIndex(Base):
    """
    Current market index state
    Single record tracking current market conditions
    """

    __tablename__ = "market_index"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Current index value (normalized to 100 as base)
    current_index = Column(Numeric(precision=20, scale=6), default=Decimal("100"), nullable=False)

    # Delayed average (used for public display)
    delayed_average = Column(Numeric(precision=20, scale=6), default=Decimal("100"), nullable=False)

    # Price per carat in diamonds
    carat_price_diamonds = Column(
        Numeric(precision=20, scale=8), default=Decimal("1"), nullable=False
    )

    # Circulation status
    circulation_status = Column(
        SQLEnum(CirculationStatus), default=CirculationStatus.HEALTHY, nullable=False
    )
    is_price_frozen = Column(Boolean, default=False, nullable=False)
    frozen_price = Column(Numeric(precision=20, scale=8), nullable=True)  # Price when frozen

    # Volume metrics
    volume_24h = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)
    transaction_count_24h = Column(Integer, default=0, nullable=False)

    # Trend indicators
    change_1h = Column(Numeric(precision=10, scale=4), default=Decimal("0"), nullable=False)
    change_24h = Column(Numeric(precision=10, scale=4), default=Decimal("0"), nullable=False)
    change_7d = Column(Numeric(precision=10, scale=4), default=Decimal("0"), nullable=False)

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_refresh = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MarketIndex(index={self.current_index}, status={self.circulation_status.value})>"

    @property
    def effective_price(self) -> Decimal:
        """Get the effective trading price (frozen or current)"""
        if self.is_price_frozen and self.frozen_price:
            return Decimal(self.frozen_price)
        return Decimal(self.carat_price_diamonds)


class MarketSnapshot(Base):
    """
    Historical market data points for charting
    """

    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Index values
    index_value = Column(Numeric(precision=20, scale=6), nullable=False)
    delayed_average = Column(Numeric(precision=20, scale=6), nullable=False)

    # Price data
    carat_price = Column(Numeric(precision=20, scale=8), nullable=False)

    # OHLC data for candlestick charts
    open_price = Column(Numeric(precision=20, scale=8), nullable=False)
    high_price = Column(Numeric(precision=20, scale=8), nullable=False)
    low_price = Column(Numeric(precision=20, scale=8), nullable=False)
    close_price = Column(Numeric(precision=20, scale=8), nullable=False)

    # Volume
    volume = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)
    transaction_count = Column(Integer, default=0, nullable=False)

    # Circulation data
    total_circulation = Column(Numeric(precision=20, scale=4), nullable=False)
    circulation_status = Column(SQLEnum(CirculationStatus), nullable=False)

    # Treasury health
    book_value = Column(Numeric(precision=20, scale=6), nullable=False)
    reserve_ratio = Column(Numeric(precision=10, scale=6), nullable=False)

    # Interval info
    interval_type = Column(String(16), nullable=False)  # 'minute', 'hour', 'day'

    # Timestamps
    snapshot_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<MarketSnapshot(time={self.snapshot_time}, index={self.index_value})>"


class MarketAlert(Base):
    """
    Market alerts and notifications
    """

    __tablename__ = "market_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Alert details
    alert_type = Column(
        String(32), nullable=False
    )  # 'circulation_low', 'price_freeze', 'volatility', etc.
    severity = Column(String(16), nullable=False)  # 'info', 'warning', 'critical'
    message = Column(String(512), nullable=False)

    # Related metrics
    trigger_value = Column(Numeric(precision=20, scale=6), nullable=True)
    threshold_value = Column(Numeric(precision=20, scale=6), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<MarketAlert(type={self.alert_type}, severity={self.severity})>"
