"""
Treasury Service
Manages the central treasury, transactions, and book value calculations
"""

from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..config import economy
from ..models.currency import CurrencyType
from ..models.treasury import TransactionType, Treasury, TreasurySnapshot, TreasuryTransaction
from ..models.user import User
from .currency_service import CurrencyService


class TreasuryService:
    """
    Service for managing the central treasury
    """

    def __init__(self, db: Session):
        self.db = db
        self.currency_service = CurrencyService(db)

    # ==================== TREASURY STATE ====================

    def get_treasury(self) -> Treasury:
        """Get or create the treasury singleton"""
        treasury = self.db.query(Treasury).first()
        if not treasury:
            treasury = Treasury(
                total_diamonds=Decimal("0"),
                total_carats_minted=Decimal("0"),
                total_golden_carats_minted=Decimal("0"),
                reserve_diamonds=Decimal("0"),
                total_books_in_circulation=0,
                accumulated_fees_carats=Decimal("0"),
            )
            self.db.add(treasury)
            self.db.flush()
        return treasury

    def get_treasury_status(self) -> dict:
        """Get comprehensive treasury status"""
        treasury = self.get_treasury()

        return {
            "total_diamonds": Decimal(treasury.total_diamonds),
            "reserve_diamonds": Decimal(treasury.reserve_diamonds),
            "total_carats_minted": Decimal(treasury.total_carats_minted),
            "total_golden_carats_minted": Decimal(treasury.total_golden_carats_minted),
            "total_circulation_in_carats": treasury.total_circulation_in_carats,
            "book_value": treasury.book_value,
            "reserve_ratio": treasury.reserve_ratio,
            "total_books": treasury.total_books_in_circulation,
            "accumulated_fees": Decimal(treasury.accumulated_fees_carats),
            "last_updated": treasury.last_updated,
        }

    def recalculate_book_value(self) -> Decimal:
        """Recalculate and return current book value"""
        treasury = self.get_treasury()
        return treasury.book_value

    # ==================== DEPOSIT / WITHDRAWAL ====================

    def deposit_diamonds(
        self,
        user: User,
        diamond_amount: Decimal,
        carat_amount: Decimal,
        notes: Optional[str] = None,
    ) -> TreasuryTransaction:
        """
        Deposit diamonds into treasury and issue carats to user
        """
        if diamond_amount <= 0:
            raise ValueError("Diamond amount must be positive")
        if carat_amount <= 0:
            raise ValueError("Carat amount must be positive")

        treasury = self.get_treasury()

        # Update treasury
        treasury.total_diamonds = Decimal(treasury.total_diamonds) + diamond_amount
        treasury.total_carats_minted = Decimal(treasury.total_carats_minted) + carat_amount

        # Add carats to user
        self.currency_service.add_balance(user, CurrencyType.CARAT, carat_amount)

        # Record transaction
        transaction = self._record_transaction(
            transaction_type=TransactionType.DEPOSIT,
            user=user,
            diamond_amount=diamond_amount,
            carat_amount=carat_amount,
            notes=notes,
        )

        return transaction

    def withdraw_diamonds(
        self, user: User, carat_amount: Decimal, notes: Optional[str] = None
    ) -> Tuple[Decimal, Decimal, TreasuryTransaction]:
        """
        Withdraw diamonds from treasury by returning carats
        Returns: (diamonds_received, fee_amount, transaction)
        """
        if carat_amount <= 0:
            raise ValueError("Carat amount must be positive")

        treasury = self.get_treasury()

        # Check user has enough carats
        balances = self.currency_service.get_user_balances(user)
        if balances["carats"] < carat_amount:
            raise ValueError("Insufficient carat balance")

        # Calculate withdrawal fee
        fee = CurrencyService.calculate_transaction_fee(carat_amount)
        fee_rate = Decimal(economy.WITHDRAWAL_FEE_PERCENT) / Decimal("100")
        withdrawal_fee = (carat_amount * fee_rate).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        net_carats = carat_amount - withdrawal_fee

        # Calculate diamonds to return based on book value
        book_value = treasury.book_value
        diamonds_to_return = (net_carats * book_value).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

        # Check treasury has enough diamonds
        available_diamonds = Decimal(treasury.total_diamonds) - Decimal(treasury.reserve_diamonds)
        if diamonds_to_return > available_diamonds:
            raise ValueError("Insufficient treasury diamonds for withdrawal")

        # Update treasury
        treasury.total_diamonds = Decimal(treasury.total_diamonds) - diamonds_to_return
        treasury.total_carats_minted = Decimal(treasury.total_carats_minted) - net_carats
        treasury.accumulated_fees_carats = (
            Decimal(treasury.accumulated_fees_carats) + withdrawal_fee
        )

        # Remove carats from user
        self.currency_service.subtract_balance(user, CurrencyType.CARAT, carat_amount)

        # Record transaction
        transaction = self._record_transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            user=user,
            diamond_amount=-diamonds_to_return,
            carat_amount=-carat_amount,
            fee_amount=withdrawal_fee,
            notes=notes,
        )

        return diamonds_to_return, withdrawal_fee, transaction

    # ==================== ATM PROFITS ====================

    def record_atm_profit(
        self, user: User, book_count: int, notes: Optional[str] = None
    ) -> TreasuryTransaction:
        """
        Record ATM profit at 90 diamonds per book
        This is pure profit for the treasury
        """
        if book_count <= 0:
            raise ValueError("Book count must be positive")

        if not user.can_write():
            raise PermissionError("Only bankers can record ATM profits")

        treasury = self.get_treasury()
        diamond_amount = Decimal(book_count * economy.DIAMONDS_PER_BOOK)

        # Update treasury - pure profit, adds to reserves
        treasury.total_diamonds = Decimal(treasury.total_diamonds) + diamond_amount
        treasury.reserve_diamonds = Decimal(treasury.reserve_diamonds) + (
            diamond_amount * Decimal(economy.TREASURY_RESERVE_RATIO)
        )
        treasury.total_books_in_circulation += book_count

        # Record transaction
        transaction = self._record_transaction(
            transaction_type=TransactionType.ATM_PROFIT,
            user=user,
            diamond_amount=diamond_amount,
            book_count=book_count,
            notes=notes
            or f"ATM profit: {book_count} books @ {economy.DIAMONDS_PER_BOOK} diamonds each",
        )

        return transaction

    # ==================== FEE COLLECTION ====================

    def collect_fee(
        self,
        fee_amount: Decimal,
        fee_type: TransactionType,
        user: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TreasuryTransaction:
        """Record fee collection"""
        treasury = self.get_treasury()
        treasury.accumulated_fees_carats = Decimal(treasury.accumulated_fees_carats) + fee_amount

        return self._record_transaction(
            transaction_type=fee_type,
            user=user,
            carat_amount=fee_amount,
            fee_amount=fee_amount,
            notes=notes,
            is_automated=True,
        )

    # ==================== TRANSACTION HISTORY ====================

    def get_transaction_history(
        self,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionType] = None,
        user: Optional[User] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TreasuryTransaction]:
        """Get transaction history with filters"""
        query = self.db.query(TreasuryTransaction)

        if transaction_type:
            query = query.filter(TreasuryTransaction.transaction_type == transaction_type)
        if user:
            query = query.filter(TreasuryTransaction.user_id == user.id)
        if start_date:
            query = query.filter(TreasuryTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(TreasuryTransaction.created_at <= end_date)

        return (
            query.order_by(desc(TreasuryTransaction.created_at)).offset(offset).limit(limit).all()
        )

    def get_inflow_outflow(self, days: int = 30) -> dict:
        """Get treasury inflow/outflow summary"""
        start_date = datetime.utcnow() - timedelta(days=days)

        transactions = (
            self.db.query(TreasuryTransaction)
            .filter(TreasuryTransaction.created_at >= start_date)
            .all()
        )

        inflow_diamonds = Decimal("0")
        outflow_diamonds = Decimal("0")
        inflow_carats = Decimal("0")
        outflow_carats = Decimal("0")
        total_fees = Decimal("0")

        for tx in transactions:
            diamond_amt = Decimal(tx.diamond_amount)
            carat_amt = Decimal(tx.carat_amount)
            fee_amt = Decimal(tx.fee_amount)

            if diamond_amt > 0:
                inflow_diamonds += diamond_amt
            else:
                outflow_diamonds += abs(diamond_amt)

            if carat_amt > 0:
                inflow_carats += carat_amt
            else:
                outflow_carats += abs(carat_amt)

            total_fees += fee_amt

        return {
            "period_days": days,
            "inflow_diamonds": inflow_diamonds,
            "outflow_diamonds": outflow_diamonds,
            "net_diamonds": inflow_diamonds - outflow_diamonds,
            "inflow_carats": inflow_carats,
            "outflow_carats": outflow_carats,
            "net_carats": inflow_carats - outflow_carats,
            "total_fees_collected": total_fees,
            "transaction_count": len(transactions),
        }

    # ==================== SNAPSHOTS ====================

    def create_snapshot(self) -> TreasurySnapshot:
        """Create a point-in-time snapshot of treasury state"""
        treasury = self.get_treasury()

        snapshot = TreasurySnapshot(
            total_diamonds=treasury.total_diamonds,
            total_carats=treasury.total_carats_minted,
            total_golden_carats=treasury.total_golden_carats_minted,
            reserve_diamonds=treasury.reserve_diamonds,
            book_value=treasury.book_value,
            reserve_ratio=treasury.reserve_ratio,
            total_circulation=treasury.total_circulation_in_carats,
            fees_collected=treasury.accumulated_fees_carats,
        )
        self.db.add(snapshot)
        return snapshot

    def get_snapshots(self, days: int = 30, limit: int = 100) -> List[TreasurySnapshot]:
        """Get treasury snapshots for the given period"""
        start_date = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(TreasurySnapshot)
            .filter(TreasurySnapshot.snapshot_time >= start_date)
            .order_by(desc(TreasurySnapshot.snapshot_time))
            .limit(limit)
            .all()
        )

    # ==================== INTERNAL HELPERS ====================

    def _record_transaction(
        self,
        transaction_type: TransactionType,
        user: Optional[User] = None,
        recipient: Optional[User] = None,
        diamond_amount: Decimal = Decimal("0"),
        carat_amount: Decimal = Decimal("0"),
        golden_carat_amount: Decimal = Decimal("0"),
        fee_amount: Decimal = Decimal("0"),
        book_count: int = 0,
        notes: Optional[str] = None,
        is_automated: bool = False,
    ) -> TreasuryTransaction:
        """Record a transaction in the ledger"""
        treasury = self.get_treasury()

        transaction = TreasuryTransaction(
            transaction_type=transaction_type,
            diamond_amount=diamond_amount,
            carat_amount=carat_amount,
            golden_carat_amount=golden_carat_amount,
            fee_amount=fee_amount,
            book_count=book_count,
            user_id=user.id if user else None,
            recipient_id=recipient.id if recipient else None,
            treasury_diamonds_after=treasury.total_diamonds,
            treasury_carats_after=treasury.total_carats_minted,
            book_value_after=treasury.book_value,
            notes=notes,
            is_automated=is_automated,
        )
        self.db.add(transaction)
        return transaction
