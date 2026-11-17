"""
Angel One 1:1 Live Chart Mirror.
Powered by TradingView's official charting engines (Lightweight Charts & Advanced Widget).
Directly ingests candles from Angel One SmartAPI to completely bypass TradingView's
external symbol licensing restrictions ("This symbol is available only on TradingView").
Includes AI Confluence Auto-Levels (S/R, CPR, PDH/PDL, Today's Open) and Trade Box (Entry/SL/Targets).
"""
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, Dict, Any, List

# Mapping Indian symbols to TradingView NSE tickers (for Cloud widget fallback)
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


def render_tradingview_confluence_chart(
    df: pd.DataFrame,
    symbol: str = "NIFTY",
    interval: str = "5m",
    trade_plan: Optional[Dict[str, Any]] = None,
    show_sr: bool = True,
    show_cpr: bool = True,
    show_pdh_pdl: bool = True,
    show_trade_overlay: bool = True,
    height: int = 650
):
    """
    Renders the AI Confluence Setup chart using the native TradingView Engine (Lightweight Charts v4.1).
    Powered by genuine Angel One SmartAPI data with Zero symbol restrictions.
    Displays automated Support/Resistance zones, CPR, PDH/PDL, Today's Open,
    and Trade Box (Entry, Stop Loss, Target 1, Target 2, Target 3, Risk-to-Reward).
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

    # Compile Price Lines and Markers from Trade Plan & Overlays
    price_lines: List[Dict[str, Any]] = []
    markers: List[Dict[str, Any]] = []
    signal_text = "WAIT / NEUTRAL"
    signal_color = "#FFD600"
    rrr_text = "1:2"

    if trade_plan:
        direction = trade_plan.get("direction", "NEUTRAL")
        signal = trade_plan.get("signal", "WAIT")
        score = trade_plan.get("confluence_score", 0)
        rrr_text = trade_plan.get("risk_reward_ratio", "1:2")

        if direction == "BUY":
            signal_text = f"🚀 {signal} • Score {score}/100"
            signal_color = "#00C853"
        elif direction == "SELL":
            signal_text = f"🔻 {signal} • Score {score}/100"
            signal_color = "#FF1744"
        else:
            signal_text = f"⏳ {signal} • Score {score}/100"
            signal_color = "#FFD600"

        entry_p = float(trade_plan.get("entry_price", 0.0))
        sl_p = float(trade_plan.get("stop_loss", 0.0))
        t1_p = float(trade_plan.get("target_1", 0.0))
        t2_p = float(trade_plan.get("target_2", 0.0))
        t3_p = float(trade_plan.get("target_3", 0.0))
        risk_pts = float(trade_plan.get("risk_points", 0.0))

        # 1. Trade Box Price Lines (Entry, SL, Targets)
        if show_trade_overlay and entry_p > 0:
            price_lines.append({
                "price": entry_p,
                "color": "#00E5FF",
                "lineWidth": 2,
                "lineStyle": 0,  # Solid
                "axisLabelVisible": True,
                "title": f"ENTRY: ₹{entry_p:,.1f}"
            })
            if sl_p > 0:
                price_lines.append({
                    "price": sl_p,
                    "color": "#FF1744",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"STOP LOSS: ₹{sl_p:,.1f} (-{risk_pts:.1f} pts)"
                })
            if t1_p > 0:
                price_lines.append({
                    "price": t1_p,
                    "color": "#00E676",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"TARGET 1 (1:1.5): ₹{t1_p:,.1f}"
                })
            if t2_p > 0:
                price_lines.append({
                    "price": t2_p,
                    "color": "#00C853",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"TARGET 2 (1:2.5): ₹{t2_p:,.1f}"
                })
            if t3_p > 0:
                price_lines.append({
                    "price": t3_p,
                    "color": "#1DE9B6",
                    "lineWidth": 1,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"TARGET 3: ₹{t3_p:,.1f}"
                })

            # Signal Arrow Marker on Latest Candle
            if candle_records and direction in ("BUY", "SELL"):
                last_time = candle_records[-1]["time"]
                if direction == "BUY":
                    markers.append({
                        "time": last_time,
                        "position": "belowBar",
                        "color": "#00E676",
                        "shape": "arrowUp",
                        "text": f"BUY ENTRY @ ₹{entry_p:,.1f}"
                    })
                else:
                    markers.append({
                        "time": last_time,
                        "position": "aboveBar",
                        "color": "#FF1744",
                        "shape": "arrowDown",
                        "text": f"SELL ENTRY @ ₹{entry_p:,.1f}"
                    })

        # 2. Central Pivot Range (CPR)
        if show_cpr and "cpr" in trade_plan and trade_plan["cpr"]:
            cpr_data = trade_plan["cpr"]
            pivot = float(cpr_data.get("pivot", 0.0))
            tc = float(cpr_data.get("tc", 0.0))
            bc = float(cpr_data.get("bc", 0.0))
            if pivot > 0:
                price_lines.append({
                    "price": pivot,
                    "color": "#E040FB",
                    "lineWidth": 1,
                    "lineStyle": 1,  # Dotted
                    "axisLabelVisible": True,
                    "title": f"CPR PIVOT: ₹{pivot:,.1f}"
                })
            if tc > 0:
                price_lines.append({
                    "price": tc,
                    "color": "#BA68C8",
                    "lineWidth": 1,
                    "lineStyle": 1,
                    "axisLabelVisible": True,
                    "title": f"CPR TC: ₹{tc:,.1f}"
                })
            if bc > 0:
                price_lines.append({
                    "price": bc,
                    "color": "#BA68C8",
                    "lineWidth": 1,
                    "lineStyle": 1,
                    "axisLabelVisible": True,
                    "title": f"CPR BC: ₹{bc:,.1f}"
                })

        # 3. Key Daily Extremes (PDH, PDL, Today's Open)
        if show_pdh_pdl and "pdh_pdl" in trade_plan and trade_plan["pdh_pdl"]:
            pdh_dict = trade_plan["pdh_pdl"]
            pdh = float(pdh_dict.get("pdh", 0.0))
            pdl = float(pdh_dict.get("pdl", 0.0))
            topen = float(pdh_dict.get("today_open", 0.0))
            if pdh > 0:
                price_lines.append({
                    "price": pdh,
                    "color": "#FF5252",
                    "lineWidth": 1,
                    "lineStyle": 1,
                    "axisLabelVisible": True,
                    "title": f"PDH: ₹{pdh:,.1f}"
                })
            if pdl > 0:
                price_lines.append({
                    "price": pdl,
                    "color": "#69F0AE",
                    "lineWidth": 1,
                    "lineStyle": 1,
                    "axisLabelVisible": True,
                    "title": f"PDL: ₹{pdl:,.1f}"
                })
            if topen > 0:
                price_lines.append({
                    "price": topen,
                    "color": "#FFD700",
                    "lineWidth": 1,
                    "lineStyle": 1,
                    "axisLabelVisible": True,
                    "title": f"OPEN: ₹{topen:,.1f}"
                })

        # 4. Support & Resistance Zones
        if show_sr and "sr_zones" in trade_plan and trade_plan["sr_zones"]:
            sr = trade_plan["sr_zones"]
            for r in sr.get("resistances", [])[:2]:
                lvl = float(r.get("level", 0.0))
                if lvl > 0:
                    price_lines.append({
                        "price": lvl,
                        "color": "#EF5350",
                        "lineWidth": 1,
                        "lineStyle": 1,
                        "axisLabelVisible": True,
                        "title": f"RES: ₹{lvl:,.1f}"
                    })
            for s in sr.get("supports", [])[:2]:
                lvl = float(s.get("level", 0.0))
                if lvl > 0:
                    price_lines.append({
                        "price": lvl,
                        "color": "#26A69A",
                        "lineWidth": 1,
                        "lineStyle": 1,
                        "axisLabelVisible": True,
                        "title": f"SUPP: ₹{lvl:,.1f}"
                    })

    candles_json = json.dumps(candle_records)
    volumes_json = json.dumps(volume_records)
    price_lines_json = json.dumps(price_lines)
    markers_json = json.dumps(markers)

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Angel One AI Confluence Chart</title>
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
                height: 44px;
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
            .badge-signal {{ background: rgba(0, 200, 83, 0.15); border: 1px solid {signal_color}; color: {signal_color}; }}
            .price-tag {{ font-size: 15px; font-weight: bold; }}
            #chart-container {{
                width: 100%;
                height: calc(100% - 44px);
                position: relative;
            }}
            #legend {{
                position: absolute;
                top: 10px;
                left: 14px;
                z-index: 10;
                font-size: 12px;
                background: rgba(19, 23, 34, 0.85);
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #2B2B43;
                pointer-events: none;
                backdrop-filter: blur(4px);
            }}
        </style>
    </head>
    <body>
        <div id="header-bar">
            <div style="display: flex; align-items: center;">
                <span class="badge badge-sym">{symbol}</span>
                <span class="badge badge-tf">{interval}</span>
                <span class="badge badge-angel">⚡ Angel One SmartAPI Feed</span>
                <span class="badge badge-signal">{signal_text}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 12px; color: #8B949E;">RR: <strong style="color: #00E5FF;">{rrr_text}</strong></span>
                <div>
                    <span class="price-tag" style="color: {chg_color};">₹ {latest_close:,.2f}</span>
                    <span style="font-size: 12px; color: {chg_color}; margin-left: 6px;">
                        {'+' if chg >= 0 else ''}{chg:.2f} ({'+' if pct >= 0 else ''}{pct:.2f}%)
                    </span>
                </div>
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

            // Add Dynamic AI Confluence & Trade Box Price Lines
            const priceLines = {price_lines_json};
            priceLines.forEach(pl => {{
                candleSeries.createPriceLine({{
                    price: pl.price,
                    color: pl.color,
                    lineWidth: pl.lineWidth,
                    lineStyle: pl.lineStyle,
                    axisLabelVisible: pl.axisLabelVisible,
                    title: pl.title,
                }});
            }});

            // Add Signal Arrow Markers
            const markers = {markers_json};
            if (markers.length > 0) {{
                candleSeries.setMarkers(markers);
            }}

            // Dynamic Crosshair Legend Update
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


def render_angel_one_smartapi_chart(
    df: pd.DataFrame,
    symbol: str = "NIFTY",
    interval: str = "5m",
    trade_plan: Optional[Dict[str, Any]] = None,
    height: int = 650
):
    """
    Renders pure Angel One SmartAPI chart with Trade Box.
    """
    render_tradingview_confluence_chart(
        df=df,
        symbol=symbol,
        interval=interval,
        trade_plan=trade_plan,
        show_sr=False,
        show_cpr=False,
        show_pdh_pdl=False,
        show_trade_overlay=True,
        height=height
    )


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
