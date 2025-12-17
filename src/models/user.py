"""
User Model
Handles Discord-Minecraft user linking and roles
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class UserRole(Enum):
    """User permission roles"""

    CONSUMER = "consumer"  # Read-only access (price checks only)
    USER = "user"  # Read + trade reporting access
    BANKER = "banker"  # Write permissions
    HEAD_BANKER = "head_banker"  # Full permissions including minting


class User(Base):
    """
    User model linking Discord and Minecraft accounts
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Discord info
    discord_id = Column(String(32), unique=True, nullable=False, index=True)
    discord_username = Column(String(64), nullable=False)

    # Minecraft info
    minecraft_uuid = Column(String(36), unique=True, nullable=True, index=True)
    minecraft_username = Column(String(16), nullable=True)

    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)

    # Relationships
    balances = relationship("CurrencyBalance", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship(
        "TreasuryTransaction",
        back_populates="user",
        foreign_keys="TreasuryTransaction.user_id",
        cascade="all, delete-orphan",
    )
    trades = relationship(
        "TradeReport", back_populates="reporter", foreign_keys="TradeReport.reporter_id"
    )

    def __repr__(self):
        return f"<User(discord={self.discord_username}, mc={self.minecraft_username}, role={self.role.value})>"

    @property
    def is_consumer(self) -> bool:
        """Check if user is consumer (read-only)"""
        return self.role == UserRole.CONSUMER

    @property
    def is_trader(self) -> bool:
        """Check if user can report trades (USER or higher)"""
        return self.role in (UserRole.USER, UserRole.BANKER, UserRole.HEAD_BANKER)

    @property
    def is_banker(self) -> bool:
        """Check if user has banker permissions"""
        return self.role in (UserRole.BANKER, UserRole.HEAD_BANKER)

    @property
    def is_head_banker(self) -> bool:
        """Check if user is head banker"""
        return self.role == UserRole.HEAD_BANKER

    @property
    def permission_level(self) -> int:
        """Get numeric permission level"""
        from ..config import permissions

        if self.role == UserRole.HEAD_BANKER:
            return permissions.LEVEL_ADMIN
        elif self.role == UserRole.BANKER:
            return permissions.LEVEL_WRITE
        elif self.role == UserRole.USER:
            return permissions.LEVEL_READ
        return permissions.LEVEL_CONSUMER

    def can_trade(self) -> bool:
        """Check if user can report trades"""
        return self.is_trader and self.is_active

    def can_write(self) -> bool:
        """Check if user can perform write operations"""
        return self.is_banker and self.is_active

    def can_mint(self) -> bool:
        """Check if user can mint/burn currency"""
        return self.is_head_banker and self.is_active
