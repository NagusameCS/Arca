# Arca Bank - Minecraft Economy System

A comprehensive economic backend system for Minecraft servers, featuring a Discord bot integration and a Fabric client mod for in-game price checking and trade reporting.

## Overview

Arca Bank provides a complete currency management system with:
- **Dual Currency System**: Carats (C) and Golden Carats (GC) with a 9:1 ratio
- **Central Treasury**: Diamond-backed currency with book value tracking
- **Market System**: Real-time price tracking, delayed averages, and circulation monitoring
- **Role-Based Permissions**: Consumer (read-only), User (trade), Banker (write), Head Banker (admin)
- **ATM Integration**: Book profit system at 90 diamonds per book
- **Chart Generation**: Stock-style market visualizations
- **Trade Reporting**: Track trades, prices, and trader reputation
- **Java Mod**: In-game keybind for price checks and trade reporting

## Currency System

### Exchange Rates
- **1 Golden Carat (GC) = 9 Carats (C)**
- Carats are backed by diamonds in the treasury
- Book value = Total Diamonds / Total Carats in Circulation

### Fees (Arca's Profit)
| Operation | Fee Rate |
|-----------|----------|
| Transfers | 1.5% |
| Currency Exchange | 2.0% |
| Withdrawals | 1.0% |

## Permission Levels

| Role | Level | Permissions |
|------|-------|-------------|
| **Consumer** | -1 | View balance, market, treasury (read-only) |
| **User** | 0 | All consumer + transfers, exchanges, trade reporting |
| **Banker** | 1 | All user + deposits, ATM profits, verify trades |
| **Head Banker** | 2 | All banker + mint/burn, promote users, freeze prices, trader reports |

## Market Features

- **Real-time Index**: Updates every 15 minutes (configurable)
- **Delayed Average**: 24-hour rolling average to prevent manipulation
- **Circulation Monitor**: Automatic price freeze if circulation falls below threshold
- **OHLC Charts**: Candlestick and line charts for market visualization
- **Item Price Tracking**: Market prices derived from trade reports
- **Trending Items**: Track most traded items by volume

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/arca-bank.git
cd arca-bank

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### 2. Configuration

Edit `.env` with your settings:
```env
DISCORD_TOKEN=your_bot_token
ARCA_DATABASE_URL=sqlite:///arca_bank.db
```

### 3. Run the Bot

```bash
python bot.py
```

### 4. Run the REST API (for Java mod)

```bash
python run_api.py
# Or manually:
uvicorn src.integration.java_interface:create_fastapi_app --host 0.0.0.0 --port 8080
```

## Project Structure

```
arca-bank/
├── src/
│   ├── config.py              # Economic configuration
│   ├── models/                # Database models
│   │   ├── base.py           # SQLAlchemy setup
│   │   ├── user.py           # User & roles
│   │   ├── currency.py       # Currency balances
│   │   ├── treasury.py       # Treasury & transactions
│   │   ├── market.py         # Market data
│   │   └── trade.py          # Trade reports & stats
│   ├── services/             # Business logic
│   │   ├── user_service.py
│   │   ├── currency_service.py
│   │   ├── treasury_service.py
│   │   ├── market_service.py
│   │   ├── mint_service.py
│   │   ├── chart_service.py
│   │   └── trade_service.py  # Trade reporting
│   ├── api/                  # External interfaces
│   │   ├── bank_api.py       # Main API class
│   │   └── scheduler.py      # Background tasks
│   └── integration/          # Mod integration
│       └── java_interface.py # Java mod REST API
├── mod/                      # Fabric Minecraft mod
│   ├── build.gradle
│   └── src/main/java/com/arcabank/
├── bot.py                    # Discord bot
└── requirements.txt
```
├── .env.example
└── README.md
```

## Discord Commands

### Public Commands
| Command | Description |
|---------|-------------|
| `/register` | Register with Arca Bank |
| `/link` | Link your Minecraft account |
| `/balance` | Check your balance |
| `/transfer @user 100 carat` | Transfer currency |
| `/exchange 9 carat golden_carat` | Exchange currencies |
| `/treasury` | View treasury status |
| `/market` | View market status |
| `/chart 7` | View 7-day market chart |
| `/advancedchart 30` | View advanced stock-style chart with indicators |
| `/marketoverview` | View multi-timeframe market overview (1D/7D/30D/90D) |
| `/history 30` | View 30-day transaction history |

### Trade Commands
| Command | Description |
|---------|-------------|
| `/reporttrade` | Report a trade (BUY/SELL/EXCHANGE) |
| `/mytrades` | View your recent trades |
| `/mystats` | View your trading statistics |
| `/itemprice [item]` | Check market price for an item |
| `/trending` | View trending items by volume |
| `/toptraders` | View top traders by volume |

### Banker Commands
| Command | Description |
|---------|-------------|
| `/deposit @user 100 100` | Deposit diamonds, issue carats |
| `/atmprofit 10` | Record ATM profit (10 books = 900) |
| `/verifytrade [id]` | Verify a trade report |
| `/resign` | Resign from banker position (with confirmation) |

### Head Banker Commands
| Command | Description |
|---------|-------------|
| `/mintcheck 5` | Check minting recommendation (with 5 expected ATM books) |
| `/mint 1000 carat` | Mint 1000 carats |
| `/burn 500 carat` | Burn 500 carats |
| `/promote @user` | Promote user to banker |
| `/setconsumer @user` | Set user to consumer (read-only) |
| `/freezeprice 1.0` | Freeze price at 1.0 |
| `/unfreezeprice` | Unfreeze market price |
| `/traderreport @user` | Get detailed report on a trader |
| `/alltraders` | Get summary of all traders |

## Profit Strategy

Arca Bank generates profit through:

1. **Transaction Fees**: 1.5% on all transfers
2. **Exchange Fees**: 2.0% on carat <-> golden carat exchanges
3. **Withdrawal Fees**: 1.0% on diamond withdrawals
4. **ATM Book Profits**: 90 diamonds per book deposited
5. **Minting**: When treasury is over-backed, mint new carats to maintain book value

### Mint Check Algorithm

The `mintcheck` command analyzes:
- Current book value vs target (1.0)
- Expected ATM profits
- Recommends MINT, BURN, or HOLD with confidence level

```
If book_value > 1.10 → MINT (over-backed, profit opportunity)
If book_value < 0.85 → BURN (under-backed, protect value)
Otherwise → HOLD
```

## Configuration

Edit `src/config.py` to customize:

```python
@dataclass
class EconomyConfig:
    GOLDEN_CARAT_MULTIPLIER = 9      # Golden carat value
    DIAMONDS_PER_BOOK = 90           # ATM profit rate
    MARKET_REFRESH_INTERVAL_MINUTES = 15
    MIN_CIRCULATION_THRESHOLD = 1000  # Freeze threshold
    TRANSACTION_FEE_PERCENT = 1.5
    EXCHANGE_FEE_PERCENT = 2.0
    MAX_MINT_PER_DAY = 10000         # Daily mint limit
```

## Java Mod Integration

The Fabric mod allows players to check prices and report trades directly from in-game.

### Building the Mod

```bash
cd mod
./gradlew build
# Output: build/libs/arca-bank-1.0.0.jar
```

### Mod Keybinds (Default)

| Key | Action |
|-----|--------|
| `K` | Open Arca Bank menu |
| `P` | Quick price check |
| `J` | Report a trade |

### Mod Configuration

Edit `config/arcabank.json`:
```json
{
  "apiUrl": "http://localhost:8080",
  "requestTimeoutMs": 5000,
  "showNotifications": true
}
```

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/balance/{uuid}` | GET | Get player balance by MC UUID |
| `/api/transfer` | POST | Transfer between players |
| `/api/register` | POST | Register new player |
| `/api/market` | GET | Get market status |
| `/api/treasury` | GET | Get treasury status |
| `/api/is_banker/{uuid}` | GET | Check permissions |
| `/api/trade/report` | POST | Report a trade |
| `/api/trade/price/{item}` | GET | Get item price |
| `/api/trade/trending` | GET | Get trending items |
| `/api/trade/history/{uuid}` | GET | Get trade history |
| `/api/trade/stats/{uuid}` | GET | Get trading statistics |

## Security Features

- **Permission Validation**: All sensitive operations require appropriate role
- **Daily Mint Limits**: Prevents runaway inflation
- **Circulation Monitoring**: Auto-freeze protects against crashes
- **Transaction Logging**: Full audit trail
- **Reserve Requirements**: 20% of diamonds held in reserve

## Trade Reporting System

The trade reporting system allows players to record their trades, building a market price database and trader reputation.

### How It Works

1. **Report Trades**: Players report trades with item, quantity, and price
2. **Market Prices**: Prices are calculated from trade reports using exponential moving average
3. **Trader Stats**: Track buy/sell counts, volume, and verified trade percentage
4. **Reputation**: Traders build reputation as trades are verified by bankers

### Trade Categories

- `DIAMOND` - Diamond items and gear
- `NETHERITE` - Netherite items and gear
- `ENCHANTED_GEAR` - Enchanted equipment
- `BUILDING_MATERIALS` - Blocks and building items
- `FOOD` - Food items
- `POTIONS` - Potions and brewing items
- `REDSTONE` - Redstone components
- `RARE_ITEMS` - Rare/unique items
- `SERVICES` - Services (repairs, builds, etc.)
- `OTHER` - Miscellaneous

## Future Enhancements

- [ ] WebSocket real-time updates
- [ ] Web dashboard
- [ ] Multi-server support
- [ ] Loan system
- [ ] Interest-bearing accounts
- [ ] Auction house integration
- [x] Trade reporting system
- [x] Java Fabric mod
- [x] Consumer role (read-only)

## License

MIT License - See LICENSE file

---

**Arca Bank** - *Securing Minecraft's Financial Future*
