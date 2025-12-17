"""
Arca Bank Configuration
Core configuration settings for the economic system
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EconomyConfig:
    """Economic system configuration"""

    # Currency conversion rates
    GOLDEN_CARAT_MULTIPLIER: int = 9  # 1 Golden Carat = 9 Carats

    # ATM and Book system
    DIAMONDS_PER_BOOK: int = 90  # ATM profit rate
    CARATS_PER_DIAMOND: float = 1.0  # Base conversion rate

    # Market settings
    MARKET_REFRESH_INTERVAL_MINUTES: int = 15  # How often to update market index
    MARKET_AVERAGE_WINDOW_HOURS: int = 24  # Window for calculating delayed average
    PRICE_HISTORY_RETENTION_DAYS: int = 365  # How long to keep price history

    # Circulation controls
    MIN_CIRCULATION_THRESHOLD: float = 1000.0  # Minimum carats in circulation
    CIRCULATION_FREEZE_ENABLED: bool = True  # Enable price freeze below threshold

    # Treasury settings
    TREASURY_RESERVE_RATIO: float = 0.20  # 20% reserve requirement
    MINT_RECOMMENDATION_THRESHOLD: float = 0.15  # 15% variance triggers recommendation

    # Profit margins (Arca's cut)
    TRANSACTION_FEE_PERCENT: float = 1.5  # 1.5% fee on transactions
    EXCHANGE_FEE_PERCENT: float = 2.0  # 2% fee on carat <-> golden carat exchange
    WITHDRAWAL_FEE_PERCENT: float = 1.0  # 1% fee on withdrawals

    # Anti-inflation measures
    MAX_MINT_PER_DAY: float = 10000.0  # Maximum carats that can be minted daily
    BURN_INCENTIVE_THRESHOLD: float = 1.10  # 10% over target triggers burn recommendation


@dataclass
class DatabaseConfig:
    """Database configuration"""

    DATABASE_URL: str = os.getenv("ARCA_DATABASE_URL", "sqlite:///arca_bank.db")
    ECHO_SQL: bool = os.getenv("ARCA_DEBUG", "false").lower() == "true"


@dataclass
class PermissionConfig:
    """Permission levels for roles"""

    # Role IDs (to be set from Discord)
    HEAD_BANKER_ROLE: Optional[str] = None
    BANKER_ROLE: Optional[str] = None

    # Permission levels
    LEVEL_CONSUMER = -1  # Consumer (read-only, price checks)
    LEVEL_READ = 0  # Regular users (can report trades)
    LEVEL_WRITE = 1  # Bankers
    LEVEL_ADMIN = 2  # Head Banker


# Global config instances
economy = EconomyConfig()
database = DatabaseConfig()
permissions = PermissionConfig()
