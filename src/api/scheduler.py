"""
Market Scheduler
Background tasks for market updates, snapshots, and monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable, Optional

from ..config import economy
from ..models.base import get_db
from ..services.market_service import MarketService
from ..services.treasury_service import TreasuryService

logger = logging.getLogger(__name__)


class MarketScheduler:
    """
    Handles scheduled background tasks for market operations
    - Market index refresh every X minutes
    - Treasury snapshots
    - Circulation monitoring
    - Book value updates
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[Thread] = None
        self._callbacks: dict = {
            "on_price_freeze": [],
            "on_price_unfreeze": [],
            "on_alert": [],
            "on_refresh": [],
        }

    def start(self):
        """Start the scheduler in a background thread"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Market scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Market scheduler stopped")

    def add_callback(self, event: str, callback: Callable):
        """Add a callback for scheduler events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _run_loop(self):
        """Main scheduler loop"""
        last_refresh = datetime.min
        last_snapshot_minute = datetime.min
        last_snapshot_hour = datetime.min
        last_snapshot_day = datetime.min

        while self._running:
            try:
                now = datetime.utcnow()

                # Market refresh every X minutes
                if (
                    now - last_refresh
                ).total_seconds() >= economy.MARKET_REFRESH_INTERVAL_MINUTES * 60:
                    self._refresh_market()
                    last_refresh = now

                # Minute snapshot (for high-frequency data)
                if (now - last_snapshot_minute).total_seconds() >= 60:
                    self._create_snapshot("minute")
                    last_snapshot_minute = now

                # Hourly snapshot
                if (now - last_snapshot_hour).total_seconds() >= 3600:
                    self._create_snapshot("hour")
                    last_snapshot_hour = now

                # Daily snapshot
                if (now - last_snapshot_day).total_seconds() >= 86400:
                    self._create_snapshot("day")
                    self._create_treasury_snapshot()
                    last_snapshot_day = now

                # Sleep for 10 seconds between checks
                time.sleep(10)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(30)  # Back off on error

    def _refresh_market(self):
        """Refresh market index and check conditions"""
        try:
            with get_db() as db:
                treasury_service = TreasuryService(db)
                market_service = MarketService(db)

                # Recalculate book value
                book_value = treasury_service.recalculate_book_value()

                # Update market price
                market_service.update_price_from_book_value(book_value)

                # Refresh market index
                old_frozen = market_service.get_market_index().is_price_frozen
                index = market_service.refresh_market_index()
                new_frozen = index.is_price_frozen

                # Trigger callbacks
                for cb in self._callbacks["on_refresh"]:
                    try:
                        cb({"book_value": float(book_value), "index": float(index.current_index)})
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

                # Check for freeze/unfreeze events
                if new_frozen and not old_frozen:
                    for cb in self._callbacks["on_price_freeze"]:
                        try:
                            cb({"frozen_price": float(index.frozen_price)})
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                elif not new_frozen and old_frozen:
                    for cb in self._callbacks["on_price_unfreeze"]:
                        try:
                            cb({"current_price": float(index.carat_price_diamonds)})
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                logger.debug(
                    f"Market refreshed: index={index.current_index}, book_value={book_value}"
                )

        except Exception as e:
            logger.error(f"Market refresh failed: {e}")

    def _create_snapshot(self, interval_type: str):
        """Create a market snapshot"""
        try:
            with get_db() as db:
                market_service = MarketService(db)
                market_service.create_snapshot(interval_type)
                logger.debug(f"Created {interval_type} snapshot")
        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")

    def _create_treasury_snapshot(self):
        """Create a treasury snapshot"""
        try:
            with get_db() as db:
                treasury_service = TreasuryService(db)
                treasury_service.create_snapshot()
                logger.debug("Created treasury snapshot")
        except Exception as e:
            logger.error(f"Treasury snapshot failed: {e}")

    def force_refresh(self):
        """Manually trigger a market refresh"""
        self._refresh_market()

    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            "running": self._running,
            "refresh_interval_minutes": economy.MARKET_REFRESH_INTERVAL_MINUTES,
            "average_window_hours": economy.MARKET_AVERAGE_WINDOW_HOURS,
        }


# Global scheduler instance
_scheduler: Optional[MarketScheduler] = None


def get_scheduler() -> MarketScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = MarketScheduler()
    return _scheduler


def start_scheduler() -> MarketScheduler:
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
