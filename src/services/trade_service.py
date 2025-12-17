"""
Trade Service
Handles trade reporting, trader statistics, and market price tracking
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from ..config import economy
from ..models.market import MarketIndex
from ..models.trade import ItemCategory, MarketPrice, TradeReport, TraderStats, TradeType
from ..models.user import User, UserRole


@dataclass
class TraderReport:
    """Comprehensive trader report"""

    user_id: int
    minecraft_username: str
    discord_username: str
    role: str
    total_trades: int
    buy_count: int
    sell_count: int
    total_volume: float
    average_trade_size: float
    first_trade: Optional[str]
    last_trade: Optional[str]
    verified_trades: int
    reputation_score: float
    recent_trades: List[dict]


class TradeService:
    """
    Service for managing trade reports and trader analytics
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== TRADE REPORTING ====================

    def report_trade(
        self,
        reporter: User,
        trade_type: TradeType,
        item_name: str,
        item_quantity: int,
        carat_amount: Decimal,
        golden_carat_amount: Decimal = Decimal("0"),
        item_category: ItemCategory = ItemCategory.OTHER,
        counterparty_name: Optional[str] = None,
        counterparty_id: Optional[int] = None,
        world_name: Optional[str] = None,
        location: Optional[Tuple[int, int, int]] = None,
        trade_timestamp: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> TradeReport:
        """
        Report a trade from in-game

        Args:
            reporter: User reporting the trade
            trade_type: BUY, SELL, or EXCHANGE
            item_name: Name of item(s) traded
            item_quantity: Quantity of items
            carat_amount: Carats involved
            golden_carat_amount: Golden carats involved (optional)
            item_category: Category for analytics
            counterparty_name: Name of other party (if known)
            counterparty_id: User ID of other party (if registered)
            world_name: Minecraft world name
            location: (x, y, z) coordinates
            trade_timestamp: When trade occurred (defaults to now)
            notes: Additional notes

        Returns:
            TradeReport object
        """
        if not reporter.can_trade():
            raise PermissionError("User cannot report trades (Consumer role)")

        if carat_amount <= 0 and golden_carat_amount <= 0:
            raise ValueError("Trade must involve currency")

        if item_quantity <= 0:
            raise ValueError("Item quantity must be positive")

        # Get current market price for snapshot
        market_index = self.db.query(MarketIndex).first()
        market_price = Decimal(market_index.carat_price_diamonds) if market_index else Decimal("1")

        # Calculate price per item
        total_carats = carat_amount + (golden_carat_amount * 9)
        price_per_item = (total_carats / item_quantity).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

        # Create trade report
        trade = TradeReport(
            reporter_id=reporter.id,
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            trade_type=trade_type,
            item_category=item_category,
            item_name=item_name,
            item_quantity=item_quantity,
            carat_amount=carat_amount,
            golden_carat_amount=golden_carat_amount,
            price_per_item=price_per_item,
            world_name=world_name,
            location_x=location[0] if location else None,
            location_y=location[1] if location else None,
            location_z=location[2] if location else None,
            market_price_at_trade=market_price,
            trade_timestamp=trade_timestamp or datetime.utcnow(),
            notes=notes,
        )
        self.db.add(trade)
        self.db.flush()

        # Update trader stats
        self._update_trader_stats(reporter, trade)

        # Update market prices
        self._update_market_price(item_category, item_name, price_per_item)

        return trade

    def verify_trade(self, trade_id: int, banker: User) -> Optional[TradeReport]:
        """Verify a trade (banker only)"""
        if not banker.is_banker:
            raise PermissionError("Only bankers can verify trades")

        trade = self.db.query(TradeReport).filter(TradeReport.id == trade_id).first()
        if not trade:
            return None

        trade.is_verified = True
        trade.verified_by_id = banker.id
        trade.verified_at = datetime.utcnow()

        # Update trader stats for verification
        stats = self.db.query(TraderStats).filter(TraderStats.user_id == trade.reporter_id).first()
        if stats:
            stats.verified_trade_count += 1
            stats.reputation_score = (
                Decimal(stats.verified_trade_count) / Decimal(stats.total_trades) * 100
            ).quantize(Decimal("0.01"))

        return trade

    # ==================== TRADE QUERIES ====================

    def get_trade(self, trade_id: int) -> Optional[TradeReport]:
        """Get a specific trade by ID"""
        return self.db.query(TradeReport).filter(TradeReport.id == trade_id).first()

    def get_user_trades(
        self,
        user: User,
        limit: int = 50,
        offset: int = 0,
        trade_type: Optional[TradeType] = None,
        days: int = 30,
    ) -> List[TradeReport]:
        """Get trades for a specific user"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(TradeReport).filter(
            TradeReport.reporter_id == user.id, TradeReport.reported_at >= cutoff
        )

        if trade_type:
            query = query.filter(TradeReport.trade_type == trade_type)

        return query.order_by(desc(TradeReport.reported_at)).offset(offset).limit(limit).all()

    def get_recent_trades(
        self,
        limit: int = 50,
        item_category: Optional[ItemCategory] = None,
        item_name: Optional[str] = None,
    ) -> List[TradeReport]:
        """Get recent trades across all users"""
        query = self.db.query(TradeReport)

        if item_category:
            query = query.filter(TradeReport.item_category == item_category)
        if item_name:
            query = query.filter(TradeReport.item_name.ilike(f"%{item_name}%"))

        return query.order_by(desc(TradeReport.reported_at)).limit(limit).all()

    # ==================== TRADER STATISTICS ====================

    def get_trader_stats(self, user: User) -> Optional[TraderStats]:
        """Get statistics for a trader"""
        return self.db.query(TraderStats).filter(TraderStats.user_id == user.id).first()

    def get_trader_report(self, user: User, admin: User) -> TraderReport:
        """
        Generate comprehensive trader report (Head Banker only)
        """
        if not admin.is_head_banker:
            raise PermissionError("Only Head Banker can view trader reports")

        stats = self.get_trader_stats(user)
        recent_trades = self.get_user_trades(user, limit=10)

        return TraderReport(
            user_id=user.id,
            minecraft_username=user.minecraft_username or "N/A",
            discord_username=user.discord_username,
            role=user.role.value,
            total_trades=stats.total_trades if stats else 0,
            buy_count=stats.buy_count if stats else 0,
            sell_count=stats.sell_count if stats else 0,
            total_volume=float(stats.total_volume_carats) if stats else 0,
            average_trade_size=float(stats.average_trade_size) if stats else 0,
            first_trade=(
                stats.first_trade_at.isoformat() if stats and stats.first_trade_at else None
            ),
            last_trade=stats.last_trade_at.isoformat() if stats and stats.last_trade_at else None,
            verified_trades=stats.verified_trade_count if stats else 0,
            reputation_score=float(stats.reputation_score) if stats else 0,
            recent_trades=[
                {
                    "id": t.id,
                    "type": t.trade_type.value,
                    "item": t.item_name,
                    "quantity": t.item_quantity,
                    "amount": float(t.carat_amount),
                    "timestamp": t.reported_at.isoformat(),
                    "verified": t.is_verified,
                }
                for t in recent_trades
            ],
        )

    def get_all_trader_reports(self, admin: User, limit: int = 100) -> List[Dict]:
        """
        Get summary reports for all traders (Head Banker only)
        """
        if not admin.is_head_banker:
            raise PermissionError("Only Head Banker can view all trader reports")

        # Get all trader stats with user info
        results = (
            self.db.query(TraderStats, User)
            .join(User, TraderStats.user_id == User.id)
            .order_by(desc(TraderStats.total_volume_carats))
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": user.id,
                "minecraft_username": user.minecraft_username or "N/A",
                "discord_username": user.discord_username,
                "role": user.role.value,
                "total_trades": stats.total_trades,
                "total_volume": float(stats.total_volume_carats),
                "average_trade_size": float(stats.average_trade_size),
                "verified_trades": stats.verified_trade_count,
                "reputation": float(stats.reputation_score),
                "last_trade": stats.last_trade_at.isoformat() if stats.last_trade_at else None,
            }
            for stats, user in results
        ]

    def get_top_traders(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """Get top traders by volume"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        results = (
            self.db.query(
                TradeReport.reporter_id,
                func.count(TradeReport.id).label("trade_count"),
                func.sum(TradeReport.carat_amount).label("total_volume"),
            )
            .filter(TradeReport.reported_at >= cutoff)
            .group_by(TradeReport.reporter_id)
            .order_by(desc("total_volume"))
            .limit(limit)
            .all()
        )

        top_traders = []
        for reporter_id, trade_count, total_volume in results:
            user = self.db.query(User).filter(User.id == reporter_id).first()
            if user:
                top_traders.append(
                    {
                        "user_id": user.id,
                        "username": user.minecraft_username or user.discord_username,
                        "trade_count": trade_count,
                        "total_volume": float(total_volume or 0),
                    }
                )

        return top_traders

    # ==================== MARKET PRICES ====================

    def get_item_price(self, item_name: str) -> Optional[MarketPrice]:
        """Get current market price for an item"""
        return self.db.query(MarketPrice).filter(MarketPrice.item_name.ilike(item_name)).first()

    def get_category_prices(self, category: ItemCategory) -> List[MarketPrice]:
        """Get all prices for a category"""
        return (
            self.db.query(MarketPrice)
            .filter(MarketPrice.item_category == category)
            .order_by(desc(MarketPrice.volume_24h))
            .all()
        )

    def get_trending_items(self, limit: int = 10) -> List[MarketPrice]:
        """Get items with highest trading volume"""
        cutoff = datetime.utcnow() - timedelta(hours=24)

        return (
            self.db.query(MarketPrice)
            .filter(MarketPrice.last_trade_at >= cutoff)
            .order_by(desc(MarketPrice.volume_24h))
            .limit(limit)
            .all()
        )

    # ==================== INTERNAL HELPERS ====================

    def _update_trader_stats(self, user: User, trade: TradeReport) -> None:
        """Update trader statistics after a new trade"""
        stats = self.db.query(TraderStats).filter(TraderStats.user_id == user.id).first()

        if not stats:
            stats = TraderStats(
                user_id=user.id,
                total_trades=0,
                buy_count=0,
                sell_count=0,
                total_volume_carats=Decimal("0"),
                first_trade_at=trade.reported_at,
            )
            self.db.add(stats)

        # Update counts
        stats.total_trades += 1
        if trade.trade_type == TradeType.BUY:
            stats.buy_count += 1
        elif trade.trade_type == TradeType.SELL:
            stats.sell_count += 1

        # Update volume
        trade_value = trade.total_value_carats
        stats.total_volume_carats = Decimal(stats.total_volume_carats) + trade_value
        stats.average_trade_size = (
            Decimal(stats.total_volume_carats) / Decimal(stats.total_trades)
        ).quantize(Decimal("0.01"))

        # Update timestamps
        stats.last_trade_at = trade.reported_at
        if not stats.first_trade_at:
            stats.first_trade_at = trade.reported_at

    def _update_market_price(self, category: ItemCategory, item_name: str, price: Decimal) -> None:
        """Update market price for an item"""
        market_price = (
            self.db.query(MarketPrice).filter(MarketPrice.item_name.ilike(item_name)).first()
        )

        if not market_price:
            market_price = MarketPrice(
                item_category=category,
                item_name=item_name,
                current_price=price,
                trade_count_24h=1,
                volume_24h=price,
                last_trade_at=datetime.utcnow(),
            )
            self.db.add(market_price)
        else:
            # Update with exponential moving average
            alpha = Decimal("0.3")  # Weight for new price
            old_price = Decimal(market_price.current_price)
            market_price.current_price = (alpha * price + (1 - alpha) * old_price).quantize(
                Decimal("0.0001"), rounding=ROUND_DOWN
            )
            market_price.trade_count_24h += 1
            market_price.volume_24h = Decimal(market_price.volume_24h) + price
            market_price.last_trade_at = datetime.utcnow()
