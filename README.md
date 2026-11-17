# 🇮🇳 Indian Stock Market Multi-Timeframe Trading Tool
### 🛡️ 100% Risk-Free Paper Trading System (Simulation Mode)

An automated trading analysis & paper trading engine tailored for Indian Equities and Indices (**Nifty 50, Bank Nifty, FinNifty, Midcap Nifty, and Equities**).

> **SAFETY NOTICE:** This application operates **EXCLUSIVELY in Paper Trading (Simulation) mode**.
> Real-money order placement is **hard-disabled**. Angel One SmartAPI is utilized strictly as a **Read-Only Live Market Data Feed** (LTP, multi-timeframe candles, 5-level market depth, order flow). Real money is never at risk.

The tool integrates with **Angel One SmartAPI** and processes **1-minute, 5-minute, 15-minute, and 1-hour** charts (plus **1-Day** for swing trading) to automatically output:
1. **Take Trade Price (Entry)**
2. **Stop Loss (SL)** with invalidation logic
3. **Targets (T1, T2, T3)** with Risk-to-Reward calculation
4. **F&O Option Strike Selection** (ATM/ITM CE/PE strike and option premium SL/TP)
5. **Automated Chart Drawing Overlays**:
   - **Support & Resistance Bands** (Fractal Pivot Clusters)
   - **Central Pivot Range (CPR)** (Pivot, TC, BC, and Narrow/Wide CPR Classification)
   - **Previous Day High (PDH)**, **Previous Day Low (PDL)**, and **Today's Open**
   - **Fair Value Gaps (FVG)** and **Order Blocks (OB)**
   - **Trade Markers**: Blue Entry line, Red Stop Loss line, Green Target lines, and Shaded Risk/Reward zones

---

## 🚀 Quick Start Guide

### 1. Configure Angel One Credentials (Optional)
Copy `.env.example` to `.env` and fill in your Angel One SmartAPI details:
```bash
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_CODE=your_client_code
ANGEL_PASSWORD=your_pin
ANGEL_TOTP_SECRET=your_base32_totp_secret
```
> *Note: If credentials are not yet entered, the tool automatically uses a live market data feed / realistic simulator so you can test immediately!*

### 2. Launch the Web Dashboard in Mozilla Firefox
You have two easy ways to launch directly in **Mozilla Firefox**:

**Option A: 1-Click Launcher (Recommended)**
Double-click `start_firefox.bat` or run:
```bash
python launch.py
```
> *This starts the trading engine and automatically opens the dashboard inside **Mozilla Firefox** (`C:\Program Files\Mozilla Firefox\firefox.exe`).*

**Option B: Standard Streamlit Command**
```bash
streamlit run app.py
```

### 3. Open in Browser
Navigate to:
`http://localhost:8501`

---

## 📂 Project Architecture

```
AI-TD/
│
├── config.py                 # Index tokens, lot sizes, strategy thresholds
├── angel_connector.py        # Angel One SmartConnect API & live data fallback
├── token_manager.py          # Scrip master downloader & option token resolver
├── indicator_engine.py       # VWAP, EMA (9, 21, 50, 200), Supertrend, ATR, RSI
├── level_detector.py         # Support & Resistance, CPR, PDH/PDL, FVG, Order Blocks
├── confluence_strategy.py    # Multi-timeframe top-down analyzer & trade calculator
├── chart_plotter.py          # Interactive Plotly chart with overlays and trade markers
├── app.py                    # Streamlit web dashboard
└── test_engine.py            # End-to-end verification test suite
```
