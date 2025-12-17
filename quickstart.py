#!/usr/bin/env python3
"""
Arca Bank Quick Start Script
Run this to set up and test the system
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import ArcaBank
from src.api.scheduler import start_scheduler
from src.models.base import get_db
from src.models.user import UserRole
from src.services.user_service import UserService


def setup_initial_head_banker(discord_id: str, discord_username: str):
    """Set up the initial head banker (run once)"""
    bank = ArcaBank()

    # Register the head banker
    result = bank.register_user(discord_id, discord_username)
    if not result.success:
        print(f"Failed to register: {result.message}")
        return False

    # Set as head banker
    with get_db() as db:
        user_service = UserService(db)
        user = user_service.get_by_discord_id(discord_id)
        user.role = UserRole.HEAD_BANKER

    print(f"Success: {discord_username} is now Head Banker!")
    return True


def print_status():
    """Print current system status"""
    bank = ArcaBank()

    print("\n" + "=" * 50)
    print("ARCA BANK STATUS")
    print("=" * 50)

    # Treasury
    treasury = bank.get_treasury_status()
    if treasury.success:
        print("\nTREASURY:")
        print(f"   Diamonds: {treasury.data['total_diamonds']:.2f}")
        print(f"   Carats Minted: {treasury.data['total_carats_minted']:.2f}")
        print(f"   Book Value: {treasury.data['book_value']:.4f}/C")
        print(f"   Reserve Ratio: {treasury.data['reserve_ratio']:.1f}%")
        print(f"   Fees Collected: {treasury.data['accumulated_fees']:.2f} C")

    # Market
    market = bank.get_market_status()
    if market.success:
        print("\nMARKET:")
        print(f"   Index: {market.data['current_index']:.2f}")
        print(f"   Price: {market.data['carat_price']:.4f}/C")
        print(f"   Status: {market.data['circulation_status']}")
        print(f"   24H Change: {market.data['change_24h']:+.2f}%")

    print("\n" + "=" * 50)


def interactive_demo():
    """Run an interactive demo"""
    bank = ArcaBank()

    print("\nWelcome to Arca Bank Demo!")
    print("-" * 40)

    # Create demo users
    print("\nCreating demo users...")
    bank.register_user("demo_admin", "DemoAdmin")
    bank.register_user("demo_banker", "DemoBanker")
    bank.register_user("demo_user1", "DemoPlayer1")
    bank.register_user("demo_user2", "DemoPlayer2")

    # Set roles
    with get_db() as db:
        user_service = UserService(db)
        admin = user_service.get_by_discord_id("demo_admin")
        admin.role = UserRole.HEAD_BANKER
        banker = user_service.get_by_discord_id("demo_banker")
        banker.role = UserRole.BANKER

    print("   - Created: DemoAdmin (Head Banker)")
    print("   - Created: DemoBanker (Banker)")
    print("   - Created: DemoPlayer1, DemoPlayer2 (Users)")

    # Initial deposit
    print("\nBanker deposits 1000 diamonds, issues 1000 carats...")
    result = bank.deposit("demo_banker", "demo_user1", 1000, 1000)
    print(f"   - {result.message}")

    # Transfer
    print("\nPlayer1 transfers 100 carats to Player2...")
    result = bank.transfer("demo_user1", "demo_user2", 100, "carat")
    if result.success:
        print(
            f"   - Sent: {result.data['amount_sent']} -> Received: {result.data['amount_received']}"
        )
        print(f"   - Fee collected: {result.data['fee']} carats")

    # ATM profit
    print("\nRecording ATM profit (5 books = 450 diamonds)...")
    result = bank.record_atm_profit("demo_banker", 5)
    print(f"   - {result.message}")

    # Mint check
    print("\nHead Banker runs mint check...")
    result = bank.mint_check("demo_admin", 0)
    if result.success:
        print(f"   - Recommendation: {result.data['action'].upper()}")
        print(f"   - {result.data['reason'][:100]}...")

    # Final status
    print_status()

    print("\nDemo complete! The database (arca_bank.db) persists between runs.")
    print("   Run 'python quickstart.py status' to see current status.")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Arca Bank Quick Start")
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["demo", "status", "setup-head-banker"],
        help="Command to run",
    )
    parser.add_argument("--discord-id", help="Discord ID for head banker setup")
    parser.add_argument("--username", help="Username for head banker setup")

    args = parser.parse_args()

    if args.command == "demo":
        interactive_demo()
    elif args.command == "status":
        print_status()
    elif args.command == "setup-head-banker":
        if not args.discord_id or not args.username:
            print("Error: --discord-id and --username required for setup-head-banker")
            sys.exit(1)
        setup_initial_head_banker(args.discord_id, args.username)


if __name__ == "__main__":
    main()
