"""
Currency Service
Handles all currency operations including conversions and exchanges
"""

from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..config import economy
from ..models.currency import CurrencyBalance, CurrencyExchange, CurrencyType
from ..models.treasury import TransactionType, TreasuryTransaction
from ..models.user import User


class CurrencyService:
    """
    Service for managing currency operations
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== CONVERSION ====================

    @staticmethod
    def carats_to_golden(carats: Decimal) -> Decimal:
        """Convert carats to golden carats (before fees)"""
        return (carats / Decimal(economy.GOLDEN_CARAT_MULTIPLIER)).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

    @staticmethod
    def golden_to_carats(golden_carats: Decimal) -> Decimal:
        """Convert golden carats to carats (before fees)"""
        return (golden_carats * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

    @staticmethod
    def calculate_exchange_fee(amount: Decimal) -> Decimal:
        """Calculate exchange fee for currency conversion"""
        fee_rate = Decimal(economy.EXCHANGE_FEE_PERCENT) / Decimal("100")
        return (amount * fee_rate).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

    @staticmethod
    def calculate_transaction_fee(amount: Decimal) -> Decimal:
        """Calculate transaction fee"""
        fee_rate = Decimal(economy.TRANSACTION_FEE_PERCENT) / Decimal("100")
        return (amount * fee_rate).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

    @staticmethod
    def to_total_carats(carats: Decimal, golden_carats: Decimal) -> Decimal:
        """Convert mixed currencies to total carats value"""
        golden_value = golden_carats * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)
        return carats + golden_value

    # ==================== BALANCE OPERATIONS ====================

    def get_or_create_balance(self, user: User, currency_type: CurrencyType) -> CurrencyBalance:
        """Get user's balance for a currency type, creating if needed"""
        balance = (
            self.db.query(CurrencyBalance)
            .filter(
                CurrencyBalance.user_id == user.id, CurrencyBalance.currency_type == currency_type
            )
            .first()
        )

        if not balance:
            balance = CurrencyBalance(
                user_id=user.id, currency_type=currency_type, balance=Decimal("0")
            )
            self.db.add(balance)
            self.db.flush()

        return balance

    def get_user_balances(self, user: User) -> dict:
        """Get all balances for a user"""
        carat_balance = self.get_or_create_balance(user, CurrencyType.CARAT)
        golden_balance = self.get_or_create_balance(user, CurrencyType.GOLDEN_CARAT)

        return {
            "carats": Decimal(carat_balance.balance),
            "golden_carats": Decimal(golden_balance.balance),
            "total_in_carats": self.to_total_carats(
                Decimal(carat_balance.balance), Decimal(golden_balance.balance)
            ),
        }

    def add_balance(
        self, user: User, currency_type: CurrencyType, amount: Decimal
    ) -> CurrencyBalance:
        """Add to user's balance"""
        if amount < 0:
            raise ValueError("Cannot add negative amount")

        balance = self.get_or_create_balance(user, currency_type)
        balance.balance = Decimal(balance.balance) + amount
        balance.updated_at = datetime.utcnow()
        return balance

    def subtract_balance(
        self, user: User, currency_type: CurrencyType, amount: Decimal
    ) -> CurrencyBalance:
        """Subtract from user's balance"""
        if amount < 0:
            raise ValueError("Cannot subtract negative amount")

        balance = self.get_or_create_balance(user, currency_type)

        if Decimal(balance.balance) < amount:
            raise ValueError(f"Insufficient {currency_type.value} balance")

        balance.balance = Decimal(balance.balance) - amount
        balance.updated_at = datetime.utcnow()
        return balance

    # ==================== EXCHANGE OPERATIONS ====================

    def exchange_currency(
        self, user: User, from_type: CurrencyType, to_type: CurrencyType, amount: Decimal
    ) -> Tuple[Decimal, Decimal, CurrencyExchange]:
        """
        Exchange between currency types with fee
        Returns: (received_amount, fee_amount, exchange_record)
        """
        if from_type == to_type:
            raise ValueError("Cannot exchange same currency type")

        if amount <= 0:
            raise ValueError("Exchange amount must be positive")

        # Check balance
        from_balance = self.get_or_create_balance(user, from_type)
        if Decimal(from_balance.balance) < amount:
            raise ValueError(f"Insufficient {from_type.value} balance")

        # Calculate conversion
        if from_type == CurrencyType.CARAT:
            # Converting carats to golden carats
            base_result = self.carats_to_golden(amount)
            fee_in_carats = self.calculate_exchange_fee(amount)
            # Deduct fee from the amount being converted
            net_amount = amount - fee_in_carats
            received = self.carats_to_golden(net_amount)
        else:
            # Converting golden carats to carats
            base_result = self.golden_to_carats(amount)
            fee_in_carats = self.calculate_exchange_fee(base_result)
            received = base_result - fee_in_carats

        # Perform the exchange
        self.subtract_balance(user, from_type, amount)
        self.add_balance(user, to_type, received)

        # Record the exchange
        exchange = CurrencyExchange(
            user_id=user.id,
            from_currency=from_type,
            to_currency=to_type,
            from_amount=amount,
            to_amount=received,
            fee_amount=fee_in_carats,
            exchange_rate=Decimal(economy.GOLDEN_CARAT_MULTIPLIER),
        )
        self.db.add(exchange)

        return received, fee_in_carats, exchange

    # ==================== TRANSFER OPERATIONS ====================

    def transfer(
        self,
        sender: User,
        recipient: User,
        currency_type: CurrencyType,
        amount: Decimal,
        apply_fee: bool = True,
    ) -> Tuple[Decimal, Decimal]:
        """
        Transfer currency between users
        Returns: (amount_received, fee_amount)
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        if sender.id == recipient.id:
            raise ValueError("Cannot transfer to self")

        # Calculate fee
        fee = self.calculate_transaction_fee(amount) if apply_fee else Decimal("0")
        amount_received = amount - fee

        # Perform transfer
        self.subtract_balance(sender, currency_type, amount)
        self.add_balance(recipient, currency_type, amount_received)

        return amount_received, fee
