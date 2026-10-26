"""Settings. Secrets come from environment variables (GitHub Actions secrets)."""
import os

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
TIMEFRAME = "15m"          # entry timeframe
HTF = "1h"                 # higher-timeframe trend filter
CANDLES = 300

# Signal rules
MIN_CATEGORIES = 3         # independent confirmation groups required (of 4)
MIN_RR = 1.8               # reject setups with reward:risk below this
ATR_SL_MULT = 0.5          # buffer beyond swing point for stop-loss
TP_RR = 2.0                # first target as multiple of risk
TP2_RR = 3.0               # second target
COOLDOWN_CANDLES = 8       # don't repeat a signal on the same symbol/side

# Data sources tried in order (first one that works for both timeframes wins)
DATA_SOURCES = [s.strip() for s in os.getenv("DATA_SOURCES", "binance,bybit,okx").split(",") if s.strip()]

# Delivery
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Synthetic data is for local demos/backtest smoke tests only; never in live scans
ALLOW_DEMO_DATA = os.getenv("ALLOW_DEMO_DATA", "0") == "1"
