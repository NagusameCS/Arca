"""
Trade Model
Tracks trade reports from players for market analysis
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class TradeType(Enum):
    """Types of trades"""

    BUY = "BUY"  # Player bought items with carats
    SELL = "SELL"  # Player sold items for carats
    EXCHANGE = "EXCHANGE"  # Player exchanged items


class ItemCategory(Enum):
    """Categories of traded items"""

    DIAMOND = "DIAMOND"
    NETHERITE = "NETHERITE"
    ENCHANTED_GEAR = "ENCHANTED_GEAR"
    BUILDING_MATERIALS = "BUILDING_MATERIALS"
    FOOD = "FOOD"
    REDSTONE = "REDSTONE"
    TOOLS = "TOOLS"
    WEAPONS = "WEAPONS"
    ARMOR = "ARMOR"
    POTIONS = "POTIONS"
    RARE_ITEMS = "RARE_ITEMS"
    SERVICES = "SERVICES"
    OTHER = "OTHER"


class TradeReport(Base):
    """
    Individual trade reports from players
    Used to track market activity and trader behavior
    """

    __tablename__ = "trade_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Reporter info
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Trade counterparty (optional - may be anonymous or NPC)
    counterparty_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    counterparty_name = Column(String(64), nullable=True)  # For non-registered players

    # Trade details
    trade_type = Column(SQLEnum(TradeType), nullable=False)

    # What was traded
    item_category = Column(SQLEnum(ItemCategory), default=ItemCategory.OTHER)
    item_name = Column(String(128), nullable=False)  # "Diamond Sword", "64 Oak Planks", etc.
    item_quantity = Column(Integer, default=1, nullable=False)

    # Currency amounts
    carat_amount = Column(Numeric(precision=20, scale=4), nullable=False)
    golden_carat_amount = Column(Numeric(precision=20, scale=4), default=Decimal("0"))

    # Calculated price per item (for analytics)
    price_per_item = Column(Numeric(precision=20, scale=4), nullable=True)

    # Location (optional - for regional market analysis)
    world_name = Column(String(64), nullable=True)
    location_x = Column(Integer, nullable=True)
    location_y = Column(Integer, nullable=True)
    location_z = Column(Integer, nullable=True)

    # Market snapshot at time of trade
    market_price_at_trade = Column(Numeric(precision=20, scale=8), nullable=True)

    # Verification status (bankers can verify trades)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    trade_timestamp = Column(DateTime, nullable=False)  # When the trade actually happened
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    reporter = relationship("User", back_populates="trades", foreign_keys=[reporter_id])
    counterparty = relationship("User", foreign_keys=[counterparty_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    def __repr__(self):
        return f"<TradeReport(id={self.id}, {self.trade_type.value} {self.item_name} for {self.carat_amount}₵)>"

    @property
    def total_value_carats(self) -> Decimal:
        """Get total value in carats"""
        golden_value = Decimal(self.golden_carat_amount or 0) * 9
        return Decimal(self.carat_amount) + golden_value


class TraderStats(Base):
    """
    Aggregated statistics for each trader
    Updated periodically for quick lookups
    """

    __tablename__ = "trader_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Trade counts
    total_trades = Column(Integer, default=0, nullable=False)
    buy_count = Column(Integer, default=0, nullable=False)
    sell_count = Column(Integer, default=0, nullable=False)

    # Volume
    total_volume_carats = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )
    average_trade_size = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )

    # Time-based
    first_trade_at = Column(DateTime, nullable=True)
    last_trade_at = Column(DateTime, nullable=True)

    # Reputation (verified trades / total trades)
    verified_trade_count = Column(Integer, default=0, nullable=False)
    reputation_score = Column(Numeric(precision=5, scale=2), default=Decimal("0"), nullable=False)

    # Last update
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User")

    def __repr__(self):
        return f"<TraderStats(user_id={self.user_id}, trades={self.total_trades}, volume={self.total_volume_carats})>"


class MarketPrice(Base):
    """
    Tracked market prices for specific items
    Built from trade report aggregation
    """

    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Item identification
    item_category = Column(SQLEnum(ItemCategory), nullable=False, index=True)
    item_name = Column(String(128), nullable=False, index=True)

    # Price data
    current_price = Column(Numeric(precision=20, scale=4), nullable=False)
    average_price_24h = Column(Numeric(precision=20, scale=4), nullable=True)
    average_price_7d = Column(Numeric(precision=20, scale=4), nullable=True)

    # Volume
    trade_count_24h = Column(Integer, default=0, nullable=False)
    volume_24h = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Price changes
    change_24h = Column(Numeric(precision=10, scale=4), default=Decimal("0"), nullable=False)
    change_7d = Column(Numeric(precision=10, scale=4), default=Decimal("0"), nullable=False)

    # Timestamps
    last_trade_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MarketPrice({self.item_name}: {self.current_price}₵)>"
