"""
Mint Service
Handles minting, burning, and provides mint/burn recommendations
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import economy
from ..models.currency import CurrencyType
from ..models.treasury import TransactionType, Treasury, TreasuryTransaction
from ..models.user import User


@dataclass
class MintRecommendation:
    """Recommendation for minting or burning currency"""

    action: str  # 'mint', 'burn', 'hold'
    amount: Decimal
    reason: str
    confidence: str  # 'high', 'medium', 'low'
    current_book_value: Decimal
    target_book_value: Decimal
    current_circulation: Decimal
    projected_book_value: Decimal


class MintService:
    """
    Service for minting/burning currency and providing recommendations
    """

    TARGET_BOOK_VALUE = Decimal("1.0")  # 1 carat = 1 diamond

    def __init__(self, db: Session):
        self.db = db

    # ==================== MINTING OPERATIONS ====================

    def mint_carats(
        self,
        admin: User,
        amount: Decimal,
        currency_type: CurrencyType = CurrencyType.CARAT,
        notes: Optional[str] = None,
    ) -> TreasuryTransaction:
        """
        Mint new currency (Head Banker only)
        This increases money supply without adding backing
        """
        if not admin.can_mint():
            raise PermissionError("Only Head Banker can mint currency")

        if amount <= 0:
            raise ValueError("Mint amount must be positive")

        # Check daily mint limit
        if not self._check_mint_limit(amount, currency_type):
            raise ValueError(f"Exceeds daily mint limit of {economy.MAX_MINT_PER_DAY} carats")

        treasury = self._get_treasury()

        # Update minted supply
        if currency_type == CurrencyType.CARAT:
            treasury.total_carats_minted = Decimal(treasury.total_carats_minted) + amount
        else:
            treasury.total_golden_carats_minted = (
                Decimal(treasury.total_golden_carats_minted) + amount
            )

        # Record transaction
        transaction = TreasuryTransaction(
            transaction_type=TransactionType.MINT,
            carat_amount=amount if currency_type == CurrencyType.CARAT else Decimal("0"),
            golden_carat_amount=(
                amount if currency_type == CurrencyType.GOLDEN_CARAT else Decimal("0")
            ),
            user_id=admin.id,
            treasury_diamonds_after=treasury.total_diamonds,
            treasury_carats_after=treasury.total_carats_minted,
            book_value_after=treasury.book_value,
            notes=notes or f"Minted {amount} {currency_type.value}",
        )
        self.db.add(transaction)

        return transaction

    def burn_carats(
        self,
        admin: User,
        amount: Decimal,
        currency_type: CurrencyType = CurrencyType.CARAT,
        notes: Optional[str] = None,
    ) -> TreasuryTransaction:
        """
        Burn currency from supply (Head Banker only)
        This reduces money supply, increasing backing per remaining carat
        """
        if not admin.can_mint():
            raise PermissionError("Only Head Banker can burn currency")

        if amount <= 0:
            raise ValueError("Burn amount must be positive")

        treasury = self._get_treasury()

        # Validate we have enough to burn
        if currency_type == CurrencyType.CARAT:
            if Decimal(treasury.total_carats_minted) < amount:
                raise ValueError("Cannot burn more carats than exist in circulation")
            treasury.total_carats_minted = Decimal(treasury.total_carats_minted) - amount
        else:
            if Decimal(treasury.total_golden_carats_minted) < amount:
                raise ValueError("Cannot burn more golden carats than exist in circulation")
            treasury.total_golden_carats_minted = (
                Decimal(treasury.total_golden_carats_minted) - amount
            )

        # Record transaction
        transaction = TreasuryTransaction(
            transaction_type=TransactionType.BURN,
            carat_amount=-amount if currency_type == CurrencyType.CARAT else Decimal("0"),
            golden_carat_amount=(
                -amount if currency_type == CurrencyType.GOLDEN_CARAT else Decimal("0")
            ),
            user_id=admin.id,
            treasury_diamonds_after=treasury.total_diamonds,
            treasury_carats_after=treasury.total_carats_minted,
            book_value_after=treasury.book_value,
            notes=notes or f"Burned {amount} {currency_type.value}",
        )
        self.db.add(transaction)

        return transaction

    # ==================== MINT CHECK / RECOMMENDATIONS ====================

    def mint_check(self, atm_books_received: int = 0) -> MintRecommendation:
        """
        Analyze whether minting or burning would be beneficial
        Considers ATM profits at 90 diamonds per book
        """
        treasury = self._get_treasury()

        # Current state
        current_book_value = treasury.book_value
        current_circulation = treasury.total_circulation_in_carats
        current_diamonds = Decimal(treasury.total_diamonds)

        # ATM profit projection (90 diamonds per book)
        atm_diamonds = Decimal(atm_books_received * economy.DIAMONDS_PER_BOOK)
        projected_diamonds = current_diamonds + atm_diamonds

        # Calculate target circulation to maintain book value of 1.0
        target_circulation = projected_diamonds / self.TARGET_BOOK_VALUE

        # Calculate variance
        variance = current_circulation - target_circulation
        variance_percent = (
            abs(variance / target_circulation) if target_circulation > 0 else Decimal("0")
        )

        # Projected book value after ATM profits
        projected_book_value = (
            projected_diamonds / current_circulation
            if current_circulation > 0
            else self.TARGET_BOOK_VALUE
        )

        # Determine recommendation
        threshold = Decimal(economy.MINT_RECOMMENDATION_THRESHOLD)
        burn_threshold = Decimal(economy.BURN_INCENTIVE_THRESHOLD)

        if projected_book_value > burn_threshold:
            # Over-backed - could burn excess circulation or mint more
            # Minting here increases Arca's profit while keeping price stable
            mint_amount = self._calculate_mint_amount(projected_diamonds, current_circulation)

            return MintRecommendation(
                action="mint",
                amount=mint_amount,
                reason=f"Treasury is over-backed ({float(projected_book_value):.4f} diamond/carat). "
                f"Minting {float(mint_amount):.2f} carats will maintain price stability while "
                f"increasing Arca's currency supply (profit opportunity).",
                confidence="high" if variance_percent > threshold else "medium",
                current_book_value=current_book_value,
                target_book_value=self.TARGET_BOOK_VALUE,
                current_circulation=current_circulation,
                projected_book_value=self.TARGET_BOOK_VALUE,
            )

        elif projected_book_value < Decimal("1") - threshold:
            # Under-backed - need to burn currency
            burn_amount = self._calculate_burn_amount(projected_diamonds, current_circulation)

            return MintRecommendation(
                action="burn",
                amount=burn_amount,
                reason=f"Treasury is under-backed ({float(projected_book_value):.4f} diamond/carat). "
                f"Burning {float(burn_amount):.2f} carats will restore backing ratio.",
                confidence="high" if variance_percent > threshold else "medium",
                current_book_value=current_book_value,
                target_book_value=self.TARGET_BOOK_VALUE,
                current_circulation=current_circulation,
                projected_book_value=self.TARGET_BOOK_VALUE,
            )

        else:
            # Within acceptable range
            return MintRecommendation(
                action="hold",
                amount=Decimal("0"),
                reason=f"Book value ({float(projected_book_value):.4f}) is within acceptable range. "
                f"No minting or burning recommended.",
                confidence="high",
                current_book_value=current_book_value,
                target_book_value=self.TARGET_BOOK_VALUE,
                current_circulation=current_circulation,
                projected_book_value=projected_book_value,
            )

    def _calculate_mint_amount(self, diamonds: Decimal, circulation: Decimal) -> Decimal:
        """Calculate optimal mint amount to reach target book value"""
        # target = diamonds / (circulation + mint)
        # mint = diamonds / target - circulation
        mint = diamonds / self.TARGET_BOOK_VALUE - circulation

        # Cap at daily limit
        max_mint = Decimal(economy.MAX_MINT_PER_DAY)
        mint = min(mint, max_mint)

        return mint.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    def _calculate_burn_amount(self, diamonds: Decimal, circulation: Decimal) -> Decimal:
        """Calculate optimal burn amount to reach target book value"""
        # target = diamonds / (circulation - burn)
        # burn = circulation - diamonds / target
        burn = circulation - diamonds / self.TARGET_BOOK_VALUE

        return max(burn, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # ==================== PROFIT ANALYSIS ====================

    def calculate_profit_projection(self, projected_books: int, days: int = 30) -> dict:
        """
        Calculate profit projection based on ATM income and fees
        """
        # ATM profit
        atm_diamonds = Decimal(projected_books * economy.DIAMONDS_PER_BOOK)

        # Get recent fee collection rate
        fee_rate = self._get_average_daily_fees() * days

        # Calculate minting opportunity
        treasury = self._get_treasury()
        current_book_value = treasury.book_value

        # If we can mint to maintain book value
        mint_check = self.mint_check(projected_books)
        potential_mint = mint_check.amount if mint_check.action == "mint" else Decimal("0")

        return {
            "period_days": days,
            "projected_atm_diamonds": atm_diamonds,
            "projected_atm_books": projected_books,
            "projected_fee_income": fee_rate,
            "potential_mint_amount": potential_mint,
            "mint_recommendation": mint_check.action,
            "mint_reason": mint_check.reason,
            "current_book_value": current_book_value,
            "estimated_total_profit_diamonds": atm_diamonds,
            "estimated_total_profit_carats": fee_rate + potential_mint,
        }

    def _get_average_daily_fees(self) -> Decimal:
        """Get average daily fee collection"""
        cutoff = datetime.utcnow() - timedelta(days=30)

        result = (
            self.db.query(func.sum(TreasuryTransaction.fee_amount))
            .filter(TreasuryTransaction.created_at >= cutoff)
            .scalar()
        )

        total_fees = Decimal(result) if result else Decimal("0")
        return (total_fees / Decimal("30")).quantize(Decimal("0.01"))

    # ==================== HELPERS ====================

    def _get_treasury(self) -> Treasury:
        """Get treasury singleton"""
        treasury = self.db.query(Treasury).first()
        if not treasury:
            treasury = Treasury()
            self.db.add(treasury)
            self.db.flush()
        return treasury

    def _check_mint_limit(self, amount: Decimal, currency_type: CurrencyType) -> bool:
        """Check if mint is within daily limit"""
        # Convert to carats for comparison
        if currency_type == CurrencyType.GOLDEN_CARAT:
            amount = amount * Decimal(economy.GOLDEN_CARAT_MULTIPLIER)

        # Get today's mints
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = (
            self.db.query(func.sum(TreasuryTransaction.carat_amount))
            .filter(
                TreasuryTransaction.transaction_type == TransactionType.MINT,
                TreasuryTransaction.created_at >= today_start,
            )
            .scalar()
        )

        today_minted = Decimal(result) if result else Decimal("0")

        return (today_minted + amount) <= Decimal(economy.MAX_MINT_PER_DAY)

    def get_mint_history(self, days: int = 30) -> dict:
        """Get minting/burning history"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        mints = (
            self.db.query(TreasuryTransaction)
            .filter(
                TreasuryTransaction.transaction_type == TransactionType.MINT,
                TreasuryTransaction.created_at >= cutoff,
            )
            .all()
        )

        burns = (
            self.db.query(TreasuryTransaction)
            .filter(
                TreasuryTransaction.transaction_type == TransactionType.BURN,
                TreasuryTransaction.created_at >= cutoff,
            )
            .all()
        )

        return {
            "period_days": days,
            "total_minted": sum(
                Decimal(m.carat_amount) + Decimal(m.golden_carat_amount) * 9 for m in mints
            ),
            "total_burned": sum(
                abs(Decimal(b.carat_amount)) + abs(Decimal(b.golden_carat_amount)) * 9
                for b in burns
            ),
            "mint_count": len(mints),
            "burn_count": len(burns),
            "mints": [
                {
                    "amount": float(m.carat_amount) + float(m.golden_carat_amount) * 9,
                    "timestamp": m.created_at.isoformat(),
                    "notes": m.notes,
                }
                for m in mints
            ],
            "burns": [
                {
                    "amount": float(abs(Decimal(b.carat_amount)))
                    + float(abs(Decimal(b.golden_carat_amount))) * 9,
                    "timestamp": b.created_at.isoformat(),
                    "notes": b.notes,
                }
                for b in burns
            ],
        }
