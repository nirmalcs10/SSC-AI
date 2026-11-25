"""
Configuration and constants for Indian Stock Market Multi-Timeframe Trading Tool.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# Angel One SmartAPI Credentials (Loaded securely from .env)
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
ANGEL_CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD", "")  # MPIN / Password
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")  # Base32 secret for TOTP

# Key Indian Index Tokens on Angel One
INDEX_TOKENS = {
    "NIFTY": {
        "name": "NIFTY 50",
        "symbol": "Nifty 50",
        "token": "99926000",
        "exchange": "NSE",
        "lot_size": 65,  # 1 Lot = 65 Qty
        "strike_step": 50,
        "yfinance_ticker": "^NSEI"
    },
    "BANKNIFTY": {
        "name": "NIFTY BANK",
        "symbol": "Nifty Bank",
        "token": "99926009",
        "exchange": "NSE",
        "lot_size": 15,
        "strike_step": 100,
        "yfinance_ticker": "^NSEBANK"
    },
    "FINNIFTY": {
        "name": "NIFTY FIN SERVICE",
        "symbol": "Nifty Fin Services",
        "token": "99926037",
        "exchange": "NSE",
        "lot_size": 25,
        "strike_step": 50,
        "yfinance_ticker": "NIFTY_FIN_SERVICE.NS"
    },
    "MIDCPNIFTY": {
        "name": "NIFTY MID SELECT",
        "symbol": "NIFTY MID SELECT",
        "token": "99926074",
        "exchange": "NSE",
        "lot_size": 50,
        "strike_step": 25,
        "yfinance_ticker": "^NSEMDCP50"
    }
}

# Popular liquid equities for intraday/swing
POPULAR_STOCKS = {
    "RELIANCE": {"token": "2885", "exchange": "NSE", "yfinance": "RELIANCE.NS"},
    "HDFCBANK": {"token": "1333", "exchange": "NSE", "yfinance": "HDFCBANK.NS"},
    "ICICIBANK": {"token": "4963", "exchange": "NSE", "yfinance": "ICICIBANK.NS"},
    "INFY": {"token": "1594", "exchange": "NSE", "yfinance": "INFY.NS"},
    "TCS": {"token": "11536", "exchange": "NSE", "yfinance": "TCS.NS"},
    "TATAMOTORS": {"token": "3456", "exchange": "NSE", "yfinance": "TATAMOTORS.NS"},
    "SBIN": {"token": "3045", "exchange": "NSE", "yfinance": "SBIN.NS"}
}

# Supported Intraday Intervals Only
INTERVAL_MAPPING = {
    "1m": "ONE_MINUTE",
    "3m": "THREE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE"
}

# Strategy & Risk Management Thresholds (Pillars 2 & 4)
ATR_MULTIPLIER_SL = 1.5
RR_RATIO_TARGET_1 = 2.0  # Target at least 1:2 Risk/Reward
RR_RATIO_TARGET_2 = 3.0  # 1:3 RR Extension
RR_RATIO_TARGET_3 = 4.0  # 1:4 RR Major Target
CONFLUENCE_BUY_THRESHOLD = 70
CONFLUENCE_SELL_THRESHOLD = -70

# Risk Management Institutional Rules (Pillar 4)
RISK_PER_TRADE_PERCENT = 0.01          # 0.5%–1.0% of Capital per Trade
DAILY_LOSS_LIMIT_PERCENT = 0.02        # 2.0% of Capital Circuit Breaker
DAILY_MAX_TRADES = 3                   # 1–3 Quality Setups Maximum
REVENGE_TRADING_COOLDOWN_MINUTES = 15  # Anti-Revenge Trading Lockout Cooldown (Minutes)
