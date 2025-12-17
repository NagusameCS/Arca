"""
Treasury Model
Central backing for all currency in circulation
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


class TransactionType(Enum):
    """Types of treasury transactions"""

    DEPOSIT = "deposit"  # Adding to treasury
    WITHDRAWAL = "withdrawal"  # Removing from treasury
    MINT = "mint"  # Creating new currency
    BURN = "burn"  # Destroying currency
    ATM_PROFIT = "atm_profit"  # ATM profits (90 diamonds/book)
    FEE_COLLECTION = "fee_collection"  # Transaction fees collected
    EXCHANGE_FEE = "exchange_fee"  # Currency exchange fees
    TRANSFER = "transfer"  # User to user transfer
    ADJUSTMENT = "adjustment"  # Manual adjustment by head banker


class Treasury(Base):
    """
    Central Treasury
    Single record tracking total treasury state
    """

    __tablename__ = "treasury"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Asset backing (in diamonds)
    total_diamonds = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Currency in circulation
    total_carats_minted = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )
    total_golden_carats_minted = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )

    # Reserve tracking
    reserve_diamonds = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Book tracking (for ATM system)
    total_books_in_circulation = Column(Integer, default=0, nullable=False)

    # Accumulated fees (Arca's profit)
    accumulated_fees_carats = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Treasury(diamonds={self.total_diamonds}, carats={self.total_carats_minted})>"

    @property
    def total_circulation_in_carats(self) -> Decimal:
        """Total currency in circulation converted to base carats"""
        from ..config import economy

        golden_as_carats = Decimal(self.total_golden_carats_minted) * Decimal(
            economy.GOLDEN_CARAT_MULTIPLIER
        )
        return Decimal(self.total_carats_minted) + golden_as_carats

    @property
    def book_value(self) -> Decimal:
        """
        Calculate book value: diamonds backing per carat in circulation
        This is the core metric for treasury health
        """
        if self.total_circulation_in_carats == 0:
            return Decimal("1.0")
        return Decimal(self.total_diamonds) / self.total_circulation_in_carats

    @property
    def reserve_ratio(self) -> Decimal:
        """Current reserve ratio"""
        if self.total_diamonds == 0:
            return Decimal("0")
        return Decimal(self.reserve_diamonds) / Decimal(self.total_diamonds)


class TreasuryTransaction(Base):
    """
    Individual treasury transactions for audit trail
    """

    __tablename__ = "treasury_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)

    # Amounts (can be positive or negative)
    diamond_amount = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)
    carat_amount = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)
    golden_carat_amount = Column(
        Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False
    )

    # Fee collected (if any)
    fee_amount = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Book tracking (for ATM transactions)
    book_count = Column(Integer, default=0, nullable=False)

    # User who initiated the transaction
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # For transfers: recipient user
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Treasury state snapshot after transaction
    treasury_diamonds_after = Column(Numeric(precision=20, scale=4), nullable=False)
    treasury_carats_after = Column(Numeric(precision=20, scale=4), nullable=False)
    book_value_after = Column(Numeric(precision=20, scale=6), nullable=False)

    # Metadata
    notes = Column(Text, nullable=True)
    is_automated = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    recipient = relationship("User", foreign_keys=[recipient_id])

    def __repr__(self):
        return f"<TreasuryTransaction(type={self.transaction_type.value}, diamonds={self.diamond_amount}, carats={self.carat_amount})>"


class TreasurySnapshot(Base):
    """
    Periodic snapshots of treasury state for historical analysis
    """

    __tablename__ = "treasury_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Treasury state at snapshot time
    total_diamonds = Column(Numeric(precision=20, scale=4), nullable=False)
    total_carats = Column(Numeric(precision=20, scale=4), nullable=False)
    total_golden_carats = Column(Numeric(precision=20, scale=4), nullable=False)
    reserve_diamonds = Column(Numeric(precision=20, scale=4), nullable=False)

    # Calculated metrics
    book_value = Column(Numeric(precision=20, scale=6), nullable=False)
    reserve_ratio = Column(Numeric(precision=10, scale=6), nullable=False)
    total_circulation = Column(Numeric(precision=20, scale=4), nullable=False)

    # Accumulated fees since last snapshot
    fees_collected = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Timestamps
    snapshot_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<TreasurySnapshot(time={self.snapshot_time}, book_value={self.book_value})>"
