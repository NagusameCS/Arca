# Arca Bank - Minecraft Economy System

A comprehensive economic backend system for Minecraft servers, featuring a Discord bot integration and a Fabric client mod for in-game price checking and trade reporting.

## 🌟 Overview

Arca Bank provides a complete currency management system with:
- **Dual Currency System**: Carats (C) and Golden Carats (GC) with a 9:1 ratio
- **Central Treasury**: Diamond-backed currency with book value tracking
- **Market System**: Real-time price tracking, delayed averages, and circulation monitoring
- **Role-Based Permissions**: Consumer (read-only), User (trade), Banker (write), Head Banker (admin)
- **ATM Integration**: Book profit system at 90 diamonds per book
- **Chart Generation**: Stock-style market visualizations
- **Trade Reporting**: Track trades, prices, and trader reputation
- **Java Mod**: In-game keybind for price checks and trade reporting

## 💰 Currency System

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

## 👥 Permission Levels

| Role | Level | Permissions |
|------|-------|-------------|
| **Consumer** | -1 | View balance, market, treasury (read-only) |
| **User** | 0 | All consumer + transfers, exchanges, trade reporting |
| **Banker** | 1 | All user + deposits, ATM profits, verify trades |
| **Head Banker** | 2 | All banker + mint/burn, promote users, freeze prices, trader reports |

## 📈 Market Features

- **Real-time Index**: Updates every 15 minutes (configurable)
- **Delayed Average**: 24-hour rolling average to prevent manipulation
- **Circulation Monitor**: Automatic price freeze if circulation falls below threshold
- **OHLC Charts**: Candlestick and line charts for market visualization
- **Item Price Tracking**: Market prices derived from trade reports
- **Trending Items**: Track most traded items by volume

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/NagusameCS/Arca.git
cd Arca

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### 2. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name (e.g., "Arca Bank")
3. Go to the **Bot** section and click **"Add Bot"**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
5. Click **"Reset Token"** and copy your bot token
6. Add the token to your `.env` file:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```

### 3. Invite the Bot to Your Server

1. In the Developer Portal, go to **OAuth2 → URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Attach Files
   - Read Message History
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 4. Run the Bot

```bash
# Activate virtual environment if not already active
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the bot
python bot.py
```

You should see: `Arca Bank Bot ready!`

### 5. Run the REST API (Optional - for Java mod)

```bash
python run_api.py
# Or with uvicorn directly:
uvicorn src.integration.java_interface:create_fastapi_app --host 0.0.0.0 --port 8080
```

---

## 🖥️ Running 24/7

### Using systemd (Linux)

Create `/etc/systemd/system/arcabank.service`:

```ini
[Unit]
Description=Arca Bank Discord Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Arca
Environment=DISCORD_TOKEN=your_token_here
ExecStart=/path/to/Arca/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable arcabank
sudo systemctl start arcabank
sudo systemctl status arcabank
```

### Using Screen (Simple method)

```bash
screen -S arcabank
python bot.py
# Press Ctrl+A then D to detach
# Reconnect later with: screen -r arcabank
```

### Using Docker (Coming soon)

```bash
docker-compose up -d
```

---

## 📋 Discord Commands

### 🔧 Utility Commands
| Command | Description |
|---------|-------------|
| `/help` | View all commands with descriptions |
| `/ping` | Check bot latency and status |
| `/about` | Learn about Arca Bank |

### 👤 Public Commands
| Command | Description |
|---------|-------------|
| `/register` | Register with Arca Bank |
| `/link` | Link your Minecraft account |
| `/balance` | Check your balance |
| `/transfer @user 100 carat` | Transfer currency |
| `/exchange 9 carat golden_carat` | Exchange currencies |
| `/leaderboard` | View wealth leaderboard |

### 📊 Market Commands
| Command | Description |
|---------|-------------|
| `/treasury` | View treasury status |
| `/market` | View market status |
| `/history 30` | View 30-day transaction history |
| `/chart 7` | View 7-day market chart |
| `/treasurychart 30` | View treasury health chart |
| `/advancedchart 30` | Advanced stock-style chart with indicators |
| `/marketoverview` | Multi-timeframe overview (1D/7D/30D/90D) |

### 🤝 Trade Commands
| Command | Description |
|---------|-------------|
| `/reporttrade` | Report a trade (BUY/SELL/EXCHANGE) |
| `/mytrades` | View your recent trades |
| `/mystats` | View your trading statistics |
| `/itemprice [item]` | Check market price for an item |
| `/trending` | View trending items by volume |
| `/toptraders` | View top traders by volume |

### 🏦 Banker Commands
| Command | Description |
|---------|-------------|
| `/deposit @user 100 100` | Deposit diamonds, issue carats |
| `/atmprofit 10` | Record ATM profit (10 books = 900 💎) |
| `/verifytrade [id]` | Verify a trade report |
| `/resign` | Resign from banker position |

### 👑 Head Banker Commands
| Command | Description |
|---------|-------------|
| `/mintcheck 5` | Check minting recommendation |
| `/mint 1000 carat` | Mint 1000 carats |
| `/burn 500 carat` | Burn 500 carats |
| `/promote @user` | Promote user to banker |
| `/setconsumer @user` | Set user to consumer (read-only) |
| `/freezeprice 1.0` | Freeze price at 1.0 |
| `/unfreezeprice` | Unfreeze market price |
| `/traderreport @user` | Get detailed report on a trader |
| `/alltraders` | Get summary of all traders |

---

## 📁 Project Structure

```
Arca/
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
│   │   └── trade_service.py
│   ├── api/                  # External interfaces
│   │   ├── bank_api.py       # Main API class
│   │   └── scheduler.py      # Background tasks
│   └── integration/          # Mod integration
│       └── java_interface.py # Java mod REST API
├── mod/                      # Fabric Minecraft mod
│   ├── build.gradle
│   └── src/main/java/com/arcabank/
├── tests/                    # Test suite
│   └── test_bank.py
├── bot.py                    # Discord bot
├── run_api.py               # REST API server
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md
```

---

## 💹 Profit Strategy

Arca Bank generates profit through:

1. **Transaction Fees**: 1.5% on all transfers
2. **Exchange Fees**: 2.0% on carat ↔ golden carat exchanges
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

---

## ⚙️ Configuration

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

---

## ⛏️ Java Mod Integration

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

---

## 🔒 Security Features

- **Permission Validation**: All sensitive operations require appropriate role
- **Daily Mint Limits**: Prevents runaway inflation
- **Circulation Monitoring**: Auto-freeze protects against crashes
- **Transaction Logging**: Full audit trail
- **Reserve Requirements**: 20% of diamonds held in reserve

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=src
```

---

## 📊 Trade Reporting System

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

---

## 🗺️ Roadmap

- [x] Discord Bot with slash commands
- [x] Trade reporting system
- [x] Java Fabric mod
- [x] Consumer role (read-only)
- [x] Advanced charting
- [x] Wealth leaderboard
- [ ] WebSocket real-time updates
- [ ] Web dashboard
- [ ] Multi-server support
- [ ] Loan system
- [ ] Interest-bearing accounts
- [ ] Auction house integration

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

<div align="center">

**Arca Bank** - *Securing Minecraft's Financial Future* 💎

[Report Bug](https://github.com/NagusameCS/Arca/issues) · [Request Feature](https://github.com/NagusameCS/Arca/issues)

</div>
