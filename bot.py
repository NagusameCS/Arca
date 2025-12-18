"""
Arca Bank Discord Bot
A comprehensive economy management bot for Minecraft servers
"""

import io
import os
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.api import ArcaBank, MarketScheduler
from src.api.scheduler import start_scheduler

# ==================== CONSTANTS & STYLING ====================


# Colors for embeds
class Colors:
    """Discord embed colors for consistent styling"""

    SUCCESS = 0x2ECC71  # Green
    ERROR = 0xE74C3C  # Red
    WARNING = 0xF39C12  # Orange
    INFO = 0x3498DB  # Blue
    GOLD = 0xF1C40F  # Gold
    PURPLE = 0x9B59B6  # Purple
    TEAL = 0x1ABC9C  # Teal
    DARK = 0x2C3E50  # Dark blue-gray


# Emoji mappings for visual enhancement
class Emoji:
    """Emoji constants for visual enhancement"""

    CARAT = "💎"
    GOLDEN_CARAT = "✨"
    BANK = "🏦"
    MONEY = "💰"
    CHART_UP = "📈"
    CHART_DOWN = "📉"
    CHART = "📊"
    TREASURY = "🏛️"
    USER = "👤"
    USERS = "👥"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    CLOCK = "🕐"
    DIAMOND = "💠"
    TRANSFER = "💸"
    EXCHANGE = "🔄"
    TRADE = "🤝"
    FIRE = "🔥"
    STAR = "⭐"
    CROWN = "👑"
    MEDAL_GOLD = "🥇"
    MEDAL_SILVER = "🥈"
    MEDAL_BRONZE = "🥉"
    LOCK = "🔒"
    UNLOCK = "🔓"
    MINT = "🪙"
    BOOK = "📖"
    PING = "🏓"
    INFO = "ℹ️"
    HELP = "❓"


def create_embed(
    title: str,
    description: str = None,
    color: int = Colors.INFO,
    footer: str = None,
    thumbnail: str = None,
) -> discord.Embed:
    """Create a styled embed with consistent formatting"""
    embed = discord.Embed(
        title=title, description=description, color=color, timestamp=datetime.utcnow()
    )
    if footer:
        embed.set_footer(text=footer, icon_url="https://i.imgur.com/placeholder.png")
    else:
        embed.set_footer(text="Arca Bank • Minecraft Economy")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


def error_embed(message: str) -> discord.Embed:
    """Create a standardized error embed"""
    return create_embed(title=f"{Emoji.CROSS} Error", description=message, color=Colors.ERROR)


def success_embed(title: str, description: str = None) -> discord.Embed:
    """Create a standardized success embed"""
    return create_embed(
        title=f"{Emoji.CHECK} {title}", description=description, color=Colors.SUCCESS
    )


# ==================== CONFIRMATION VIEWS ====================


class ResignConfirmView(ui.View):
    """Confirmation view for banker resignation"""

    def __init__(self, bank: ArcaBank, discord_id: str):
        super().__init__(timeout=60)
        self.bank = bank
        self.discord_id = discord_id
        self.confirmed = False

    @ui.button(label="Confirm Resignation", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Confirm resignation"""
        if str(interaction.user.id) != self.discord_id:
            await interaction.response.send_message(
                "You can only confirm your own resignation.", ephemeral=True
            )
            return

        result = self.bank.resign_as_banker(self.discord_id)

        if result.success:
            self.confirmed = True
            await interaction.response.edit_message(
                content="You have resigned as Banker. You are now a regular user.",
                view=None,
            )
        else:
            await interaction.response.edit_message(content=f"Error: {result.message}", view=None)
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel resignation"""
        if str(interaction.user.id) != self.discord_id:
            await interaction.response.send_message(
                "You can only cancel your own resignation.", ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="Resignation cancelled. You are still a Banker.", view=None
        )
        self.stop()

    async def on_timeout(self):
        """Handle timeout"""
        pass


class ArcaBankBot(commands.Bot):
    """Discord bot for Arca Bank"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)

        self.bank = ArcaBank()
        self.scheduler: Optional[MarketScheduler] = None

    async def setup_hook(self):
        """Called when bot is ready"""
        # Start market scheduler
        self.scheduler = start_scheduler()

        # Add event callbacks
        self.scheduler.add_callback("on_price_freeze", self._on_price_freeze)
        self.scheduler.add_callback("on_price_unfreeze", self._on_price_unfreeze)

        # Sync slash commands
        await self.tree.sync()
        print("Arca Bank Bot ready!")

    def _on_price_freeze(self, data):
        """Called when price is frozen"""
        # You can send alerts to a specific channel here
        print(f"ALERT: Price frozen at {data['frozen_price']}")

    def _on_price_unfreeze(self, data):
        """Called when price is unfrozen"""
        print(f"ALERT: Price unfrozen, now {data['current_price']}")


bot = ArcaBankBot()


# ==================== PUBLIC COMMANDS ====================


@bot.tree.command(name="balance", description="Check your Arca Bank balance")
async def balance(interaction: discord.Interaction):
    """Check user balance"""
    result = bot.bank.get_balance(str(interaction.user.id))

    if result.success:
        embed = create_embed(title=f"{Emoji.BANK} Your Balance", color=Colors.GOLD)
        embed.add_field(
            name=f"{Emoji.CARAT} Carats", value=f"```{result.data['carats']:,.2f} C```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.GOLDEN_CARAT} Golden Carats",
            value=f"```{result.data['golden_carats']:,.2f} GC```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.MONEY} Total Value",
            value=f"```{result.data['total_in_carats']:,.2f} C```",
            inline=False,
        )
        embed.add_field(
            name=f"{Emoji.INFO} Exchange Rate", value="1 Golden Carat = 9 Carats", inline=False
        )
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="register", description="Register with Arca Bank")
@app_commands.describe(minecraft_username="Your Minecraft username (optional)")
async def register(interaction: discord.Interaction, minecraft_username: Optional[str] = None):
    """Register a new user"""
    result = bot.bank.register_user(
        str(interaction.user.id), interaction.user.name, minecraft_username=minecraft_username
    )

    if result.success:
        embed = create_embed(
            title=f"{Emoji.BANK} Welcome to Arca Bank!",
            description=f"{Emoji.CHECK} {result.message}",
            color=Colors.SUCCESS,
        )
        embed.add_field(name=f"{Emoji.USER} Discord", value=interaction.user.mention, inline=True)
        if result.data.get("minecraft_username"):
            embed.add_field(
                name="⛏️ Minecraft", value=result.data["minecraft_username"], inline=True
            )
        embed.add_field(
            name=f"{Emoji.INFO} Getting Started",
            value="Use `/balance` to check your balance\nUse `/help` to see all commands",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="link", description="Link your Minecraft account")
@app_commands.describe(
    minecraft_uuid="Your Minecraft UUID", minecraft_username="Your Minecraft username"
)
async def link(interaction: discord.Interaction, minecraft_uuid: str, minecraft_username: str):
    """Link Minecraft account"""
    result = bot.bank.link_minecraft(str(interaction.user.id), minecraft_uuid, minecraft_username)

    if result.success:
        embed = success_embed(
            "Account Linked!", f"⛏️ Your Minecraft account **{minecraft_username}** has been linked."
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="transfer", description="Transfer currency to another user")
@app_commands.describe(
    recipient="The user to transfer to",
    amount="Amount to transfer",
    currency="Currency type (carat or golden_carat)",
)
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Carats", value="carat"),
        app_commands.Choice(name="Golden Carats", value="golden_carat"),
    ]
)
async def transfer(
    interaction: discord.Interaction,
    recipient: discord.Member,
    amount: float,
    currency: str = "carat",
):
    """Transfer currency"""
    result = bot.bank.transfer(str(interaction.user.id), str(recipient.id), amount, currency)

    if result.success:
        currency_emoji = Emoji.GOLDEN_CARAT if currency == "golden_carat" else Emoji.CARAT
        currency_name = "GC" if currency == "golden_carat" else "C"

        embed = create_embed(title=f"{Emoji.TRANSFER} Transfer Complete", color=Colors.SUCCESS)
        embed.add_field(
            name="💳 Sent",
            value=f"```{result.data['amount_sent']:,.2f} {currency_name}```",
            inline=True,
        )
        embed.add_field(
            name=f"{currency_emoji} Received",
            value=f"```{result.data['amount_received']:,.2f} {currency_name}```",
            inline=True,
        )
        embed.add_field(
            name="📋 Fee (1.5%)",
            value=f"```{result.data['fee']:,.2f} {currency_name}```",
            inline=True,
        )
        embed.add_field(name=f"{Emoji.USER} Recipient", value=recipient.mention, inline=False)
        embed.set_author(
            name=f"From: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="exchange", description="Exchange between Carats and Golden Carats")
@app_commands.describe(
    amount="Amount to exchange",
    from_currency="Currency to exchange from",
    to_currency="Currency to exchange to",
)
@app_commands.choices(
    from_currency=[
        app_commands.Choice(name="Carats", value="carat"),
        app_commands.Choice(name="Golden Carats", value="golden_carat"),
    ],
    to_currency=[
        app_commands.Choice(name="Carats", value="carat"),
        app_commands.Choice(name="Golden Carats", value="golden_carat"),
    ],
)
async def exchange(
    interaction: discord.Interaction, amount: float, from_currency: str, to_currency: str
):
    """Exchange currency"""
    result = bot.bank.exchange_currency(
        str(interaction.user.id), amount, from_currency, to_currency
    )

    if result.success:
        from_emoji = Emoji.GOLDEN_CARAT if from_currency == "golden_carat" else Emoji.CARAT
        to_emoji = Emoji.GOLDEN_CARAT if to_currency == "golden_carat" else Emoji.CARAT

        embed = create_embed(title=f"{Emoji.EXCHANGE} Exchange Complete", color=Colors.INFO)
        embed.add_field(
            name=f"{from_emoji} From",
            value=f"```{result.data['from_amount']:,.2f} {result.data['from_currency'].upper()}```",
            inline=True,
        )
        embed.add_field(
            name=f"{to_emoji} To",
            value=f"```{result.data['to_amount']:,.2f} {result.data['to_currency'].upper()}```",
            inline=True,
        )
        embed.add_field(name="📋 Fee (2%)", value=f"```{result.data['fee']:,.2f} C```", inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


# ==================== TREASURY COMMANDS ====================


@bot.tree.command(name="treasury", description="View treasury status")
async def treasury(interaction: discord.Interaction):
    """View treasury status"""
    result = bot.bank.get_treasury_status()

    if result.success:
        # Determine reserve health color
        reserve_ratio = result.data["reserve_ratio"]
        if reserve_ratio >= 80:
            color = Colors.SUCCESS
            status = f"{Emoji.CHECK} Healthy"
        elif reserve_ratio >= 50:
            color = Colors.WARNING
            status = f"{Emoji.WARNING} Moderate"
        else:
            color = Colors.ERROR
            status = f"{Emoji.CROSS} Low"

        embed = create_embed(
            title=f"{Emoji.TREASURY} Arca Treasury",
            description=f"**Status:** {status}",
            color=color,
        )
        embed.add_field(
            name=f"{Emoji.DIAMOND} Total Diamonds",
            value=f"```{result.data['total_diamonds']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.LOCK} Reserves",
            value=f"```{result.data['reserve_diamonds']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name="📊 Reserve Ratio", value=f"```{result.data['reserve_ratio']:.1f}%```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.CARAT} Carats Minted",
            value=f"```{result.data['total_carats_minted']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.GOLDEN_CARAT} Golden Carats",
            value=f"```{result.data['total_golden_carats_minted']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.BOOK} Book Value",
            value=f"```{result.data['book_value']:.4f}/C```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.MONEY} Circulation",
            value=f"```{result.data['total_circulation']:,.0f} C```",
            inline=True,
        )
        embed.add_field(
            name="💰 Fees Collected",
            value=f"```{result.data['accumulated_fees']:,.2f} C```",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="history", description="View treasury transaction history")
@app_commands.describe(days="Number of days to look back")
async def history(interaction: discord.Interaction, days: int = 30):
    """View treasury history"""
    result = bot.bank.get_treasury_history(days=days)

    if result.success:
        summary = result.data["summary"]

        # Determine net flow color
        net_positive = summary["net_diamonds"] >= 0
        color = Colors.SUCCESS if net_positive else Colors.WARNING

        embed = create_embed(title=f"{Emoji.CLOCK} Treasury History ({days} days)", color=color)

        # Diamond flows
        embed.add_field(
            name=f"{Emoji.DIAMOND} Diamond Inflow",
            value=f"```diff\n+{summary['inflow_diamonds']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.DIAMOND} Diamond Outflow",
            value=f"```diff\n-{summary['outflow_diamonds']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name="Net",
            value=f"```{'diff' if summary['net_diamonds'] != 0 else ''}\n{summary['net_diamonds']:+,.0f}```",
            inline=True,
        )

        # Carat flows
        embed.add_field(
            name=f"{Emoji.CARAT} Carat Inflow",
            value=f"```diff\n+{summary['inflow_carats']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.CARAT} Carat Outflow",
            value=f"```diff\n-{summary['outflow_carats']:,.0f}```",
            inline=True,
        )
        embed.add_field(name="Net", value=f"```{summary['net_carats']:+,.0f}```", inline=True)

        # Summary
        embed.add_field(
            name="💰 Total Fees", value=f"```{summary['total_fees']:,.2f} C```", inline=True
        )
        embed.add_field(
            name="📋 Transactions", value=f"```{summary['transaction_count']}```", inline=True
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


# ==================== MARKET COMMANDS ====================


@bot.tree.command(name="market", description="View current market status")
async def market(interaction: discord.Interaction):
    """View market status"""
    result = bot.bank.get_market_status()

    if result.success:
        # Determine status color
        status = result.data["circulation_status"]
        color = {
            "healthy": Colors.SUCCESS,
            "low": Colors.WARNING,
            "frozen": Colors.ERROR,
            "critical": Colors.ERROR,
        }.get(status, Colors.INFO)

        status_emoji = {
            "healthy": Emoji.CHECK,
            "low": Emoji.WARNING,
            "frozen": Emoji.LOCK,
            "critical": Emoji.CROSS,
        }.get(status, Emoji.INFO)

        embed = create_embed(title=f"{Emoji.CHART} Arca Market", color=color)

        # Price info
        price = result.data["effective_price"]
        embed.add_field(name=f"{Emoji.CARAT} Carat Price", value=f"```{price:.4f}```", inline=True)
        embed.add_field(
            name="📊 Index", value=f"```{result.data['current_index']:.2f}```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.CLOCK} Delayed Avg",
            value=f"```{result.data['delayed_average']:.2f}```",
            inline=True,
        )

        # Changes with color indicators
        change_24h = result.data["change_24h"]
        change_emoji = Emoji.CHART_UP if change_24h >= 0 else Emoji.CHART_DOWN

        embed.add_field(
            name="1H Change", value=f"```diff\n{result.data['change_1h']:+.2f}%```", inline=True
        )
        embed.add_field(
            name=f"24H Change {change_emoji}", value=f"```diff\n{change_24h:+.2f}%```", inline=True
        )
        embed.add_field(
            name="7D Change", value=f"```diff\n{result.data['change_7d']:+.2f}%```", inline=True
        )

        # Volume
        embed.add_field(
            name=f"{Emoji.MONEY} 24H Volume",
            value=f"```{result.data['volume_24h']:,.0f} C```",
            inline=True,
        )
        embed.add_field(
            name="📋 Transactions",
            value=f"```{result.data['transaction_count_24h']}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.USERS} Circulation",
            value=f"```{result.data['total_circulation']:,.0f} C```",
            inline=True,
        )

        # Status
        status_text = f"{status_emoji} **{status.upper()}**"
        if result.data["is_price_frozen"]:
            status_text += f" (Frozen at {result.data['frozen_price']:.4f})"
        embed.add_field(name="Status", value=status_text, inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="chart", description="View market price chart")
@app_commands.describe(days="Number of days to display")
async def chart(interaction: discord.Interaction, days: int = 7):
    """View market chart"""
    await interaction.response.defer()  # Chart generation takes time

    chart_data = bot.bank.get_market_chart(days=days)

    if isinstance(chart_data, bytes):
        file = discord.File(io.BytesIO(chart_data), filename="market_chart.png")
        await interaction.followup.send(file=file)
    else:
        await interaction.followup.send(f"Error: {chart_data.message}")


@bot.tree.command(name="treasurychart", description="View treasury health chart")
@app_commands.describe(days="Number of days to display")
async def treasurychart(interaction: discord.Interaction, days: int = 30):
    """View treasury chart"""
    await interaction.response.defer()

    chart_data = bot.bank.get_treasury_chart(days=days)

    if isinstance(chart_data, bytes):
        file = discord.File(io.BytesIO(chart_data), filename="treasury_chart.png")
        await interaction.followup.send(file=file)
    else:
        await interaction.followup.send(f"Error: {chart_data.message}")


@bot.tree.command(
    name="advancedchart", description="View advanced stock-style chart with indicators"
)
@app_commands.describe(
    days="Number of days to display (default: 30)", chart_type="Chart type: candlestick or line"
)
@app_commands.choices(
    chart_type=[
        app_commands.Choice(name="Candlestick", value="candlestick"),
        app_commands.Choice(name="Line", value="line"),
    ]
)
async def advancedchart(
    interaction: discord.Interaction, days: int = 30, chart_type: str = "candlestick"
):
    """
    View advanced stock-style chart
    Features: Candlesticks, Moving Averages, Bollinger Bands, RSI, Volume
    """
    await interaction.response.defer()

    chart_data = bot.bank.get_advanced_chart(days=days, chart_type=chart_type)

    if isinstance(chart_data, bytes):
        file = discord.File(io.BytesIO(chart_data), filename="advanced_chart.png")
        embed = discord.Embed(
            title="Advanced Market Chart",
            description=f"**{days}-day {chart_type} chart** with technical indicators\n"
            "- Moving Averages (7d, 21d)\n"
            "- Bollinger Bands\n"
            "- RSI (Relative Strength Index)\n"
            "- Volume bars",
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://advanced_chart.png")
        await interaction.followup.send(embed=embed, file=file)
    else:
        await interaction.followup.send(f"Error: {chart_data.message}")


@bot.tree.command(name="marketoverview", description="View multi-timeframe market overview")
async def marketoverview(interaction: discord.Interaction):
    """
    View market performance across multiple timeframes
    Shows 1D, 7D, 30D, and 90D at a glance
    """
    await interaction.response.defer()

    chart_data = bot.bank.get_multi_timeframe_chart()

    if isinstance(chart_data, bytes):
        file = discord.File(io.BytesIO(chart_data), filename="market_overview.png")
        embed = discord.Embed(
            title="Market Overview",
            description="Performance across multiple timeframes: 1D, 7D, 30D, 90D",
            color=discord.Color.gold(),
        )
        embed.set_image(url="attachment://market_overview.png")
        await interaction.followup.send(embed=embed, file=file)
    else:
        await interaction.followup.send(f"Error: {chart_data.message}")


# ==================== BANKER COMMANDS ====================


@bot.tree.command(name="deposit", description="[BANKER] Deposit diamonds and issue carats")
@app_commands.describe(
    user="User to issue carats to",
    diamonds="Amount of diamonds deposited",
    carats="Amount of carats to issue",
)
async def deposit(
    interaction: discord.Interaction, user: discord.Member, diamonds: float, carats: float
):
    """Banker deposit command"""
    result = bot.bank.deposit(
        str(interaction.user.id),
        str(user.id),
        diamonds,
        carats,
        f"Deposit by {interaction.user.name}",
    )

    if result.success:
        embed = create_embed(title=f"{Emoji.BANK} Deposit Complete", color=Colors.SUCCESS)
        embed.add_field(
            name=f"{Emoji.DIAMOND} Diamonds",
            value=f"```{result.data['diamonds_deposited']:,.0f}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emoji.CARAT} Carats Issued",
            value=f"```{result.data['carats_issued']:,.0f} C```",
            inline=True,
        )
        embed.add_field(name=f"{Emoji.USER} Recipient", value=user.mention, inline=False)
        embed.add_field(
            name=f"{Emoji.BOOK} New Book Value",
            value=f"```{result.data['new_book_value']:.4f}/C```",
            inline=True,
        )
        embed.set_author(
            name=f"Banker: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="atmprofit", description="[BANKER] Record ATM book profits")
@app_commands.describe(books="Number of books received (90 diamonds each)")
async def atmprofit(interaction: discord.Interaction, books: int):
    """Record ATM profit"""
    result = bot.bank.record_atm_profit(
        str(interaction.user.id), books, f"ATM profit recorded by {interaction.user.name}"
    )

    if result.success:
        embed = create_embed(title=f"{Emoji.BOOK} ATM Profit Recorded", color=Colors.SUCCESS)
        embed.add_field(name="📚 Books", value=f"```{result.data['books']}```", inline=True)
        embed.add_field(
            name=f"{Emoji.DIAMOND} Diamonds", value=f"```{result.data['diamonds']}```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.BOOK} New Book Value",
            value=f"```{result.data['new_book_value']:.4f}/C```",
            inline=True,
        )
        embed.set_footer(text="90 diamonds per book")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


# ==================== HEAD BANKER COMMANDS ====================


@bot.tree.command(
    name="mintcheck", description="[HEAD BANKER] Check if minting/burning is recommended"
)
@app_commands.describe(atm_books="Expected ATM books to receive")
async def mintcheck(interaction: discord.Interaction, atm_books: int = 0):
    """Mint check recommendation"""
    result = bot.bank.mint_check(str(interaction.user.id), atm_books)

    if result.success:
        action = result.data["action"]
        action_emoji = {"mint": Emoji.MINT, "burn": Emoji.FIRE, "hold": Emoji.CLOCK}.get(
            action, Emoji.INFO
        )
        color = {"mint": Colors.SUCCESS, "burn": Colors.WARNING, "hold": Colors.INFO}.get(
            action, Colors.INFO
        )

        embed = create_embed(
            title=f"{action_emoji} Mint Check: {action.upper()}",
            description=result.data["reason"],
            color=color,
        )

        if result.data["amount"] > 0:
            embed.add_field(
                name="📋 Recommended Amount",
                value=f"```{result.data['amount']:,.2f} C```",
                inline=False,
            )

        embed.add_field(
            name="Current Book Value",
            value=f"```{result.data['current_book_value']:.4f}```",
            inline=True,
        )
        embed.add_field(
            name="Target Book Value",
            value=f"```{result.data['target_book_value']:.4f}```",
            inline=True,
        )
        embed.add_field(
            name="Confidence", value=f"```{result.data['confidence'].upper()}```", inline=True
        )

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="mint", description="[HEAD BANKER] Mint new currency")
@app_commands.describe(amount="Amount to mint", currency="Currency type")
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Carats", value="carat"),
        app_commands.Choice(name="Golden Carats", value="golden_carat"),
    ]
)
async def mint(interaction: discord.Interaction, amount: float, currency: str = "carat"):
    """Mint currency"""
    result = bot.bank.mint(
        str(interaction.user.id), amount, currency, f"Minted by {interaction.user.name}"
    )

    if result.success:
        currency_emoji = Emoji.GOLDEN_CARAT if currency == "golden_carat" else Emoji.CARAT
        embed = create_embed(title=f"{Emoji.MINT} Currency Minted", color=Colors.SUCCESS)
        embed.add_field(
            name=f"{currency_emoji} Amount",
            value=f"```{result.data['amount']:,.2f}```",
            inline=True,
        )
        embed.add_field(
            name="Currency", value=f"```{result.data['currency'].upper()}```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.BOOK} New Book Value",
            value=f"```{result.data['new_book_value']:.4f}/C```",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="burn", description="[HEAD BANKER] Burn currency from supply")
@app_commands.describe(amount="Amount to burn", currency="Currency type")
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Carats", value="carat"),
        app_commands.Choice(name="Golden Carats", value="golden_carat"),
    ]
)
async def burn(interaction: discord.Interaction, amount: float, currency: str = "carat"):
    """Burn currency"""
    result = bot.bank.burn(
        str(interaction.user.id), amount, currency, f"Burned by {interaction.user.name}"
    )

    if result.success:
        currency_emoji = Emoji.GOLDEN_CARAT if currency == "golden_carat" else Emoji.CARAT
        embed = create_embed(title=f"{Emoji.FIRE} Currency Burned", color=Colors.WARNING)
        embed.add_field(
            name=f"{currency_emoji} Amount",
            value=f"```{result.data['amount']:,.2f}```",
            inline=True,
        )
        embed.add_field(
            name="Currency", value=f"```{result.data['currency'].upper()}```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.BOOK} New Book Value",
            value=f"```{result.data['new_book_value']:.4f}/C```",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="promote", description="[HEAD BANKER] Promote user to banker")
@app_commands.describe(user="User to promote")
async def promote(interaction: discord.Interaction, user: discord.Member):
    """Promote to banker"""
    result = bot.bank.promote_to_banker(str(interaction.user.id), str(user.id))

    if result.success:
        embed = success_embed(
            "User Promoted!", f"{Emoji.CROWN} {user.mention} has been promoted to **Banker**."
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="resign", description="[BANKER] Resign from your banker position")
async def resign(interaction: discord.Interaction):
    """Resign from banker position (requires confirmation)"""
    # First check if user is a banker
    result = bot.bank.get_balance(str(interaction.user.id))

    if not result.success:
        await interaction.response.send_message(f"Error: {result.message}", ephemeral=True)
        return

    # Check their role
    role = result.data.get("role", "user")
    if role == "head_banker":
        await interaction.response.send_message(
            "Head Bankers cannot resign through this command.", ephemeral=True
        )
        return
    if role != "banker":
        await interaction.response.send_message(
            "Only bankers can use this command.", ephemeral=True
        )
        return

    # Show confirmation
    view = ResignConfirmView(bot.bank, str(interaction.user.id))
    await interaction.response.send_message(
        "**Are you sure you want to resign as Banker?**\n\n"
        "This action will:\n"
        "- Remove your banker permissions\n"
        "- Demote you to regular user\n\n"
        "This cannot be undone without Head Banker approval.",
        view=view,
        ephemeral=True,
    )


@bot.tree.command(name="freezeprice", description="[HEAD BANKER] Freeze market price")
@app_commands.describe(price="Price to freeze at (optional)")
async def freezeprice(interaction: discord.Interaction, price: Optional[float] = None):
    """Freeze price"""
    result = bot.bank.freeze_price(str(interaction.user.id), price)

    if result.success:
        await interaction.response.send_message(f"Frozen: {result.message}")
    else:
        await interaction.response.send_message(f"Error: {result.message}", ephemeral=True)


@bot.tree.command(name="unfreezeprice", description="[HEAD BANKER] Unfreeze market price")
async def unfreezeprice(interaction: discord.Interaction):
    """Unfreeze price"""
    result = bot.bank.unfreeze_price(str(interaction.user.id))

    if result.success:
        await interaction.response.send_message(f"Unfrozen: {result.message}")
    else:
        await interaction.response.send_message(f"Error: {result.message}", ephemeral=True)


# ==================== TRADE COMMANDS ====================


@bot.tree.command(name="reporttrade", description="Report a trade you made")
@app_commands.describe(
    trade_type="Type of trade",
    item_name="Name of item traded",
    quantity="Number of items",
    carats="Amount of Carats",
    golden_carats="Amount of Golden Carats (optional)",
    counterparty="Who you traded with (optional)",
)
@app_commands.choices(
    trade_type=[
        app_commands.Choice(name="Buy", value="BUY"),
        app_commands.Choice(name="Sell", value="SELL"),
        app_commands.Choice(name="Exchange", value="EXCHANGE"),
    ]
)
async def reporttrade(
    interaction: discord.Interaction,
    trade_type: str,
    item_name: str,
    quantity: int,
    carats: float,
    golden_carats: Optional[float] = 0.0,
    counterparty: Optional[str] = None,
):
    """Report a trade"""
    result = bot.bank.report_trade(
        discord_id=str(interaction.user.id),
        trade_type=trade_type,
        item_name=item_name,
        item_quantity=quantity,
        carat_amount=carats,
        golden_carat_amount=golden_carats or 0.0,
        counterparty_name=counterparty,
    )

    if result.success:
        type_emoji = {"BUY": "🟢", "SELL": "🔴", "EXCHANGE": "🔵"}.get(trade_type, Emoji.TRADE)
        embed = create_embed(title=f"{Emoji.TRADE} Trade Reported", color=Colors.SUCCESS)
        embed.add_field(name="🆔 Trade ID", value=f"```#{result.data['trade_id']}```", inline=True)
        embed.add_field(
            name=f"{type_emoji} Type", value=f"```{result.data['trade_type']}```", inline=True
        )
        embed.add_field(name="📦 Item", value=f"```{quantity}x {item_name}```", inline=True)
        embed.add_field(
            name=f"{Emoji.CARAT} Price/Item",
            value=f"```{result.data['price_per_item']:.4f} C```",
            inline=True,
        )
        if counterparty:
            embed.add_field(
                name=f"{Emoji.USER} Traded With", value=f"```{counterparty}```", inline=True
            )
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="mytrades", description="View your recent trades")
@app_commands.describe(limit="Number of trades to show")
async def mytrades(interaction: discord.Interaction, limit: Optional[int] = 10):
    """View user's trades"""
    result = bot.bank.get_my_trades(str(interaction.user.id), limit=min(limit, 25))

    if result.success:
        trades = result.data.get("trades", [])
        if not trades:
            embed = create_embed(
                title=f"{Emoji.TRADE} Your Trades",
                description="You haven't reported any trades yet.\nUse `/reporttrade` to report your first trade!",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(title=f"{Emoji.TRADE} Your Recent Trades", color=Colors.INFO)

        for trade in trades[:10]:
            status = f"{Emoji.CHECK}" if trade["verified"] else "⏳"
            type_emoji = {"BUY": "🟢", "SELL": "🔴", "EXCHANGE": "🔵"}.get(trade["type"], "❓")
            value = f"{type_emoji} {trade['quantity']}x - **{trade['carats']:.2f}C**"
            if trade.get("counterparty"):
                value += f"\n└ with `{trade['counterparty']}`"
            embed.add_field(name=f"{status} {trade['item'][:25]}", value=value, inline=False)

        embed.set_footer(text=f"Showing {len(trades)} trades • {Emoji.CHECK} = Verified")
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="mystats", description="View your trading statistics")
async def mystats(interaction: discord.Interaction):
    """View user's trading stats"""
    result = bot.bank.get_my_trader_stats(str(interaction.user.id))

    if result.success:
        data = result.data
        if data.get("total_trades", 0) == 0:
            embed = create_embed(
                title=f"{Emoji.CHART} Your Trading Stats",
                description="You don't have any trading history yet.\nStart trading to build your reputation!",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        # Determine reputation color
        rep = data["reputation_score"]
        if rep >= 80:
            color = Colors.SUCCESS
            rep_status = f"{Emoji.STAR} Excellent"
        elif rep >= 50:
            color = Colors.WARNING
            rep_status = f"{Emoji.CHECK} Good"
        else:
            color = Colors.ERROR
            rep_status = f"{Emoji.WARNING} Building"

        embed = create_embed(title=f"{Emoji.CHART} Your Trading Stats", color=color)
        embed.add_field(name="📊 Total Trades", value=f"```{data['total_trades']}```", inline=True)
        embed.add_field(name="🟢 Buys", value=f"```{data['buy_count']}```", inline=True)
        embed.add_field(name="🔴 Sells", value=f"```{data['sell_count']}```", inline=True)
        embed.add_field(
            name=f"{Emoji.MONEY} Total Volume",
            value=f"```{data['total_volume']:,.2f} C```",
            inline=True,
        )
        embed.add_field(
            name="📋 Avg Trade", value=f"```{data['average_trade_size']:.2f} C```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.CHECK} Verified", value=f"```{data['verified_trades']}```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.STAR} Reputation",
            value=f"{rep_status}\n```{data['reputation_score']:.1f}%```",
            inline=False,
        )
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="itemprice", description="Check market price for an item")
@app_commands.describe(item_name="Name of the item")
async def itemprice(interaction: discord.Interaction, item_name: str):
    """Check item price"""
    result = bot.bank.get_item_price(item_name)

    if result.success:
        data = result.data
        if not data.get("found"):
            embed = create_embed(
                title=f"{Emoji.CROSS} Item Not Found",
                description=f"No price data found for: **{item_name}**\n\nTry reporting trades with `/reporttrade` to add price data.",
                color=Colors.WARNING,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = create_embed(title=f"📦 {data['item_name']}", color=Colors.TEAL)
        embed.add_field(name="🏷️ Category", value=f"```{data['category']}```", inline=True)
        embed.add_field(
            name=f"{Emoji.CARAT} Price", value=f"```{data['current_price']:.4f} C```", inline=True
        )
        embed.add_field(
            name=f"{Emoji.MONEY} 24h Volume", value=f"```{data['volume_24h']:.2f} C```", inline=True
        )
        embed.add_field(
            name="📋 Trades (24h)", value=f"```{data['trade_count_24h']}```", inline=True
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="trending", description="View trending items by trading volume")
async def trending(interaction: discord.Interaction):
    """View trending items"""
    result = bot.bank.get_trending_items(limit=10)

    if result.success:
        items = result.data.get("items", [])
        if not items:
            embed = create_embed(
                title=f"{Emoji.FIRE} Trending Items",
                description="No trending items yet.\nStart trading to see market activity!",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(title=f"{Emoji.FIRE} Trending Items (24h)", color=Colors.WARNING)

        for i, item in enumerate(items[:10], 1):
            medal = (
                Emoji.MEDAL_GOLD
                if i == 1
                else Emoji.MEDAL_SILVER if i == 2 else Emoji.MEDAL_BRONZE if i == 3 else f"`{i}.`"
            )
            embed.add_field(
                name=f"{medal} {item['item_name'][:25]}",
                value=f"{Emoji.CARAT} {item['current_price']:.2f}C\n📊 Vol: {item['volume_24h']:,.0f}",
                inline=True,
            )

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="verifytrade", description="[BANKER] Verify a trade report")
@app_commands.describe(trade_id="ID of the trade to verify")
async def verifytrade(interaction: discord.Interaction, trade_id: int):
    """Verify a trade"""
    result = bot.bank.verify_trade(str(interaction.user.id), trade_id)

    if result.success:
        await interaction.response.send_message(f"Trade #{trade_id} verified!")
    else:
        await interaction.response.send_message(f"Error: {result.message}", ephemeral=True)


@bot.tree.command(name="traderreport", description="[HEAD BANKER] Get report on a trader")
@app_commands.describe(user="The trader to get a report on")
async def traderreport(interaction: discord.Interaction, user: discord.Member):
    """Get trader report"""
    result = bot.bank.get_trader_report(str(interaction.user.id), str(user.id))

    if result.success:
        data = result.data
        embed = discord.Embed(
            title=f"Trader Report: {data['minecraft_username']}", color=discord.Color.dark_blue()
        )
        embed.add_field(name="Role", value=data["role"])
        embed.add_field(name="Total Trades", value=str(data["total_trades"]))
        embed.add_field(name="Volume", value=f"{data['total_volume']:.2f} C")
        embed.add_field(name="Buys", value=str(data["buy_count"]))
        embed.add_field(name="Sells", value=str(data["sell_count"]))
        embed.add_field(name="Avg Trade", value=f"{data['average_trade_size']:.2f} C")
        embed.add_field(name="Verified", value=str(data["verified_trades"]))
        embed.add_field(name="Reputation", value=f"{data['reputation_score']:.1f}%")

        if data.get("recent_trades"):
            recent = "\n".join(
                [
                    f"- {t['type']} {t['item'][:15]}: {t['amount']:.2f}C"
                    for t in data["recent_trades"][:5]
                ]
            )
            embed.add_field(name="Recent Trades", value=recent, inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error: {result.message}", ephemeral=True)


@bot.tree.command(name="alltraders", description="[HEAD BANKER] Get summary of all traders")
async def alltraders(interaction: discord.Interaction):
    """Get all trader reports"""
    result = bot.bank.get_all_trader_reports(str(interaction.user.id), limit=20)

    if result.success:
        traders = result.data.get("traders", [])
        if not traders:
            embed = create_embed(
                title=f"{Emoji.USERS} All Traders Report",
                description="No traders found.",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(title=f"{Emoji.USERS} All Traders Report", color=Colors.GOLD)

        for trader in traders[:15]:
            if trader["reputation"] >= 80:
                rep_marker = Emoji.STAR
            elif trader["reputation"] >= 50:
                rep_marker = Emoji.CHECK
            else:
                rep_marker = Emoji.WARNING
            embed.add_field(
                name=f"{rep_marker} {trader['minecraft_username'][:20]}",
                value=f"📊 {trader['total_trades']} trades\n{Emoji.MONEY} {trader['total_volume']:,.0f}C",
                inline=True,
            )

        embed.set_footer(text=f"Showing top {len(traders)} traders by volume")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="setconsumer", description="[HEAD BANKER] Set user to consumer (read-only)")
@app_commands.describe(user="User to set as consumer")
async def setconsumer(interaction: discord.Interaction, user: discord.Member):
    """Set user to consumer role"""
    result = bot.bank.set_consumer(str(interaction.user.id), str(user.id))

    if result.success:
        embed = success_embed(
            "Role Updated", f"{user.mention} has been set to **Consumer** (read-only access)."
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="toptraders", description="View top traders by volume")
async def toptraders(interaction: discord.Interaction):
    """View top traders"""
    result = bot.bank.get_top_traders(limit=10, days=30)

    if result.success:
        traders = result.data.get("traders", [])
        if not traders:
            embed = create_embed(
                title=f"{Emoji.CROWN} Top Traders",
                description="No traders found yet.\nBe the first to trade!",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(title=f"{Emoji.CROWN} Top Traders (30 days)", color=Colors.GOLD)

        for i, trader in enumerate(traders[:10], 1):
            medal = (
                Emoji.MEDAL_GOLD
                if i == 1
                else Emoji.MEDAL_SILVER if i == 2 else Emoji.MEDAL_BRONZE if i == 3 else f"`{i}.`"
            )
            embed.add_field(
                name=f"{medal} {trader['username'][:20]}",
                value=f"📊 {trader['trade_count']} trades\n{Emoji.MONEY} {trader['total_volume']:,.0f}C",
                inline=True,
            )

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


# ==================== UTILITY COMMANDS ====================


@bot.tree.command(name="help", description="View all Arca Bank commands")
async def help_command(interaction: discord.Interaction):
    """Display help information"""
    embed = create_embed(
        title=f"{Emoji.HELP} Arca Bank Commands",
        description="A complete economy management system for Minecraft servers.",
        color=Colors.INFO,
    )

    # Public Commands
    embed.add_field(
        name=f"{Emoji.USER} __Public Commands__",
        value=(
            "`/register` - Register with Arca Bank\n"
            "`/balance` - Check your balance\n"
            "`/link` - Link your Minecraft account\n"
            "`/transfer` - Transfer currency to another user\n"
            "`/exchange` - Exchange Carats ↔ Golden Carats"
        ),
        inline=False,
    )

    # Market Commands
    embed.add_field(
        name=f"{Emoji.CHART} __Market Commands__",
        value=(
            "`/market` - View market status\n"
            "`/treasury` - View treasury status\n"
            "`/history` - View treasury history\n"
            "`/chart` - View price chart\n"
            "`/advancedchart` - Technical analysis chart\n"
            "`/marketoverview` - Multi-timeframe overview"
        ),
        inline=False,
    )

    # Trading Commands
    embed.add_field(
        name=f"{Emoji.TRADE} __Trading Commands__",
        value=(
            "`/reporttrade` - Report a trade\n"
            "`/mytrades` - View your trades\n"
            "`/mystats` - Your trading statistics\n"
            "`/itemprice` - Check item prices\n"
            "`/trending` - View trending items\n"
            "`/toptraders` - View top traders"
        ),
        inline=False,
    )

    # Banker Commands
    embed.add_field(
        name=f"{Emoji.BANK} __Banker Commands__",
        value=(
            "`/deposit` - Deposit diamonds and issue carats\n"
            "`/atmprofit` - Record ATM profits\n"
            "`/verifytrade` - Verify trade reports\n"
            "`/resign` - Resign as banker"
        ),
        inline=False,
    )

    # Head Banker Commands
    embed.add_field(
        name=f"{Emoji.CROWN} __Head Banker Commands__",
        value=(
            "`/mint` - Mint new currency\n"
            "`/burn` - Burn currency from supply\n"
            "`/mintcheck` - Get minting recommendation\n"
            "`/promote` - Promote user to banker\n"
            "`/setconsumer` - Set user to read-only\n"
            "`/freezeprice` / `/unfreezeprice` - Control prices\n"
            "`/traderreport` - Get trader report\n"
            "`/alltraders` - View all traders"
        ),
        inline=False,
    )

    embed.set_footer(text="Use /ping to check bot status • 1 GC = 9 C")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Check bot latency and status")
async def ping(interaction: discord.Interaction):
    """Check bot status"""
    latency = round(bot.latency * 1000)

    # Determine status color based on latency
    if latency < 100:
        color = Colors.SUCCESS
        status = "Excellent"
    elif latency < 200:
        color = Colors.WARNING
        status = "Good"
    else:
        color = Colors.ERROR
        status = "Slow"

    embed = create_embed(title=f"{Emoji.PING} Pong!", color=color)
    embed.add_field(name="Latency", value=f"```{latency}ms```", inline=True)
    embed.add_field(name="Status", value=f"```{status}```", inline=True)
    embed.add_field(
        name="Scheduler",
        value=f"```{'Running' if bot.scheduler and bot.scheduler.is_running else 'Stopped'}```",
        inline=True,
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="View the richest users")
async def leaderboard(interaction: discord.Interaction):
    """View wealth leaderboard"""
    result = bot.bank.get_leaderboard(limit=10)

    if result.success:
        users = result.data.get("users", [])
        if not users:
            embed = create_embed(
                title=f"{Emoji.CROWN} Wealth Leaderboard",
                description="No users found yet.\nRegister with `/register` to get started!",
                color=Colors.INFO,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(
            title=f"{Emoji.CROWN} Wealth Leaderboard",
            description="Top 10 richest users by total value",
            color=Colors.GOLD,
        )

        for i, user in enumerate(users[:10], 1):
            medal = (
                Emoji.MEDAL_GOLD
                if i == 1
                else Emoji.MEDAL_SILVER if i == 2 else Emoji.MEDAL_BRONZE if i == 3 else f"`{i}.`"
            )
            embed.add_field(
                name=f"{medal} {user['username'][:20]}",
                value=f"{Emoji.MONEY} **{user['total_value']:,.2f}C**\n{Emoji.CARAT} {user['carats']:,.0f} | {Emoji.GOLDEN_CARAT} {user['golden_carats']:,.1f}",
                inline=True,
            )

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=error_embed(result.message), ephemeral=True)


@bot.tree.command(name="about", description="Learn about Arca Bank")
async def about(interaction: discord.Interaction):
    """Display information about Arca Bank"""
    embed = create_embed(
        title=f"{Emoji.BANK} About Arca Bank",
        description=(
            "Arca Bank is a comprehensive economy management system "
            "designed for Minecraft servers.\n\n"
            "**Features:**\n"
            f"{Emoji.CARAT} Dual currency system (Carats & Golden Carats)\n"
            f"{Emoji.DIAMOND} Diamond-backed treasury\n"
            f"{Emoji.CHART} Real-time market tracking\n"
            f"{Emoji.TRADE} Trade reporting and verification\n"
            f"{Emoji.CROWN} Role-based permissions\n"
            f"📊 Advanced chart generation"
        ),
        color=Colors.GOLD,
    )

    embed.add_field(
        name=f"{Emoji.INFO} Exchange Rate", value="**1 Golden Carat = 9 Carats**", inline=True
    )

    embed.add_field(
        name="📋 Fee Structure", value="Transfer: 1.5%\nExchange: 2.0%\nWithdraw: 1.0%", inline=True
    )

    embed.add_field(
        name=f"{Emoji.USERS} Roles", value="Consumer → User → Banker → Head Banker", inline=True
    )

    embed.set_footer(text="Use /help to see all commands")
    await interaction.response.send_message(embed=embed)


# ==================== RUN BOT ====================


def run_bot():
    """Run the Discord bot"""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    bot.run(token)


if __name__ == "__main__":
    run_bot()
