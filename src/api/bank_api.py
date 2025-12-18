"""
Arca Bank API
Main unified interface for all banking operations
This is the primary class Discord bots should interact with
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple, Union

from ..models.base import get_db, init_db
from ..models.currency import CurrencyType
from ..models.trade import ItemCategory, TradeType
from ..models.treasury import TransactionType
from ..models.user import User, UserRole
from ..services.chart_service import ChartService
from ..services.currency_service import CurrencyService
from ..services.market_service import MarketService
from ..services.mint_service import MintService
from ..services.trade_service import TradeService
from ..services.treasury_service import TreasuryService
from ..services.user_service import UserService


@dataclass
class OperationResult:
    """Standard result wrapper for API operations"""

    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None


class ArcaBank:
    """
    Main API for Arca Bank operations
    All Discord bot commands should go through this class
    """

    def __init__(self):
        """Initialize the bank API"""
        init_db()

    # ==================== USER OPERATIONS ====================

    def register_user(
        self,
        discord_id: str,
        discord_username: str,
        minecraft_uuid: Optional[str] = None,
        minecraft_username: Optional[str] = None,
    ) -> OperationResult:
        """Register a new user or get existing user"""
        try:
            with get_db() as db:
                service = UserService(db)
                user = service.get_or_create_user(discord_id, discord_username)

                if minecraft_uuid and not user.minecraft_uuid:
                    service.link_minecraft(user, minecraft_uuid, minecraft_username)

                return OperationResult(
                    success=True,
                    message=f"Welcome to Arca Bank, {discord_username}!",
                    data={
                        "user_id": user.id,
                        "discord_id": user.discord_id,
                        "discord_username": user.discord_username,
                        "minecraft_uuid": user.minecraft_uuid,
                        "minecraft_username": user.minecraft_username,
                        "role": user.role.value,
                        "is_linked": user.minecraft_uuid is not None,
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to register user", error=str(e))

    def link_minecraft(
        self, discord_id: str, minecraft_uuid: str, minecraft_username: str
    ) -> OperationResult:
        """Link a Minecraft account to a Discord user"""
        try:
            with get_db() as db:
                service = UserService(db)
                user = service.get_by_discord_id(discord_id)

                if not user:
                    return OperationResult(
                        success=False, message="User not found. Please register first."
                    )

                service.link_minecraft(user, minecraft_uuid, minecraft_username)

                return OperationResult(
                    success=True,
                    message=f"Successfully linked Minecraft account: {minecraft_username}",
                    data={
                        "minecraft_username": minecraft_username,
                        "minecraft_uuid": minecraft_uuid,
                    },
                )
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Failed to link account", error=str(e))

    def get_user_info(self, discord_id: str) -> OperationResult:
        """Get user information and balances"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                balances = currency_service.get_user_balances(user)

                return OperationResult(
                    success=True,
                    message="User info retrieved",
                    data={
                        "discord_username": user.discord_username,
                        "minecraft_username": user.minecraft_username,
                        "role": user.role.value,
                        "carats": float(balances["carats"]),
                        "golden_carats": float(balances["golden_carats"]),
                        "total_value_carats": float(balances["total_in_carats"]),
                        "is_banker": user.is_banker,
                        "is_head_banker": user.is_head_banker,
                        "member_since": user.created_at.isoformat(),
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get user info", error=str(e))

    # ==================== BALANCE OPERATIONS ====================

    def get_balance(self, discord_id: str) -> OperationResult:
        """Get user's currency balances"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                balances = currency_service.get_user_balances(user)

                return OperationResult(
                    success=True,
                    message="Balance retrieved",
                    data={
                        "carats": float(balances["carats"]),
                        "golden_carats": float(balances["golden_carats"]),
                        "total_in_carats": float(balances["total_in_carats"]),
                        "role": user.role.name.lower(),
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get balance", error=str(e))

    def transfer(
        self,
        sender_discord_id: str,
        recipient_discord_id: str,
        amount: float,
        currency: str = "carat",
    ) -> OperationResult:
        """Transfer currency between users"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)
                treasury_service = TreasuryService(db)

                sender = user_service.get_by_discord_id(sender_discord_id)
                recipient = user_service.get_by_discord_id(recipient_discord_id)

                if not sender:
                    return OperationResult(success=False, message="Sender not found")
                if not recipient:
                    return OperationResult(success=False, message="Recipient not found")

                currency_type = (
                    CurrencyType.GOLDEN_CARAT
                    if currency.lower() == "golden_carat"
                    else CurrencyType.CARAT
                )
                amount_decimal = Decimal(str(amount))

                received, fee = currency_service.transfer(
                    sender, recipient, currency_type, amount_decimal
                )

                # Collect fee for treasury
                if fee > 0:
                    treasury_service.collect_fee(fee, TransactionType.FEE_COLLECTION, sender)

                return OperationResult(
                    success=True,
                    message=f"Transferred {float(received):.2f} {currency_type.value} to {recipient.discord_username}",
                    data={
                        "amount_sent": float(amount_decimal),
                        "amount_received": float(received),
                        "fee": float(fee),
                        "currency": currency_type.value,
                        "recipient": recipient.discord_username,
                    },
                )
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Transfer failed", error=str(e))

    def exchange_currency(
        self, discord_id: str, amount: float, from_currency: str, to_currency: str
    ) -> OperationResult:
        """Exchange between Carats and Golden Carats"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)
                treasury_service = TreasuryService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                from_type = (
                    CurrencyType.GOLDEN_CARAT
                    if "golden" in from_currency.lower()
                    else CurrencyType.CARAT
                )
                to_type = (
                    CurrencyType.GOLDEN_CARAT
                    if "golden" in to_currency.lower()
                    else CurrencyType.CARAT
                )

                received, fee, exchange = currency_service.exchange_currency(
                    user, from_type, to_type, Decimal(str(amount))
                )

                # Collect exchange fee
                if fee > 0:
                    treasury_service.collect_fee(fee, TransactionType.EXCHANGE_FEE, user)

                return OperationResult(
                    success=True,
                    message=f"Exchanged {amount:.2f} {from_type.value} for {float(received):.2f} {to_type.value}",
                    data={
                        "from_amount": float(amount),
                        "from_currency": from_type.value,
                        "to_amount": float(received),
                        "to_currency": to_type.value,
                        "fee": float(fee),
                        "exchange_rate": 9,  # 1 golden = 9 carats
                    },
                )
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Exchange failed", error=str(e))

    # ==================== TREASURY OPERATIONS ====================

    def get_treasury_status(self) -> OperationResult:
        """Get current treasury status (public read)"""
        try:
            with get_db() as db:
                treasury_service = TreasuryService(db)
                status = treasury_service.get_treasury_status()

                return OperationResult(
                    success=True,
                    message="Treasury status retrieved",
                    data={
                        "total_diamonds": float(status["total_diamonds"]),
                        "reserve_diamonds": float(status["reserve_diamonds"]),
                        "total_carats_minted": float(status["total_carats_minted"]),
                        "total_golden_carats_minted": float(status["total_golden_carats_minted"]),
                        "total_circulation": float(status["total_circulation_in_carats"]),
                        "book_value": float(status["book_value"]),
                        "reserve_ratio": float(status["reserve_ratio"]) * 100,
                        "total_books": status["total_books"],
                        "accumulated_fees": float(status["accumulated_fees"]),
                        "last_updated": (
                            status["last_updated"].isoformat() if status["last_updated"] else None
                        ),
                    },
                )
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to get treasury status", error=str(e)
            )

    def get_treasury_history(self, days: int = 30, limit: int = 50) -> OperationResult:
        """Get treasury transaction history"""
        try:
            with get_db() as db:
                treasury_service = TreasuryService(db)

                inflow_outflow = treasury_service.get_inflow_outflow(days)
                transactions = treasury_service.get_transaction_history(limit=limit)

                return OperationResult(
                    success=True,
                    message="Treasury history retrieved",
                    data={
                        "summary": {
                            "period_days": inflow_outflow["period_days"],
                            "inflow_diamonds": float(inflow_outflow["inflow_diamonds"]),
                            "outflow_diamonds": float(inflow_outflow["outflow_diamonds"]),
                            "net_diamonds": float(inflow_outflow["net_diamonds"]),
                            "inflow_carats": float(inflow_outflow["inflow_carats"]),
                            "outflow_carats": float(inflow_outflow["outflow_carats"]),
                            "net_carats": float(inflow_outflow["net_carats"]),
                            "total_fees": float(inflow_outflow["total_fees_collected"]),
                            "transaction_count": inflow_outflow["transaction_count"],
                        },
                        "transactions": [
                            {
                                "type": tx.transaction_type.value,
                                "diamonds": float(tx.diamond_amount),
                                "carats": float(tx.carat_amount),
                                "fee": float(tx.fee_amount),
                                "book_value_after": float(tx.book_value_after),
                                "timestamp": tx.created_at.isoformat(),
                                "notes": tx.notes,
                            }
                            for tx in transactions
                        ],
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get history", error=str(e))

    # ==================== BANKER OPERATIONS (Write Permission) ====================

    def deposit(
        self,
        banker_discord_id: str,
        user_discord_id: str,
        diamonds: float,
        carats_to_issue: float,
        notes: Optional[str] = None,
    ) -> OperationResult:
        """Deposit diamonds and issue carats (Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                treasury_service = TreasuryService(db)

                banker = user_service.get_by_discord_id(banker_discord_id)
                if not banker or not banker.can_write():
                    return OperationResult(success=False, message="Banker permission required")

                user = user_service.get_by_discord_id(user_discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                transaction = treasury_service.deposit_diamonds(
                    user, Decimal(str(diamonds)), Decimal(str(carats_to_issue)), notes
                )

                return OperationResult(
                    success=True,
                    message=f"Deposited {diamonds}◆ and issued {carats_to_issue} carats to {user.discord_username}",
                    data={
                        "diamonds_deposited": float(diamonds),
                        "carats_issued": float(carats_to_issue),
                        "new_book_value": float(transaction.book_value_after),
                        "recipient": user.discord_username,
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Deposit failed", error=str(e))

    def record_atm_profit(
        self, banker_discord_id: str, book_count: int, notes: Optional[str] = None
    ) -> OperationResult:
        """Record ATM profit at 90 diamonds per book (Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                treasury_service = TreasuryService(db)

                banker = user_service.get_by_discord_id(banker_discord_id)
                if not banker or not banker.can_write():
                    return OperationResult(success=False, message="Banker permission required")

                transaction = treasury_service.record_atm_profit(banker, book_count, notes)

                diamond_amount = book_count * 90

                return OperationResult(
                    success=True,
                    message=f"Recorded ATM profit: {book_count} books = {diamond_amount}◆",
                    data={
                        "books": book_count,
                        "diamonds": diamond_amount,
                        "new_book_value": float(transaction.book_value_after),
                        "total_books_in_circulation": transaction.book_count,
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to record ATM profit", error=str(e)
            )

    # ==================== HEAD BANKER OPERATIONS (Admin Permission) ====================

    def mint_check(self, admin_discord_id: str, atm_books_received: int = 0) -> OperationResult:
        """Get minting/burning recommendation (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                mint_service = MintService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.can_mint():
                    return OperationResult(success=False, message="Head Banker permission required")

                recommendation = mint_service.mint_check(atm_books_received)

                return OperationResult(
                    success=True,
                    message=f"Mint Check Complete - Recommendation: {recommendation.action.upper()}",
                    data={
                        "action": recommendation.action,
                        "amount": float(recommendation.amount),
                        "reason": recommendation.reason,
                        "confidence": recommendation.confidence,
                        "current_book_value": float(recommendation.current_book_value),
                        "target_book_value": float(recommendation.target_book_value),
                        "current_circulation": float(recommendation.current_circulation),
                        "projected_book_value": float(recommendation.projected_book_value),
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Mint check failed", error=str(e))

    def mint(
        self,
        admin_discord_id: str,
        amount: float,
        currency: str = "carat",
        notes: Optional[str] = None,
    ) -> OperationResult:
        """Mint new currency (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                mint_service = MintService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.can_mint():
                    return OperationResult(success=False, message="Head Banker permission required")

                currency_type = (
                    CurrencyType.GOLDEN_CARAT
                    if "golden" in currency.lower()
                    else CurrencyType.CARAT
                )

                transaction = mint_service.mint_carats(
                    admin, Decimal(str(amount)), currency_type, notes
                )

                return OperationResult(
                    success=True,
                    message=f"Minted {amount:.2f} {currency_type.value}",
                    data={
                        "amount": float(amount),
                        "currency": currency_type.value,
                        "new_book_value": float(transaction.book_value_after),
                    },
                )
        except (PermissionError, ValueError) as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Minting failed", error=str(e))

    def burn(
        self,
        admin_discord_id: str,
        amount: float,
        currency: str = "carat",
        notes: Optional[str] = None,
    ) -> OperationResult:
        """Burn currency from supply (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                mint_service = MintService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.can_mint():
                    return OperationResult(success=False, message="Head Banker permission required")

                currency_type = (
                    CurrencyType.GOLDEN_CARAT
                    if "golden" in currency.lower()
                    else CurrencyType.CARAT
                )

                transaction = mint_service.burn_carats(
                    admin, Decimal(str(amount)), currency_type, notes
                )

                return OperationResult(
                    success=True,
                    message=f"Burned {amount:.2f} {currency_type.value}",
                    data={
                        "amount": float(amount),
                        "currency": currency_type.value,
                        "new_book_value": float(transaction.book_value_after),
                    },
                )
        except (PermissionError, ValueError) as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Burning failed", error=str(e))

    def promote_to_banker(self, admin_discord_id: str, user_discord_id: str) -> OperationResult:
        """Promote user to banker role (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin:
                    return OperationResult(success=False, message="Admin not found")

                user = user_service.get_by_discord_id(user_discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                user_service.promote_to_banker(user, admin)

                return OperationResult(
                    success=True,
                    message=f"Promoted {user.discord_username} to Banker",
                    data={"user": user.discord_username, "new_role": "banker"},
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Promotion failed", error=str(e))

    def resign_as_banker(self, discord_id: str) -> OperationResult:
        """
        Allow a banker to voluntarily resign their position.
        Returns to regular USER role.
        """
        try:
            with get_db() as db:
                user_service = UserService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                user_service.resign_as_banker(user)

                return OperationResult(
                    success=True,
                    message=f"{user.discord_username} has resigned as Banker",
                    data={"user": user.discord_username, "new_role": "user"},
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Resignation failed", error=str(e))

    # ==================== MARKET OPERATIONS ====================

    def get_market_status(self) -> OperationResult:
        """Get current market status"""
        try:
            with get_db() as db:
                market_service = MarketService(db)
                status = market_service.get_market_status()

                return OperationResult(
                    success=True,
                    message="Market status retrieved",
                    data={
                        "current_index": float(status["current_index"]),
                        "delayed_average": float(status["delayed_average"]),
                        "carat_price": float(status["carat_price"]),
                        "effective_price": float(status["effective_price"]),
                        "circulation_status": status["circulation_status"],
                        "is_price_frozen": status["is_price_frozen"],
                        "frozen_price": (
                            float(status["frozen_price"]) if status["frozen_price"] else None
                        ),
                        "volume_24h": float(status["volume_24h"]),
                        "transaction_count_24h": status["transaction_count_24h"],
                        "change_1h": float(status["change_1h"]),
                        "change_24h": float(status["change_24h"]),
                        "change_7d": float(status["change_7d"]),
                        "total_circulation": float(status["total_circulation"]),
                    },
                )
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to get market status", error=str(e)
            )

    def get_market_chart(
        self, days: int = 7, chart_type: str = "line"
    ) -> Union[bytes, OperationResult]:
        """Generate market chart image"""
        try:
            with get_db() as db:
                chart_service = ChartService(db)
                return chart_service.generate_market_chart(days=days, chart_type=chart_type)
        except Exception as e:
            return OperationResult(success=False, message="Failed to generate chart", error=str(e))

    def get_advanced_chart(
        self,
        days: int = 30,
        show_volume: bool = True,
        show_rsi: bool = True,
        show_bollinger: bool = True,
        show_ma: bool = True,
        chart_type: str = "candlestick",
    ) -> Union[bytes, OperationResult]:
        """
        Generate advanced stock-style chart with technical indicators

        Features:
        - Candlestick or line chart
        - Moving averages (7-day, 21-day)
        - Bollinger Bands
        - RSI indicator
        - Volume bars
        """
        try:
            with get_db() as db:
                chart_service = ChartService(db)
                return chart_service.generate_advanced_chart(
                    days=days,
                    show_volume=show_volume,
                    show_rsi=show_rsi,
                    show_bollinger=show_bollinger,
                    show_ma=show_ma,
                    chart_type=chart_type,
                )
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to generate advanced chart", error=str(e)
            )

    def get_multi_timeframe_chart(self) -> Union[bytes, OperationResult]:
        """
        Generate multi-timeframe overview chart
        Shows 1D, 7D, 30D, and 90D performance at a glance
        """
        try:
            with get_db() as db:
                chart_service = ChartService(db)
                return chart_service.generate_multi_timeframe_chart()
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to generate timeframe chart", error=str(e)
            )

    def get_treasury_chart(self, days: int = 30) -> Union[bytes, OperationResult]:
        """Generate treasury health chart"""
        try:
            with get_db() as db:
                chart_service = ChartService(db)
                return chart_service.generate_treasury_chart(days=days)
        except Exception as e:
            return OperationResult(success=False, message="Failed to generate chart", error=str(e))

    def get_sparkline(self, days: int = 7) -> Union[bytes, OperationResult]:
        """Generate small sparkline chart"""
        try:
            with get_db() as db:
                chart_service = ChartService(db)
                return chart_service.generate_mini_sparkline(days=days)
        except Exception as e:
            return OperationResult(
                success=False, message="Failed to generate sparkline", error=str(e)
            )

    # ==================== ADMIN MARKET CONTROLS ====================

    def freeze_price(self, admin_discord_id: str, price: Optional[float] = None) -> OperationResult:
        """Manually freeze price (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                market_service = MarketService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.can_mint():
                    return OperationResult(success=False, message="Head Banker permission required")

                index = market_service.force_freeze(Decimal(str(price)) if price else None)

                return OperationResult(
                    success=True,
                    message=f"Price frozen at {float(index.frozen_price):.4f}◆/carat",
                    data={"frozen_price": float(index.frozen_price)},
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to freeze price", error=str(e))

    def unfreeze_price(self, admin_discord_id: str) -> OperationResult:
        """Manually unfreeze price (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                market_service = MarketService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.can_mint():
                    return OperationResult(success=False, message="Head Banker permission required")

                index = market_service.force_unfreeze()

                return OperationResult(
                    success=True,
                    message="Price unfrozen - market prices now active",
                    data={"current_price": float(index.carat_price_diamonds)},
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to unfreeze price", error=str(e))

    # ==================== TRADE REPORTING ====================

    def report_trade(
        self,
        discord_id: str,
        trade_type: str,
        item_name: str,
        item_quantity: int,
        carat_amount: float,
        golden_carat_amount: float = 0.0,
        item_category: str = "OTHER",
        counterparty_name: Optional[str] = None,
        world_name: Optional[str] = None,
        location: Optional[Tuple[int, int, int]] = None,
        notes: Optional[str] = None,
    ) -> OperationResult:
        """
        Report a trade from in-game or Discord

        Args:
            discord_id: Discord ID of the reporter
            trade_type: "BUY", "SELL", or "EXCHANGE"
            item_name: Name of item(s) traded
            item_quantity: Quantity of items
            carat_amount: Carats involved
            golden_carat_amount: Golden carats involved
            item_category: Category for analytics
            counterparty_name: Name of other party
            world_name: Minecraft world name
            location: (x, y, z) coordinates
            notes: Additional notes
        """
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                if not user.can_trade():
                    return OperationResult(
                        success=False, message="Consumer accounts cannot report trades"
                    )

                # Parse trade type
                try:
                    tt = TradeType(trade_type.upper())
                except ValueError:
                    return OperationResult(
                        success=False, message="Invalid trade type. Use: BUY, SELL, or EXCHANGE"
                    )

                # Parse category
                try:
                    cat = ItemCategory(item_category.upper())
                except ValueError:
                    cat = ItemCategory.OTHER

                trade = trade_service.report_trade(
                    reporter=user,
                    trade_type=tt,
                    item_name=item_name,
                    item_quantity=item_quantity,
                    carat_amount=Decimal(str(carat_amount)),
                    golden_carat_amount=Decimal(str(golden_carat_amount)),
                    item_category=cat,
                    counterparty_name=counterparty_name,
                    world_name=world_name,
                    location=location,
                    notes=notes,
                )

                return OperationResult(
                    success=True,
                    message=f"Trade #{trade.id} reported: {tt.value} {item_quantity}x {item_name}",
                    data={
                        "trade_id": trade.id,
                        "trade_type": trade.trade_type.value,
                        "item_name": trade.item_name,
                        "item_quantity": trade.item_quantity,
                        "carat_amount": float(trade.carat_amount),
                        "golden_carat_amount": float(trade.golden_carat_amount),
                        "price_per_item": float(trade.price_per_item),
                        "timestamp": trade.reported_at.isoformat(),
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except ValueError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Failed to report trade", error=str(e))

    def report_trade_by_uuid(
        self,
        minecraft_uuid: str,
        trade_type: str,
        item_name: str,
        item_quantity: int,
        carat_amount: float,
        golden_carat_amount: float = 0.0,
        item_category: str = "OTHER",
        counterparty_name: Optional[str] = None,
        world_name: Optional[str] = None,
        location: Optional[Tuple[int, int, int]] = None,
        notes: Optional[str] = None,
    ) -> OperationResult:
        """Report a trade using Minecraft UUID (for Java mod)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_minecraft_uuid(minecraft_uuid)
                if not user:
                    return OperationResult(success=False, message="Player not found")

                if not user.can_trade():
                    return OperationResult(
                        success=False, message="Consumer accounts cannot report trades"
                    )

                try:
                    tt = TradeType(trade_type.upper())
                except ValueError:
                    return OperationResult(success=False, message="Invalid trade type")

                try:
                    cat = ItemCategory(item_category.upper())
                except ValueError:
                    cat = ItemCategory.OTHER

                trade = trade_service.report_trade(
                    reporter=user,
                    trade_type=tt,
                    item_name=item_name,
                    item_quantity=item_quantity,
                    carat_amount=Decimal(str(carat_amount)),
                    golden_carat_amount=Decimal(str(golden_carat_amount)),
                    item_category=cat,
                    counterparty_name=counterparty_name,
                    world_name=world_name,
                    location=location,
                    notes=notes,
                )

                return OperationResult(
                    success=True,
                    message=f"Trade #{trade.id} reported",
                    data={
                        "trade_id": trade.id,
                        "trade_type": trade.trade_type.value,
                        "item_name": trade.item_name,
                        "item_quantity": trade.item_quantity,
                        "price_per_item": float(trade.price_per_item),
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to report trade", error=str(e))

    def get_my_trades(
        self, discord_id: str, limit: int = 20, trade_type: Optional[str] = None
    ) -> OperationResult:
        """Get user's recent trades"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                tt = None
                if trade_type:
                    try:
                        tt = TradeType(trade_type.upper())
                    except ValueError:
                        pass

                trades = trade_service.get_user_trades(user, limit=limit, trade_type=tt)

                return OperationResult(
                    success=True,
                    message=f"Found {len(trades)} trades",
                    data={
                        "trades": [
                            {
                                "id": t.id,
                                "type": t.trade_type.value,
                                "item": t.item_name,
                                "quantity": t.item_quantity,
                                "carats": float(t.carat_amount),
                                "golden_carats": float(t.golden_carat_amount),
                                "price_per_item": float(t.price_per_item),
                                "counterparty": t.counterparty_name,
                                "verified": t.is_verified,
                                "timestamp": t.reported_at.isoformat(),
                            }
                            for t in trades
                        ]
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get trades", error=str(e))

    def get_my_trader_stats(self, discord_id: str) -> OperationResult:
        """Get user's trading statistics"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_discord_id(discord_id)
                if not user:
                    return OperationResult(success=False, message="User not found")

                stats = trade_service.get_trader_stats(user)

                if not stats:
                    return OperationResult(
                        success=True, message="No trading history", data={"total_trades": 0}
                    )

                return OperationResult(
                    success=True,
                    message="Trader stats retrieved",
                    data={
                        "total_trades": stats.total_trades,
                        "buy_count": stats.buy_count,
                        "sell_count": stats.sell_count,
                        "total_volume": float(stats.total_volume_carats),
                        "average_trade_size": float(stats.average_trade_size),
                        "verified_trades": stats.verified_trade_count,
                        "reputation_score": float(stats.reputation_score),
                        "first_trade": (
                            stats.first_trade_at.isoformat() if stats.first_trade_at else None
                        ),
                        "last_trade": (
                            stats.last_trade_at.isoformat() if stats.last_trade_at else None
                        ),
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get stats", error=str(e))

    def verify_trade(self, banker_discord_id: str, trade_id: int) -> OperationResult:
        """Verify a trade (Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                banker = user_service.get_by_discord_id(banker_discord_id)
                if not banker or not banker.is_banker:
                    return OperationResult(success=False, message="Banker permission required")

                trade = trade_service.verify_trade(trade_id, banker)
                if not trade:
                    return OperationResult(success=False, message="Trade not found")

                return OperationResult(
                    success=True,
                    message=f"Trade #{trade_id} verified",
                    data={
                        "trade_id": trade.id,
                        "verified_by": banker.discord_username,
                        "verified_at": trade.verified_at.isoformat(),
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Failed to verify trade", error=str(e))

    def get_trader_report(self, admin_discord_id: str, target_discord_id: str) -> OperationResult:
        """Get comprehensive trader report (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.is_head_banker:
                    return OperationResult(success=False, message="Head Banker permission required")

                target = user_service.get_by_discord_id(target_discord_id)
                if not target:
                    return OperationResult(success=False, message="Target user not found")

                report = trade_service.get_trader_report(target, admin)

                return OperationResult(
                    success=True,
                    message=f"Trader report for {report.minecraft_username}",
                    data={
                        "user_id": report.user_id,
                        "minecraft_username": report.minecraft_username,
                        "discord_username": report.discord_username,
                        "role": report.role,
                        "total_trades": report.total_trades,
                        "buy_count": report.buy_count,
                        "sell_count": report.sell_count,
                        "total_volume": report.total_volume,
                        "average_trade_size": report.average_trade_size,
                        "first_trade": report.first_trade,
                        "last_trade": report.last_trade,
                        "verified_trades": report.verified_trades,
                        "reputation_score": report.reputation_score,
                        "recent_trades": report.recent_trades,
                    },
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Failed to get report", error=str(e))

    def get_all_trader_reports(self, admin_discord_id: str, limit: int = 50) -> OperationResult:
        """Get summary reports for all traders (Head Banker only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.is_head_banker:
                    return OperationResult(success=False, message="Head Banker permission required")

                reports = trade_service.get_all_trader_reports(admin, limit)

                return OperationResult(
                    success=True, message=f"Found {len(reports)} traders", data={"traders": reports}
                )
        except PermissionError as e:
            return OperationResult(success=False, message=str(e))
        except Exception as e:
            return OperationResult(success=False, message="Failed to get reports", error=str(e))

    def get_top_traders(self, limit: int = 10, days: int = 30) -> OperationResult:
        """Get top traders by volume"""
        try:
            with get_db() as db:
                trade_service = TradeService(db)
                traders = trade_service.get_top_traders(limit, days)

                return OperationResult(
                    success=True, message=f"Top {len(traders)} traders", data={"traders": traders}
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get top traders", error=str(e))

    def get_item_price(self, item_name: str) -> OperationResult:
        """Get current market price for an item"""
        try:
            with get_db() as db:
                trade_service = TradeService(db)
                price = trade_service.get_item_price(item_name)

                if not price:
                    return OperationResult(
                        success=True,
                        message=f"No price data for {item_name}",
                        data={"found": False},
                    )

                return OperationResult(
                    success=True,
                    message=f"Price for {item_name}",
                    data={
                        "found": True,
                        "item_name": price.item_name,
                        "category": price.item_category.value,
                        "current_price": float(price.current_price),
                        "trade_count_24h": price.trade_count_24h,
                        "volume_24h": float(price.volume_24h),
                        "last_trade": (
                            price.last_trade_at.isoformat() if price.last_trade_at else None
                        ),
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get price", error=str(e))

    def get_trending_items(self, limit: int = 10) -> OperationResult:
        """Get items with highest trading volume"""
        try:
            with get_db() as db:
                trade_service = TradeService(db)
                items = trade_service.get_trending_items(limit)

                return OperationResult(
                    success=True,
                    message=f"Top {len(items)} trending items",
                    data={
                        "items": [
                            {
                                "item_name": item.item_name,
                                "category": item.item_category.value,
                                "current_price": float(item.current_price),
                                "trade_count_24h": item.trade_count_24h,
                                "volume_24h": float(item.volume_24h),
                            }
                            for item in items
                        ]
                    },
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get trending", error=str(e))

    # ==================== ROLE MANAGEMENT ====================

    def set_consumer(self, admin_discord_id: str, target_discord_id: str) -> OperationResult:
        """Set a user to Consumer role (read-only)"""
        try:
            with get_db() as db:
                user_service = UserService(db)

                admin = user_service.get_by_discord_id(admin_discord_id)
                if not admin or not admin.is_head_banker:
                    return OperationResult(success=False, message="Head Banker permission required")

                target = user_service.get_by_discord_id(target_discord_id)
                if not target:
                    return OperationResult(success=False, message="User not found")

                target.role = UserRole.CONSUMER

                return OperationResult(
                    success=True,
                    message=f"{target.discord_username} set to Consumer (read-only)",
                    data={"username": target.discord_username, "role": "consumer"},
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to set role", error=str(e))

    def get_leaderboard(self, limit: int = 10) -> OperationResult:
        """Get wealth leaderboard - top users by total value"""
        try:
            with get_db() as db:
                currency_service = CurrencyService(db)

                # Get all users
                users = db.query(User).filter(User.role != UserRole.CONSUMER).all()

                # Calculate total value for each user
                user_values = []
                for user in users:
                    balances = currency_service.get_user_balances(user)
                    total_value = float(balances["total_in_carats"])
                    if total_value > 0:  # Only include users with balance
                        user_values.append(
                            {
                                "username": user.minecraft_username or user.discord_username,
                                "discord_id": user.discord_id,
                                "carats": float(balances["carats"]),
                                "golden_carats": float(balances["golden_carats"]),
                                "total_value": total_value,
                            }
                        )

                # Sort by total value descending
                user_values.sort(key=lambda x: x["total_value"], reverse=True)

                return OperationResult(
                    success=True,
                    message=f"Top {min(limit, len(user_values))} users by wealth",
                    data={"users": user_values[:limit]},
                )
        except Exception as e:
            return OperationResult(success=False, message="Failed to get leaderboard", error=str(e))
