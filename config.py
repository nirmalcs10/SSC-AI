"""
Configuration and constants for Indian Stock Market Multi-Timeframe Trading Tool.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# Angel One SmartAPI Credentials
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "https://apiconnect.angelone.in")
ANGEL_CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "AACO036098")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD", "")  # MPIN / Password
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")  # Base32 secret for TOTP

# Key Indian Index Tokens on Angel One
INDEX_TOKENS = {
    "NIFTY": {
        "name": "NIFTY 50",
        "symbol": "Nifty 50",
        "token": "99926000",
        "exchange": "NSE",
        "lot_size": 25,
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

# Supported Intervals
INTERVAL_MAPPING = {
    "1m": "ONE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "1h": "ONE_HOUR",
    "1D": "ONE_DAY"
}

# Strategy Thresholds
ATR_MULTIPLIER_SL = 1.5
RR_RATIO_TARGET_1 = 1.5
RR_RATIO_TARGET_2 = 2.5
CONFLUENCE_BUY_THRESHOLD = 70
CONFLUENCE_SELL_THRESHOLD = -70
