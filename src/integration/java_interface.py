"""
Java Mod Integration Interface
REST API endpoints for Minecraft mod integration
"""

from dataclasses import asdict
from decimal import Decimal
from typing import Optional

from ..api.bank_api import ArcaBank, OperationResult

# This module provides a JSON-based interface for Java mod integration
# Can be used with FastAPI, Flask, or any other web framework



class JavaModInterface:
    """
    Interface for Java Minecraft mod to communicate with Arca Bank
    All methods return JSON-serializable dictionaries
    """

    def __init__(self):
        self.bank = ArcaBank()

    def get_balance_by_uuid(self, minecraft_uuid: str) -> dict:
        """
        Get player balance by Minecraft UUID

        Args:
            minecraft_uuid: Player's Minecraft UUID

        Returns:
            {"success": bool, "carats": float, "golden_carats": float, "total": float}
        """
        from ..models.base import get_db
        from ..services.currency_service import CurrencyService
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)

                user = user_service.get_by_minecraft_uuid(minecraft_uuid)
                if not user:
                    return {"success": False, "error": "Player not registered"}

                balances = currency_service.get_user_balances(user)

                return {
                    "success": True,
                    "minecraft_uuid": minecraft_uuid,
                    "minecraft_username": user.minecraft_username,
                    "carats": float(balances["carats"]),
                    "golden_carats": float(balances["golden_carats"]),
                    "total_in_carats": float(balances["total_in_carats"]),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def transfer_by_uuid(
        self, sender_uuid: str, recipient_uuid: str, amount: float, currency: str = "carat"
    ) -> dict:
        """
        Transfer currency between players using Minecraft UUIDs

        Args:
            sender_uuid: Sender's Minecraft UUID
            recipient_uuid: Recipient's Minecraft UUID
            amount: Amount to transfer
            currency: "carat" or "golden_carat"

        Returns:
            {"success": bool, "amount_sent": float, "amount_received": float, "fee": float}
        """
        from ..models.base import get_db
        from ..models.currency import CurrencyType
        from ..models.treasury import TransactionType
        from ..services.currency_service import CurrencyService
        from ..services.treasury_service import TreasuryService
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)
                currency_service = CurrencyService(db)
                treasury_service = TreasuryService(db)

                sender = user_service.get_by_minecraft_uuid(sender_uuid)
                recipient = user_service.get_by_minecraft_uuid(recipient_uuid)

                if not sender:
                    return {"success": False, "error": "Sender not registered"}
                if not recipient:
                    return {"success": False, "error": "Recipient not registered"}

                currency_type = (
                    CurrencyType.GOLDEN_CARAT
                    if currency.lower() == "golden_carat"
                    else CurrencyType.CARAT
                )

                received, fee = currency_service.transfer(
                    sender, recipient, currency_type, Decimal(str(amount))
                )

                if fee > 0:
                    treasury_service.collect_fee(fee, TransactionType.FEE_COLLECTION, sender)

                return {
                    "success": True,
                    "amount_sent": float(amount),
                    "amount_received": float(received),
                    "fee": float(fee),
                    "currency": currency_type.value,
                }
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_player(
        self, minecraft_uuid: str, minecraft_username: str, discord_id: Optional[str] = None
    ) -> dict:
        """
        Register a new player from in-game
        If discord_id is provided, links to existing Discord account

        Args:
            minecraft_uuid: Player's Minecraft UUID
            minecraft_username: Player's Minecraft username
            discord_id: Optional Discord ID to link

        Returns:
            {"success": bool, "message": str}
        """
        from ..models.base import get_db
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)

                # Check if already registered
                existing = user_service.get_by_minecraft_uuid(minecraft_uuid)
                if existing:
                    return {
                        "success": True,
                        "message": "Player already registered",
                        "user_id": existing.id,
                    }

                if discord_id:
                    # Link to existing Discord account
                    user = user_service.get_by_discord_id(discord_id)
                    if user:
                        user_service.link_minecraft(user, minecraft_uuid, minecraft_username)
                        return {
                            "success": True,
                            "message": f"Linked to Discord: {user.discord_username}",
                            "user_id": user.id,
                        }

                # Create new user with temporary Discord ID
                user = user_service.create_user(
                    discord_id=discord_id or f"mc_{minecraft_uuid}",
                    discord_username=minecraft_username,
                    minecraft_uuid=minecraft_uuid,
                    minecraft_username=minecraft_username,
                )

                return {
                    "success": True,
                    "message": "Player registered successfully",
                    "user_id": user.id,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_market_price(self) -> dict:
        """
        Get current market price for displaying in-game

        Returns:
            {"success": bool, "carat_price": float, "index": float, "status": str}
        """
        result = self.bank.get_market_status()

        if result.success:
            return {
                "success": True,
                "carat_price": result.data["effective_price"],
                "index": result.data["current_index"],
                "status": result.data["circulation_status"],
                "is_frozen": result.data["is_price_frozen"],
                "change_24h": result.data["change_24h"],
            }
        return {"success": False, "error": result.message}

    def get_treasury_info(self) -> dict:
        """
        Get treasury information for in-game display

        Returns:
            {"success": bool, "total_diamonds": float, "book_value": float, ...}
        """
        result = self.bank.get_treasury_status()

        if result.success:
            return {
                "success": True,
                "total_diamonds": result.data["total_diamonds"],
                "total_carats": result.data["total_carats_minted"],
                "total_golden_carats": result.data["total_golden_carats_minted"],
                "book_value": result.data["book_value"],
                "reserve_ratio": result.data["reserve_ratio"],
            }
        return {"success": False, "error": result.message}

    def check_is_banker(self, minecraft_uuid: str) -> dict:
        """
        Check if a player has banker permissions

        Args:
            minecraft_uuid: Player's Minecraft UUID

        Returns:
            {"success": bool, "is_banker": bool, "is_head_banker": bool}
        """
        from ..models.base import get_db
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)
                user = user_service.get_by_minecraft_uuid(minecraft_uuid)

                if not user:
                    return {"success": False, "error": "Player not registered"}

                return {
                    "success": True,
                    "is_banker": user.is_banker,
                    "is_head_banker": user.is_head_banker,
                    "is_consumer": user.is_consumer,
                    "can_trade": user.can_trade(),
                    "role": user.role.value,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== TRADE REPORTING ====================

    def report_trade(
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
        location_x: Optional[int] = None,
        location_y: Optional[int] = None,
        location_z: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Report a trade from in-game

        Args:
            minecraft_uuid: Reporter's Minecraft UUID
            trade_type: "BUY", "SELL", or "EXCHANGE"
            item_name: Name of item traded
            item_quantity: Quantity of items
            carat_amount: Carats involved
            golden_carat_amount: Golden carats involved
            item_category: Category for analytics
            counterparty_name: Name of other party
            world_name: Current world
            location_x/y/z: Player coordinates
            notes: Additional notes

        Returns:
            {"success": bool, "trade_id": int, ...}
        """
        location = None
        if location_x is not None and location_y is not None and location_z is not None:
            location = (location_x, location_y, location_z)

        result = self.bank.report_trade_by_uuid(
            minecraft_uuid=minecraft_uuid,
            trade_type=trade_type,
            item_name=item_name,
            item_quantity=item_quantity,
            carat_amount=carat_amount,
            golden_carat_amount=golden_carat_amount,
            item_category=item_category,
            counterparty_name=counterparty_name,
            world_name=world_name,
            location=location,
            notes=notes,
        )

        if result.success:
            return {
                "success": True,
                "trade_id": result.data["trade_id"],
                "trade_type": result.data["trade_type"],
                "item_name": result.data["item_name"],
                "price_per_item": result.data["price_per_item"],
                "message": result.message,
            }
        return {"success": False, "error": result.message}

    def get_item_price(self, item_name: str) -> dict:
        """
        Get current market price for an item

        Args:
            item_name: Name of the item

        Returns:
            {"success": bool, "price": float, ...}
        """
        result = self.bank.get_item_price(item_name)

        if result.success:
            if result.data.get("found"):
                return {
                    "success": True,
                    "found": True,
                    "item_name": result.data["item_name"],
                    "category": result.data["category"],
                    "current_price": result.data["current_price"],
                    "trade_count_24h": result.data["trade_count_24h"],
                    "volume_24h": result.data["volume_24h"],
                }
            return {"success": True, "found": False, "item_name": item_name}
        return {"success": False, "error": result.message}

    def get_trending_items(self, limit: int = 10) -> dict:
        """
        Get items with highest trading volume

        Args:
            limit: Maximum number of items to return

        Returns:
            {"success": bool, "items": [...]}
        """
        result = self.bank.get_trending_items(limit)

        if result.success:
            return {"success": True, "items": result.data["items"]}
        return {"success": False, "error": result.message}

    def get_my_trades(self, minecraft_uuid: str, limit: int = 20) -> dict:
        """
        Get player's recent trades

        Args:
            minecraft_uuid: Player's Minecraft UUID
            limit: Maximum trades to return

        Returns:
            {"success": bool, "trades": [...]}
        """
        from ..models.base import get_db
        from ..services.trade_service import TradeService
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_minecraft_uuid(minecraft_uuid)
                if not user:
                    return {"success": False, "error": "Player not registered"}

                trades = trade_service.get_user_trades(user, limit=limit)

                return {
                    "success": True,
                    "trade_count": len(trades),
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
                    ],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_my_stats(self, minecraft_uuid: str) -> dict:
        """
        Get player's trading statistics

        Args:
            minecraft_uuid: Player's Minecraft UUID

        Returns:
            {"success": bool, "stats": {...}}
        """
        from ..models.base import get_db
        from ..services.trade_service import TradeService
        from ..services.user_service import UserService

        try:
            with get_db() as db:
                user_service = UserService(db)
                trade_service = TradeService(db)

                user = user_service.get_by_minecraft_uuid(minecraft_uuid)
                if not user:
                    return {"success": False, "error": "Player not registered"}

                stats = trade_service.get_trader_stats(user)

                if not stats:
                    return {"success": True, "has_stats": False, "total_trades": 0}

                return {
                    "success": True,
                    "has_stats": True,
                    "total_trades": stats.total_trades,
                    "buy_count": stats.buy_count,
                    "sell_count": stats.sell_count,
                    "total_volume": float(stats.total_volume_carats),
                    "average_trade_size": float(stats.average_trade_size),
                    "verified_trades": stats.verified_trade_count,
                    "reputation": float(stats.reputation_score),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Example FastAPI integration
def create_fastapi_app():
    """
    Create a FastAPI app for Java mod REST integration

    Usage:
        from src.integration.java_interface import create_fastapi_app
        app = create_fastapi_app()
        # Run with: uvicorn module:app --host 0.0.0.0 --port 8080
    """
    try:
        from typing import List, Optional

        from fastapi import FastAPI, HTTPException, Query
        from pydantic import BaseModel
    except ImportError:
        raise ImportError("FastAPI required: pip install fastapi uvicorn")

    app = FastAPI(title="Arca Bank API", version="1.0.0")
    interface = JavaModInterface()

    class TransferRequest(BaseModel):
        sender_uuid: str
        recipient_uuid: str
        amount: float
        currency: str = "carat"

    class RegisterRequest(BaseModel):
        minecraft_uuid: str
        minecraft_username: str
        discord_id: str = None

    class TradeReportRequest(BaseModel):
        minecraft_uuid: str
        trade_type: str  # BUY, SELL, EXCHANGE
        item_name: str
        item_quantity: int
        carat_amount: float
        golden_carat_amount: float = 0.0
        item_category: str = "OTHER"
        counterparty_name: Optional[str] = None
        world_name: Optional[str] = None
        location_x: Optional[int] = None
        location_y: Optional[int] = None
        location_z: Optional[int] = None
        notes: Optional[str] = None

    @app.get("/api/balance/{minecraft_uuid}")
    async def get_balance(minecraft_uuid: str):
        result = interface.get_balance_by_uuid(minecraft_uuid)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @app.post("/api/transfer")
    async def transfer(request: TransferRequest):
        result = interface.transfer_by_uuid(
            request.sender_uuid, request.recipient_uuid, request.amount, request.currency
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.post("/api/register")
    async def register(request: RegisterRequest):
        result = interface.register_player(
            request.minecraft_uuid, request.minecraft_username, request.discord_id
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.get("/api/market")
    async def get_market():
        return interface.get_market_price()

    @app.get("/api/treasury")
    async def get_treasury():
        return interface.get_treasury_info()

    @app.get("/api/is_banker/{minecraft_uuid}")
    async def is_banker(minecraft_uuid: str):
        result = interface.check_is_banker(minecraft_uuid)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    # ==================== TRADE ENDPOINTS ====================

    @app.post("/api/trade/report")
    async def report_trade(request: TradeReportRequest):
        """Report a trade from in-game"""
        result = interface.report_trade(
            minecraft_uuid=request.minecraft_uuid,
            trade_type=request.trade_type,
            item_name=request.item_name,
            item_quantity=request.item_quantity,
            carat_amount=request.carat_amount,
            golden_carat_amount=request.golden_carat_amount,
            item_category=request.item_category,
            counterparty_name=request.counterparty_name,
            world_name=request.world_name,
            location_x=request.location_x,
            location_y=request.location_y,
            location_z=request.location_z,
            notes=request.notes,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to report trade")
            )
        return result

    @app.get("/api/trade/price/{item_name}")
    async def get_item_price(item_name: str):
        """Get current market price for an item"""
        return interface.get_item_price(item_name)

    @app.get("/api/trade/trending")
    async def get_trending(limit: int = Query(default=10, le=50)):
        """Get trending items by trading volume"""
        return interface.get_trending_items(limit)

    @app.get("/api/trade/history/{minecraft_uuid}")
    async def get_trade_history(minecraft_uuid: str, limit: int = Query(default=20, le=100)):
        """Get player's trade history"""
        result = interface.get_my_trades(minecraft_uuid, limit)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @app.get("/api/trade/stats/{minecraft_uuid}")
    async def get_trade_stats(minecraft_uuid: str):
        """Get player's trading statistics"""
        result = interface.get_my_stats(minecraft_uuid)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    return app
