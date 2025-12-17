"""
Currency Model
Handles Carats and Golden Carats
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..config import economy
from .base import Base


class CurrencyType(Enum):
    """Types of currency in the system"""

    CARAT = "carat"
    GOLDEN_CARAT = "golden_carat"


class CurrencyBalance(Base):
    """
    User currency balances
    Tracks both Carats and Golden Carats for each user
    """

    __tablename__ = "currency_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Currency details
    currency_type = Column(SQLEnum(CurrencyType), nullable=False)
    balance = Column(Numeric(precision=20, scale=4), default=Decimal("0"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="balances")

    def __repr__(self):
        return f"<CurrencyBalance(user_id={self.user_id}, type={self.currency_type.value}, balance={self.balance})>"

    @property
    def balance_in_carats(self) -> Decimal:
        """Convert balance to base carats"""
        if self.currency_type == CurrencyType.GOLDEN_CARAT:
            return Decimal(self.balance) * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)
        return Decimal(self.balance)

    @classmethod
    def convert_to_golden(cls, carats: Decimal) -> Decimal:
        """Convert carats to golden carats"""
        return carats / Decimal(economy.GOLDEN_CARAT_MULTIPLIER)

    @classmethod
    def convert_to_carats(cls, golden_carats: Decimal) -> Decimal:
        """Convert golden carats to carats"""
        return golden_carats * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)


class CurrencyExchange(Base):
    """
    Record of currency exchanges between Carats and Golden Carats
    """

    __tablename__ = "currency_exchanges"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Exchange details
    from_currency = Column(SQLEnum(CurrencyType), nullable=False)
    to_currency = Column(SQLEnum(CurrencyType), nullable=False)
    from_amount = Column(Numeric(precision=20, scale=4), nullable=False)
    to_amount = Column(Numeric(precision=20, scale=4), nullable=False)
    fee_amount = Column(Numeric(precision=20, scale=4), nullable=False)  # Fee in carats

    # Exchange rate at time of transaction
    exchange_rate = Column(Numeric(precision=10, scale=4), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CurrencyExchange({self.from_amount} {self.from_currency.value} -> {self.to_amount} {self.to_currency.value})>"
