"""
Angel One 1:1 Live Chart Mirror.
Powered by TradingView's official charting engines (Lightweight Charts & Advanced Widget).
Directly ingests candles from Angel One SmartAPI to completely bypass TradingView's
external symbol licensing restrictions ("This symbol is available only on TradingView").
"""
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, Dict, Any

# Mapping Indian symbols to TradingView NSE tickers
TV_SYMBOL_MAP = {
    "NIFTY": "CAPITALCOM:INDIA50",  # Unrestricted 1:1 Nifty 50 tracker on TradingView
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


def render_angel_one_smartapi_chart(
    df: pd.DataFrame,
    symbol: str = "NIFTY",
    interval: str = "5m",
    trade_plan: Optional[Dict[str, Any]] = None,
    height: int = 650
):
    """
    Renders an authentic, unrestricted Angel One chart using TradingView's official 
    Lightweight Charts engine (v4.1) powered directly by Angel One SmartAPI candles.
    
    Zero 'Available only on TradingView' restrictions, full crosshairs, mouse zoom/pan,
    volume bars, and automated Entry / SL / Target price lines.
    """
    if df is None or df.empty:
        st.warning(f"No candle data available from Angel One for {symbol} ({interval}).")
        return

    # Clean and sort DataFrame
    clean_df = df.copy()
    if "datetime" in clean_df.columns:
        clean_df = clean_df.drop_duplicates(subset=["datetime"]).sort_values("datetime")
    
    candle_records = []
    volume_records = []

    for _, row in clean_df.iterrows():
        try:
            dt = row["datetime"]
            t = int(pd.Timestamp(dt).timestamp())
            o = float(row["open"])
            h = float(row["high"])
            l = float(row["low"])
            c = float(row["close"])
            v = float(row.get("volume", 0) or 0)

            candle_records.append({
                "time": t,
                "open": o,
                "high": h,
                "low": l,
                "close": c
            })
            volume_records.append({
                "time": t,
                "value": v,
                "color": "rgba(8, 153, 129, 0.45)" if c >= o else "rgba(242, 54, 69, 0.45)"
            })
        except Exception:
            continue

    if not candle_records:
        st.error("Error formatting Angel One candle data for chart rendering.")
        return

    latest_close = candle_records[-1]["close"]
    prev_close = candle_records[-2]["close"] if len(candle_records) > 1 else latest_close
    chg = latest_close - prev_close
    pct = (chg / prev_close) * 100 if prev_close else 0.0
    chg_color = "#089981" if chg >= 0 else "#F23645"

    # Extract Trade Plan Levels
    entry_price = 0.0
    stop_loss = 0.0
    target_1 = 0.0
    target_2 = 0.0
    if trade_plan:
        entry_price = float(trade_plan.get("entry_price", 0.0))
        stop_loss = float(trade_plan.get("stop_loss", 0.0))
        target_1 = float(trade_plan.get("target_1", 0.0))
        target_2 = float(trade_plan.get("target_2", 0.0))

    candles_json = json.dumps(candle_records)
    volumes_json = json.dumps(volume_records)

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Angel One SmartAPI Live Chart</title>
        <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background-color: #131722;
                font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
                overflow: hidden;
                color: #D9D9D9;
            }}
            #header-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                height: 42px;
                padding: 0 16px;
                background-color: #1E222D;
                border-bottom: 1px solid #2B2B43;
                font-size: 13px;
            }}
            .badge {{
                display: inline-block;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                margin-right: 6px;
            }}
            .badge-sym {{ background: #2962FF; color: white; }}
            .badge-tf {{ background: #2A2E39; color: #ECEFF1; border: 1px solid #434651; }}
            .badge-angel {{ background: #00E5FF; color: #0E1117; }}
            .price-tag {{ font-size: 15px; font-weight: bold; }}
            #chart-container {{
                width: 100%;
                height: calc(100% - 42px);
                position: relative;
            }}
            #legend {{
                position: absolute;
                top: 10px;
                left: 14px;
                z-index: 10;
                font-size: 12px;
                background: rgba(19, 23, 34, 0.75);
                padding: 6px 10px;
                border-radius: 6px;
                border: 1px solid #2B2B43;
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div id="header-bar">
            <div style="display: flex; align-items: center;">
                <span class="badge badge-sym">{symbol}</span>
                <span class="badge badge-tf">{interval}</span>
                <span class="badge badge-angel">⚡ Angel One SmartAPI Feed</span>
            </div>
            <div>
                <span class="price-tag" style="color: {chg_color};">₹ {latest_close:,.2f}</span>
                <span style="font-size: 12px; color: {chg_color}; margin-left: 6px;">
                    {'+' if chg >= 0 else ''}{chg:.2f} ({'+' if pct >= 0 else ''}{pct:.2f}%)
                </span>
            </div>
        </div>

        <div id="chart-container">
            <div id="legend">
                <span style="font-weight: bold; color: #ECEFF1;">{symbol} • {interval}</span>
                <span id="ohlc-text" style="margin-left: 10px; color: #8B949E;">O: - H: - L: - C: -</span>
            </div>
        </div>

        <script>
            const container = document.getElementById('chart-container');
            const chart = LightweightCharts.createChart(container, {{
                layout: {{
                    background: {{ type: 'solid', color: '#131722' }},
                    textColor: '#D9D9D9',
                    fontSize: 12,
                    fontFamily: "-apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif"
                }},
                grid: {{
                    vertLines: {{ color: 'rgba(42, 46, 57, 0.4)' }},
                    horzLines: {{ color: 'rgba(42, 46, 57, 0.4)' }},
                }},
                crosshair: {{
                    mode: LightweightCharts.CrosshairMode.Normal,
                }},
                rightPriceScale: {{
                    borderColor: '#2B2B43',
                    scaleMargins: {{
                        top: 0.08,
                        bottom: 0.22,
                    }},
                }},
                timeScale: {{
                    borderColor: '#2B2B43',
                    timeVisible: true,
                    secondsVisible: false,
                }},
            }});

            const candleSeries = chart.addCandlestickSeries({{
                upColor: '#089981',
                downColor: '#F23645',
                borderDownColor: '#F23645',
                borderUpColor: '#089981',
                wickDownColor: '#F23645',
                wickUpColor: '#089981',
            }});

            const candleData = {candles_json};
            const volumeData = {volumes_json};

            candleSeries.setData(candleData);

            const volumeSeries = chart.addHistogramSeries({{
                priceFormat: {{
                    type: 'volume',
                }},
                priceScaleId: '',
            }});
            volumeSeries.priceScale().applyOptions({{
                scaleMargins: {{
                    top: 0.82,
                    bottom: 0,
                }},
            }});
            volumeSeries.setData(volumeData);

            // Add Automated AI Confluence Trade Price Lines
            const entryPrice = {entry_price};
            const stopLoss = {stop_loss};
            const target1 = {target_1};
            const target2 = {target_2};

            if (entryPrice > 0) {{
                candleSeries.createPriceLine({{
                    price: entryPrice,
                    color: '#00E5FF',
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Solid,
                    axisLabelVisible: true,
                    title: 'ENTRY (TAKE TRADE)',
                }});
            }}

            if (stopLoss > 0) {{
                candleSeries.createPriceLine({{
                    price: stopLoss,
                    color: '#F23645',
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'STOP LOSS',
                }});
            }}

            if (target1 > 0) {{
                candleSeries.createPriceLine({{
                    price: target1,
                    color: '#089981',
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'TARGET 1 (1:1.5)',
                }});
            }}

            if (target2 > 0) {{
                candleSeries.createPriceLine({{
                    price: target2,
                    color: '#00E676',
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'TARGET 2 (1:2.5)',
                }});
            }}

            // Legend Dynamic Crosshair Update
            const ohlcText = document.getElementById('ohlc-text');
            chart.subscribeCrosshairMove(param => {{
                if (!param || !param.time || !param.seriesData.get(candleSeries)) {{
                    const last = candleData[candleData.length - 1];
                    if (last) {{
                        ohlcText.innerText = `O: ${{last.open.toFixed(2)}}  H: ${{last.high.toFixed(2)}}  L: ${{last.low.toFixed(2)}}  C: ${{last.close.toFixed(2)}}`;
                    }}
                    return;
                }}
                const c = param.seriesData.get(candleSeries);
                ohlcText.innerText = `O: ${{c.open.toFixed(2)}}  H: ${{c.high.toFixed(2)}}  L: ${{c.low.toFixed(2)}}  C: ${{c.close.toFixed(2)}}`;
            }});

            // Auto fit visible bars
            chart.timeScale().fitContent();

            // Responsive Resize
            window.addEventListener('resize', () => {{
                chart.resize(container.clientWidth, container.clientHeight);
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=False)


def render_angel_one_mirror(symbol: str = "NIFTY", interval: str = "5m", height: int = 640):
    """
    Fallback TradingView Cloud Widget with mapped unrestricted symbols.
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
        <title>Angel One TradingView Widget</title>
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
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=False)
