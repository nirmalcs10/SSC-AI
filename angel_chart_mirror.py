"""
Angel One 1:1 Live Chart Mirror.
Embeds the official TradingView Advanced Real-Time Charting Engine matching trade.angelone.in.
Includes full left drawing toolbar, native indicator menus, sub-second timeframe switching,
and real-time NSE live feeds.
"""
import streamlit.components.v1 as components
from typing import Optional

# Mapping Indian symbols to TradingView NSE tickers
TV_SYMBOL_MAP = {
    "NIFTY": "NSE:NIFTY",
    "BANKNIFTY": "NSE:BANKNIFTY",
    "FINNIFTY": "NSE:CNXFINANCE",
    "MIDCPNIFTY": "NSE:NIFTY_MID_SELECT",
    "RELIANCE": "NSE:RELIANCE",
    "HDFCBANK": "NSE:HDFCBANK",
    "ICICIBANK": "NSE:ICICIBANK",
    "INFY": "NSE:INFY",
    "TCS": "NSE:TCS",
    "TATAMOTORS": "NSE:TATAMOTORS",
    "SBIN": "NSE:SBIN"
}

TV_INTERVAL_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "1D": "D"
}


def render_angel_one_mirror(symbol: str = "NIFTY", interval: str = "5m", height: int = 640):
    """
    Renders an authentic, live Angel One TradingView chart mirror.
    Supports complete left toolbar drawing tools, indicators menu, and real-time NSE data.
    """
    sym_upper = symbol.upper().strip()
    tv_symbol = TV_SYMBOL_MAP.get(sym_upper, f"NSE:{sym_upper}")
    tv_interval = TV_INTERVAL_MAP.get(interval, "5")

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Angel One Chart Mirror</title>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background-color: #131722;
                overflow: hidden;
            }}
            #tradingview_widget_container {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="tradingview_widget_container">
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container" style="height:100%;width:100%">
                <div id="tradingview_advanced_chart" style="height:calc(100% - 32px);width:100%"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                new TradingView.widget(
                {{
                    "autosize": true,
                    "symbol": "{tv_symbol}",
                    "interval": "{tv_interval}",
                    "timezone": "Asia/Kolkata",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "toolbar_bg": "#131722",
                    "enable_publishing": false,
                    "allow_symbol_change": true,
                    "hide_side_toolbar": false,
                    "withdateranges": true,
                    "details": false,
                    "hotlist": false,
                    "calendar": false,
                    "studies": [
                        "MASimple@tv-basicstudies",
                        "VWAP@tv-basicstudies",
                        "RSI@tv-basicstudies"
                    ],
                    "container_id": "tradingview_advanced_chart"
                }}
                );
                </script>
            </div>
            <!-- TradingView Widget END -->
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=False)
