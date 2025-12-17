"""
Arca Bank Test Suite
"""

from datetime import datetime
from decimal import Decimal

import pytest

from src.api.bank_api import ArcaBank
from src.models.base import Base, engine, get_db, init_db
from src.models.currency import CurrencyType
from src.models.user import User, UserRole


@pytest.fixture(autouse=True)
def setup_database():
    """Setup a fresh database for each test"""
    # Create all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def bank():
    """Get a fresh bank instance"""
    return ArcaBank()


class TestUserOperations:
    """Test user registration and management"""

    def test_register_user(self, bank):
        """Test user registration"""
        result = bank.register_user("12345", "TestUser")

        assert result.success
        assert result.data["discord_id"] == "12345"
        assert result.data["discord_username"] == "TestUser"
        assert result.data["role"] == "user"

    def test_register_user_with_minecraft(self, bank):
        """Test user registration with Minecraft account"""
        result = bank.register_user(
            "12345",
            "TestUser",
            minecraft_uuid="550e8400-e29b-41d4-a716-446655440000",
            minecraft_username="MCPlayer",
        )

        assert result.success
        assert result.data["minecraft_username"] == "MCPlayer"
        assert result.data["is_linked"]

    def test_duplicate_user(self, bank):
        """Test that duplicate registration returns existing user"""
        bank.register_user("12345", "TestUser")
        result = bank.register_user("12345", "TestUser2")

        assert result.success
        # Should return existing user

    def test_link_minecraft(self, bank):
        """Test linking Minecraft account"""
        bank.register_user("12345", "TestUser")
        result = bank.link_minecraft("12345", "550e8400-e29b-41d4-a716-446655440000", "MCPlayer")

        assert result.success
        assert result.data["minecraft_username"] == "MCPlayer"


class TestCurrencyOperations:
    """Test currency operations"""

    def test_get_balance_new_user(self, bank):
        """Test balance for new user is zero"""
        bank.register_user("12345", "TestUser")
        result = bank.get_balance("12345")

        assert result.success
        assert result.data["carats"] == 0
        assert result.data["golden_carats"] == 0

    def test_exchange_currency(self, bank):
        """Test currency exchange"""
        # Setup: Register user and deposit
        bank.register_user("admin", "Admin")
        bank.register_user("12345", "TestUser")

        # Need to manually add balance for test
        with get_db() as db:
            from src.services.currency_service import CurrencyService
            from src.services.user_service import UserService

            user_service = UserService(db)
            currency_service = CurrencyService(db)

            user = user_service.get_by_discord_id("12345")
            currency_service.add_balance(user, CurrencyType.CARAT, Decimal("100"))

        # Exchange 9 carats for 1 golden carat (minus fee)
        result = bank.exchange_currency("12345", 9, "carat", "golden_carat")

        assert result.success
        assert result.data["from_amount"] == 9
        # Should get slightly less than 1 due to fee
        assert result.data["to_amount"] < 1
        assert result.data["fee"] > 0


class TestTreasuryOperations:
    """Test treasury operations"""

    def test_get_treasury_status(self, bank):
        """Test getting treasury status"""
        result = bank.get_treasury_status()

        assert result.success
        assert "total_diamonds" in result.data
        assert "book_value" in result.data
        assert "reserve_ratio" in result.data

    def test_deposit_requires_banker(self, bank):
        """Test that deposit requires banker permission"""
        bank.register_user("12345", "TestUser")
        bank.register_user("67890", "Recipient")

        result = bank.deposit("12345", "67890", 100, 100)

        assert not result.success
        assert "Banker permission" in result.message


class TestMintOperations:
    """Test minting operations"""

    def test_mint_requires_head_banker(self, bank):
        """Test that minting requires head banker permission"""
        bank.register_user("12345", "TestUser")

        result = bank.mint("12345", 1000, "carat")

        assert not result.success
        assert "Head Banker permission" in result.message

    def test_mint_check_requires_head_banker(self, bank):
        """Test that mint check requires head banker permission"""
        bank.register_user("12345", "TestUser")

        result = bank.mint_check("12345", 0)

        assert not result.success
        assert "Head Banker permission" in result.message


class TestMarketOperations:
    """Test market operations"""

    def test_get_market_status(self, bank):
        """Test getting market status"""
        result = bank.get_market_status()

        assert result.success
        assert "current_index" in result.data
        assert "carat_price" in result.data
        assert "circulation_status" in result.data


class TestTransferOperations:
    """Test transfer operations"""

    def test_transfer_between_users(self, bank):
        """Test transferring currency between users"""
        # Setup users
        bank.register_user("sender", "Sender")
        bank.register_user("recipient", "Recipient")

        # Add balance to sender
        with get_db() as db:
            from src.services.currency_service import CurrencyService
            from src.services.user_service import UserService

            user_service = UserService(db)
            currency_service = CurrencyService(db)

            sender = user_service.get_by_discord_id("sender")
            currency_service.add_balance(sender, CurrencyType.CARAT, Decimal("100"))

        # Transfer
        result = bank.transfer("sender", "recipient", 50, "carat")

        assert result.success
        assert result.data["amount_sent"] == 50
        assert result.data["amount_received"] < 50  # Fee deducted
        assert result.data["fee"] > 0

    def test_transfer_insufficient_balance(self, bank):
        """Test transfer with insufficient balance"""
        bank.register_user("sender", "Sender")
        bank.register_user("recipient", "Recipient")

        result = bank.transfer("sender", "recipient", 100, "carat")

        assert not result.success
        assert "Insufficient" in result.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
