"""
Market Service
Tracks market index, price history, circulation status, and provides delayed averages
"""

from collections import deque
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..config import economy
from ..models.market import CirculationStatus, MarketAlert, MarketIndex, MarketSnapshot
from ..models.treasury import Treasury


class MarketService:
    """
    Service for managing market data and indices
    """

    # In-memory price buffer for delayed average calculation
    _price_buffer: deque = deque(maxlen=1000)

    def __init__(self, db: Session):
        self.db = db

    # ==================== MARKET INDEX ====================

    def get_market_index(self) -> MarketIndex:
        """Get or create the market index singleton"""
        index = self.db.query(MarketIndex).first()
        if not index:
            index = MarketIndex(
                current_index=Decimal("100"),
                delayed_average=Decimal("100"),
                carat_price_diamonds=Decimal("1"),
                circulation_status=CirculationStatus.HEALTHY,
                is_price_frozen=False,
            )
            self.db.add(index)
            self.db.flush()
        return index

    def get_market_status(self) -> dict:
        """Get comprehensive market status"""
        index = self.get_market_index()
        treasury = self.db.query(Treasury).first()

        return {
            "current_index": Decimal(index.current_index),
            "delayed_average": Decimal(index.delayed_average),
            "carat_price": Decimal(index.carat_price_diamonds),
            "effective_price": index.effective_price,
            "circulation_status": index.circulation_status.value,
            "is_price_frozen": index.is_price_frozen,
            "frozen_price": Decimal(index.frozen_price) if index.frozen_price else None,
            "volume_24h": Decimal(index.volume_24h),
            "transaction_count_24h": index.transaction_count_24h,
            "change_1h": Decimal(index.change_1h),
            "change_24h": Decimal(index.change_24h),
            "change_7d": Decimal(index.change_7d),
            "last_updated": index.last_updated,
            "last_refresh": index.last_refresh,
            "total_circulation": treasury.total_circulation_in_carats if treasury else Decimal("0"),
        }

    # ==================== PRICE CALCULATIONS ====================

    def update_price_from_book_value(self, book_value: Decimal) -> Decimal:
        """
        Update carat price based on treasury book value
        Book value is diamonds/carat, which directly determines price
        """
        index = self.get_market_index()
        old_price = Decimal(index.carat_price_diamonds)

        # Store in buffer for delayed average
        self._price_buffer.append({"price": book_value, "timestamp": datetime.utcnow()})

        # Update current price (unless frozen)
        if not index.is_price_frozen:
            index.carat_price_diamonds = book_value

        # Update index relative to base
        base_price = Decimal("1.0")  # Base price is 1 diamond = 1 carat
        index.current_index = (book_value / base_price * Decimal("100")).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

        index.last_updated = datetime.utcnow()

        return book_value

    def calculate_delayed_average(self, window_hours: int = None) -> Decimal:
        """
        Calculate delayed moving average for public display
        This prevents front-running and manipulation
        """
        if window_hours is None:
            window_hours = economy.MARKET_AVERAGE_WINDOW_HOURS

        cutoff = datetime.utcnow() - timedelta(hours=window_hours)

        # Get from snapshots
        snapshots = (
            self.db.query(MarketSnapshot).filter(MarketSnapshot.snapshot_time >= cutoff).all()
        )

        if not snapshots:
            index = self.get_market_index()
            return Decimal(index.current_index)

        total = sum(Decimal(s.index_value) for s in snapshots)
        return (total / len(snapshots)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

    def refresh_market_index(self) -> MarketIndex:
        """
        Periodic refresh of market index
        Called every X minutes as configured
        """
        index = self.get_market_index()
        treasury = self.db.query(Treasury).first()

        if not treasury:
            return index

        # Update delayed average
        index.delayed_average = self.calculate_delayed_average()

        # Calculate changes
        index.change_1h = self._calculate_change(hours=1)
        index.change_24h = self._calculate_change(hours=24)
        index.change_7d = self._calculate_change(hours=168)

        # Update volume metrics
        self._update_volume_metrics(index)

        # Check circulation status
        self._check_circulation_status(treasury, index)

        index.last_refresh = datetime.utcnow()

        return index

    def _calculate_change(self, hours: int) -> Decimal:
        """Calculate percentage change over time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        old_snapshot = (
            self.db.query(MarketSnapshot)
            .filter(MarketSnapshot.snapshot_time <= cutoff)
            .order_by(desc(MarketSnapshot.snapshot_time))
            .first()
        )

        if not old_snapshot:
            return Decimal("0")

        index = self.get_market_index()
        old_value = Decimal(old_snapshot.index_value)
        current_value = Decimal(index.current_index)

        if old_value == 0:
            return Decimal("0")

        change = ((current_value - old_value) / old_value * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        return change

    def _update_volume_metrics(self, index: MarketIndex) -> None:
        """Update 24h volume metrics"""
        from ..models.treasury import TreasuryTransaction

        cutoff = datetime.utcnow() - timedelta(hours=24)

        transactions = (
            self.db.query(TreasuryTransaction)
            .filter(TreasuryTransaction.created_at >= cutoff)
            .all()
        )

        total_volume = sum(
            abs(Decimal(tx.carat_amount))
            + abs(Decimal(tx.golden_carat_amount)) * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)
            for tx in transactions
        )

        index.volume_24h = total_volume
        index.transaction_count_24h = len(transactions)

    # ==================== CIRCULATION CONTROL ====================

    def _check_circulation_status(self, treasury: Treasury, index: MarketIndex) -> None:
        """Check and update circulation status"""
        total_circulation = treasury.total_circulation_in_carats
        threshold = Decimal(economy.MIN_CIRCULATION_THRESHOLD)

        if total_circulation < threshold * Decimal("0.5"):
            # Critical - way below threshold
            index.circulation_status = CirculationStatus.CRITICAL
            if economy.CIRCULATION_FREEZE_ENABLED and not index.is_price_frozen:
                self._freeze_price(index)
        elif total_circulation < threshold:
            # Low - below threshold
            index.circulation_status = CirculationStatus.LOW
            if economy.CIRCULATION_FREEZE_ENABLED and not index.is_price_frozen:
                self._freeze_price(index)
        elif total_circulation < threshold * Decimal("1.5"):
            # Recovering but still monitoring
            if index.circulation_status in (CirculationStatus.CRITICAL, CirculationStatus.FROZEN):
                index.circulation_status = CirculationStatus.LOW
        else:
            # Healthy
            if index.is_price_frozen:
                self._unfreeze_price(index)
            index.circulation_status = CirculationStatus.HEALTHY

    def _freeze_price(self, index: MarketIndex) -> None:
        """Freeze price at current level"""
        index.is_price_frozen = True
        index.frozen_price = index.carat_price_diamonds
        index.circulation_status = CirculationStatus.FROZEN

        # Create alert
        self._create_alert(
            alert_type="price_freeze",
            severity="warning",
            message="Price frozen due to low circulation",
            trigger_value=Decimal(index.carat_price_diamonds),
        )

    def _unfreeze_price(self, index: MarketIndex) -> None:
        """Unfreeze price"""
        index.is_price_frozen = False
        index.frozen_price = None

        self._create_alert(
            alert_type="price_unfreeze",
            severity="info",
            message="Price unfrozen - circulation restored to healthy levels",
        )

    def force_freeze(self, price: Optional[Decimal] = None) -> MarketIndex:
        """Manually freeze price (Head Banker only)"""
        index = self.get_market_index()
        index.is_price_frozen = True
        index.frozen_price = price or index.carat_price_diamonds
        return index

    def force_unfreeze(self) -> MarketIndex:
        """Manually unfreeze price (Head Banker only)"""
        index = self.get_market_index()
        index.is_price_frozen = False
        index.frozen_price = None
        return index

    # ==================== SNAPSHOTS ====================

    def create_snapshot(self, interval_type: str = "hour") -> MarketSnapshot:
        """Create a market snapshot"""
        index = self.get_market_index()
        treasury = self.db.query(Treasury).first()

        # Get OHLC data from recent transactions
        last_snapshot = (
            self.db.query(MarketSnapshot).order_by(desc(MarketSnapshot.snapshot_time)).first()
        )

        open_price = (
            Decimal(last_snapshot.close_price)
            if last_snapshot
            else Decimal(index.carat_price_diamonds)
        )
        current_price = Decimal(index.carat_price_diamonds)

        # Simplified OHLC - in production you'd track highs/lows
        snapshot = MarketSnapshot(
            index_value=index.current_index,
            delayed_average=index.delayed_average,
            carat_price=current_price,
            open_price=open_price,
            high_price=max(open_price, current_price),
            low_price=min(open_price, current_price),
            close_price=current_price,
            volume=index.volume_24h,
            transaction_count=index.transaction_count_24h,
            total_circulation=treasury.total_circulation_in_carats if treasury else Decimal("0"),
            circulation_status=index.circulation_status,
            book_value=treasury.book_value if treasury else Decimal("1"),
            reserve_ratio=treasury.reserve_ratio if treasury else Decimal("0"),
            interval_type=interval_type,
        )
        self.db.add(snapshot)
        return snapshot

    def get_snapshots(
        self, interval_type: str = "hour", days: int = 30, limit: int = 720
    ) -> List[MarketSnapshot]:
        """Get market snapshots for charting"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.snapshot_time >= cutoff,
                MarketSnapshot.interval_type == interval_type,
            )
            .order_by(MarketSnapshot.snapshot_time)
            .limit(limit)
            .all()
        )

    def get_price_history(self, days: int = 7) -> List[dict]:
        """Get simplified price history for charting"""
        snapshots = self.get_snapshots(interval_type="hour", days=days)

        return [
            {
                "timestamp": s.snapshot_time.isoformat(),
                "price": float(s.carat_price),
                "index": float(s.index_value),
                "volume": float(s.volume),
            }
            for s in snapshots
        ]

    # ==================== ALERTS ====================

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        trigger_value: Optional[Decimal] = None,
        threshold_value: Optional[Decimal] = None,
    ) -> MarketAlert:
        """Create a market alert"""
        alert = MarketAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            trigger_value=trigger_value,
            threshold_value=threshold_value,
        )
        self.db.add(alert)
        return alert

    def get_active_alerts(self) -> List[MarketAlert]:
        """Get all active alerts"""
        return (
            self.db.query(MarketAlert)
            .filter(MarketAlert.is_active == True)
            .order_by(desc(MarketAlert.created_at))
            .all()
        )

    def acknowledge_alert(self, alert_id: int) -> Optional[MarketAlert]:
        """Acknowledge an alert"""
        alert = self.db.query(MarketAlert).filter(MarketAlert.id == alert_id).first()
        if alert:
            alert.acknowledged_at = datetime.utcnow()
        return alert

    def resolve_alert(self, alert_id: int) -> Optional[MarketAlert]:
        """Resolve an alert"""
        alert = self.db.query(MarketAlert).filter(MarketAlert.id == alert_id).first()
        if alert:
            alert.is_active = False
            alert.resolved_at = datetime.utcnow()
        return alert
