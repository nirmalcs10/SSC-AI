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
from indicator_engine import IndicatorEngine

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
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "1h": "60"
}


def render_tradingview_confluence_chart(
    df: pd.DataFrame,
    symbol: str = "NIFTY",
    interval: str = "5m",
    trade_plan: Optional[Dict[str, Any]] = None,
    pattern_drawings: Optional[Dict[str, Any]] = None,
    show_sr: bool = True,
    show_cpr: bool = True,
    show_pdh_pdl: bool = True,
    show_trade_overlay: bool = True,
    show_vwap: bool = True,
    show_ema: bool = True,
    show_rsi: bool = True,
    height: int = 650
):
    """
    Renders the AI Confluence Setup chart using the native TradingView Engine (Lightweight Charts v4.1).
    Powered by genuine Angel One SmartAPI data with Zero symbol restrictions.
    Displays automated Support/Resistance zones, CPR, PDH/PDL, Today's Open,
    and Trade Box (Entry, Stop Loss, Target 1, Target 2, Target 3, Risk-to-Reward).
    Includes real-time VWAP, EMA 9/21, and synchronized RSI(14) indicator sub-pane.
    """
    if df is None or df.empty:
        st.warning(f"No candle data available from Angel One for {symbol} ({interval}).")
        return

    # Clean and sort DataFrame
    clean_df = df.copy()
    if "datetime" in clean_df.columns:
        clean_df = clean_df.drop_duplicates(subset=["datetime"]).sort_values("datetime")

    # Ensure technical indicators (VWAP, EMA 9/21, RSI) are computed
    req_indicators = ["vwap", "ema_9", "ema_21", "rsi"]
    if not all(col in clean_df.columns for col in req_indicators):
        try:
            clean_df = IndicatorEngine.apply_all(clean_df)
        except Exception:
            pass

    candle_records = []
    volume_records = []
    vwap_records = []
    ema9_records = []
    ema21_records = []
    rsi_records = []
    seen_times = set()

    for _, row in clean_df.iterrows():
        try:
            dt = row["datetime"]
            t = int(pd.Timestamp(dt).timestamp())
            if t in seen_times:
                continue
            seen_times.add(t)
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

            if show_vwap and "vwap" in row and pd.notna(row["vwap"]):
                vwap_records.append({"time": t, "value": round(float(row["vwap"]), 2)})
            if show_ema and "ema_9" in row and pd.notna(row["ema_9"]):
                ema9_records.append({"time": t, "value": round(float(row["ema_9"]), 2)})
            if show_ema and "ema_21" in row and pd.notna(row["ema_21"]):
                ema21_records.append({"time": t, "value": round(float(row["ema_21"]), 2)})
            if show_rsi and "rsi" in row and pd.notna(row["rsi"]):
                rsi_records.append({"time": t, "value": round(float(row["rsi"]), 2)})
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
        score = trade_plan.get("confluence_score", trade_plan.get("score", 0))
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
                    "title": f"TARGET 1 (1:2.0): ₹{t1_p:,.1f}"
                })
            if t2_p > 0:
                price_lines.append({
                    "price": t2_p,
                    "color": "#00C853",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"TARGET 2 (1:3.0): ₹{t2_p:,.1f}"
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
            if show_trade_overlay and candle_records and direction in ("BUY", "SELL"):
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
        if show_sr:
            if "sr_zones" in trade_plan and trade_plan["sr_zones"]:
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

            # Institutional Option Chain Support & Resistance Walls
            put_supp = float(trade_plan.get("put_support_strike", 0.0))
            call_res = float(trade_plan.get("call_resistance_strike", 0.0))
            if put_supp > 0:
                price_lines.append({
                    "price": put_supp,
                    "color": "#00E676",
                    "lineWidth": 1,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"OI Put Support: ₹{put_supp:,.0f}"
                })
            if call_res > 0:
                price_lines.append({
                    "price": call_res,
                    "color": "#FF1744",
                    "lineWidth": 1,
                    "lineStyle": 2,  # Dashed
                    "axisLabelVisible": True,
                    "title": f"OI Call Resistance: ₹{call_res:,.0f}"
                })

    # Process Automatic Pattern Drawings (Geometry Lines, Necklines & Markers)
    pattern_lines: List[Dict[str, Any]] = []
    if pattern_drawings and isinstance(pattern_drawings, dict):
        for line in pattern_drawings.get("lines", []):
            pts = line.get("points", [])
            valid_pts = []
            seen_p_times = set()
            for pt in pts:
                pt_t = pt.get("time")
                pt_val = pt.get("value")
                if pt_t and pt_val is not None and pt_t not in seen_p_times:
                    seen_p_times.add(pt_t)
                    valid_pts.append({"time": int(pt_t), "value": float(pt_val)})
            valid_pts.sort(key=lambda x: x["time"])
            if len(valid_pts) >= 2:
                raw_color = line.get("color", "#FFFFFF")
                line_color = "#FFFFFF" if str(raw_color).upper() in ["#FF1744", "#FF5252", "#EF5350", "RED", "#FF0000"] else raw_color
                pattern_lines.append({
                    "title": line.get("title", "Pattern"),
                    "color": line_color,
                    "lineWidth": line.get("lineWidth", 2),
                    "lineStyle": line.get("lineStyle", 0),
                    "points": valid_pts
                })

        for pl in pattern_drawings.get("price_lines", []):
            lvl = float(pl.get("price", 0.0))
            if lvl > 0:
                raw_color = pl.get("color", "#FFFFFF")
                pl_color = "#FFFFFF" if str(raw_color).upper() in ["#FF1744", "#FF5252", "#EF5350", "RED", "#FF0000"] else raw_color
                price_lines.append({
                    "price": lvl,
                    "color": pl_color,
                    "lineWidth": pl.get("lineWidth", 2),
                    "lineStyle": pl.get("lineStyle", 0),
                    "axisLabelVisible": pl.get("axisLabelVisible", True),
                    "title": pl.get("title", "Pattern Level")
                })

        for mk in pattern_drawings.get("markers", []):
            markers.append({
                "time": int(mk.get("time")),
                "position": mk.get("position", "aboveBar"),
                "color": mk.get("color", "#FFD600"),
                "shape": mk.get("shape", "circle"),
                "text": mk.get("text", "")
            })

    # Deduplicate and sort markers by time strictly ascending
    if markers:
        # Keep unique (time, text) combinations
        seen_mk = set()
        clean_markers = []
        for m in sorted(markers, key=lambda x: x["time"]):
            key = (m["time"], m.get("text", ""))
            if key not in seen_mk:
                seen_mk.add(key)
                clean_markers.append(m)
        markers = clean_markers

    candles_json = json.dumps(candle_records)
    volumes_json = json.dumps(volume_records)
    vwap_json = json.dumps(vwap_records)
    ema9_json = json.dumps(ema9_records)
    ema21_json = json.dumps(ema21_records)
    rsi_json = json.dumps(rsi_records)
    price_lines_json = json.dumps(price_lines)
    markers_json = json.dumps(markers)
    pattern_lines_json = json.dumps(pattern_lines)
    has_rsi_js = "true" if (show_rsi and len(rsi_records) > 0) else "false"
    show_vwap_js = "true" if (show_vwap and len(vwap_records) > 0) else "false"
    show_ema_js = "true" if (show_ema and len(ema9_records) > 0) else "false"

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
            #chart-wrapper {{
                width: 100%;
                height: calc(100% - 44px);
                display: flex;
                flex-direction: column;
                position: relative;
            }}
            #price-container {{
                width: 100%;
                height: {"74%" if (show_rsi and rsi_records) else "100%"};
                position: relative;
            }}
            #rsi-container {{
                width: 100%;
                height: 26%;
                position: relative;
                border-top: 1px solid #2B2B43;
            }}
            #legend {{
                position: absolute;
                top: 8px;
                left: 12px;
                z-index: 10;
                font-size: 11px;
                background: rgba(19, 23, 34, 0.88);
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #2B2B43;
                pointer-events: none;
                backdrop-filter: blur(4px);
                white-space: nowrap;
            }}
            #rsi-legend {{
                position: absolute;
                top: 4px;
                left: 12px;
                z-index: 10;
                font-size: 11px;
                background: rgba(19, 23, 34, 0.88);
                padding: 2px 8px;
                border-radius: 4px;
                border: 1px solid #2B2B43;
                pointer-events: none;
                backdrop-filter: blur(4px);
            }}
        </style>
    </head>
    <body>
        <div id="header-bar">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
                <span class="badge badge-sym">{symbol}</span>
                <span class="badge badge-tf">{interval}</span>
                <span class="badge badge-angel">⚡ Angel One SmartAPI Feed</span>
                <span class="badge badge-signal">{signal_text}</span>
                {"<span class=\"badge\" style=\"background: rgba(255, 235, 59, 0.15); color: #FFEB3B; border: 1px solid rgba(255, 235, 59, 0.4);\">VWAP</span>" if (show_vwap and vwap_records) else ""}
                {"<span class=\"badge\" style=\"background: rgba(41, 98, 255, 0.15); color: #2962FF; border: 1px solid rgba(41, 98, 255, 0.4);\">EMA 9</span>" if (show_ema and ema9_records) else ""}
                {"<span class=\"badge\" style=\"background: rgba(255, 152, 0, 0.15); color: #FF9800; border: 1px solid rgba(255, 152, 0, 0.4);\">EMA 21</span>" if (show_ema and ema21_records) else ""}
                {"<span class=\"badge\" style=\"background: rgba(171, 71, 188, 0.15); color: #AB47BC; border: 1px solid rgba(171, 71, 188, 0.4);\">RSI 14</span>" if (show_rsi and rsi_records) else ""}
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

        <div id="chart-wrapper">
            <div id="price-container">
                <div id="legend">
                    <span style="font-weight: bold; color: #ECEFF1;">{symbol} • {interval}</span>
                    <span id="ohlc-text" style="margin-left: 8px; color: #8B949E;">O: - H: - L: - C: -</span>
                    <span id="ind-legend" style="margin-left: 10px;">
                        {"<span style=\"color: #FFEB3B; margin-left: 6px;\">VWAP: <strong id=\"vwap-legend-val\">-</strong></span>" if (show_vwap and vwap_records) else ""}
                        {"<span style=\"color: #2962FF; margin-left: 6px;\">EMA 9: <strong id=\"ema9-legend-val\">-</strong></span>" if (show_ema and ema9_records) else ""}
                        {"<span style=\"color: #FF9800; margin-left: 6px;\">EMA 21: <strong id=\"ema21-legend-val\">-</strong></span>" if (show_ema and ema21_records) else ""}
                    </span>
                </div>
            </div>
            {"<div id=\"rsi-container\"><div id=\"rsi-legend\"><span style=\"font-weight: bold; color: #AB47BC;\">RSI (14):</span> <strong id=\"rsi-legend-val\" style=\"color: #ECEFF1; margin-left: 4px;\">-</strong><span style=\"color: #787B86; font-size: 10px; margin-left: 8px;\">(70 OB / 30 OS)</span></div></div>" if (show_rsi and rsi_records) else ""}
        </div>

        <script>
            const hasRsi = {has_rsi_js};
            const showVwap = {show_vwap_js};
            const showEma = {show_ema_js};

            const priceContainer = document.getElementById('price-container');
            const priceChart = LightweightCharts.createChart(priceContainer, {{
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
                        bottom: 0.20,
                    }},
                }},
                timeScale: {{
                    borderColor: '#2B2B43',
                    timeVisible: true,
                    secondsVisible: false,
                }},
            }});

            const candleSeries = priceChart.addCandlestickSeries({{
                upColor: '#089981',
                downColor: '#F23645',
                borderDownColor: '#F23645',
                borderUpColor: '#089981',
                wickDownColor: '#F23645',
                wickUpColor: '#089981',
            }});

            const candleData = {candles_json};
            const volumeData = {volumes_json};
            const vwapData = {vwap_json};
            const ema9Data = {ema9_json};
            const ema21Data = {ema21_json};
            const rsiData = {rsi_json};

            candleSeries.setData(candleData);

            const volumeSeries = priceChart.addHistogramSeries({{
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

            // Add VWAP Line Series
            let vwapSeries = null;
            if (showVwap && vwapData.length > 0) {{
                vwapSeries = priceChart.addLineSeries({{
                    color: '#FFEB3B',
                    lineWidth: 2,
                    title: 'VWAP',
                    priceLineVisible: false,
                    lastValueVisible: true,
                    crosshairMarkerVisible: true,
                }});
                vwapSeries.setData(vwapData);
            }}

            // Add EMA 9 Line Series
            let ema9Series = null;
            if (showEma && ema9Data.length > 0) {{
                ema9Series = priceChart.addLineSeries({{
                    color: '#2962FF',
                    lineWidth: 1.5,
                    title: 'EMA 9',
                    priceLineVisible: false,
                    lastValueVisible: true,
                    crosshairMarkerVisible: true,
                }});
                ema9Series.setData(ema9Data);
            }}

            // Add EMA 21 Line Series
            let ema21Series = null;
            if (showEma && ema21Data.length > 0) {{
                ema21Series = priceChart.addLineSeries({{
                    color: '#FF9800',
                    lineWidth: 1.5,
                    title: 'EMA 21',
                    priceLineVisible: false,
                    lastValueVisible: true,
                    crosshairMarkerVisible: true,
                }});
                ema21Series.setData(ema21Data);
            }}

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

            // Add Dynamic Pattern Drawing Lines (M, W, Flag Pole/Channel, Trendlines)
            const patternLines = {pattern_lines_json};
            patternLines.forEach(pl => {{
                try {{
                    const lineSeries = priceChart.addLineSeries({{
                        color: pl.color || '#FFFFFF',
                        lineWidth: pl.lineWidth || 2,
                        lineStyle: pl.lineStyle !== undefined ? pl.lineStyle : 0,
                        priceLineVisible: false,
                        lastValueVisible: false,
                        crosshairMarkerVisible: true
                    }});
                    lineSeries.setData(pl.points);
                }} catch (e) {{
                    console.error("Error drawing pattern line:", e);
                }}
            }});

            // Add Signal Arrow & Pattern Markers
            const markers = {markers_json};
            if (markers.length > 0) {{
                candleSeries.setMarkers(markers);
            }}

            // RSI Sub-Chart Setup
            let rsiChart = null;
            let rsiSeries = null;
            if (hasRsi) {{
                const rsiContainer = document.getElementById('rsi-container');
                rsiChart = LightweightCharts.createChart(rsiContainer, {{
                    layout: {{
                        background: {{ type: 'solid', color: '#131722' }},
                        textColor: '#D9D9D9',
                        fontSize: 11,
                        fontFamily: "-apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif"
                    }},
                    grid: {{
                        vertLines: {{ color: 'rgba(42, 46, 57, 0.3)' }},
                        horzLines: {{ color: 'rgba(42, 46, 57, 0.3)' }},
                    }},
                    crosshair: {{
                        mode: LightweightCharts.CrosshairMode.Normal,
                    }},
                    rightPriceScale: {{
                        borderColor: '#2B2B43',
                        scaleMargins: {{
                            top: 0.12,
                            bottom: 0.12,
                        }},
                    }},
                    timeScale: {{
                        borderColor: '#2B2B43',
                        timeVisible: true,
                        secondsVisible: false,
                    }},
                }});

                rsiSeries = rsiChart.addLineSeries({{
                    color: '#AB47BC',
                    lineWidth: 1.5,
                    title: 'RSI 14',
                    priceLineVisible: false,
                    lastValueVisible: true,
                }});
                rsiSeries.setData(rsiData);

                // Levels 70 (Overbought), 50 (Midline), 30 (Oversold)
                rsiSeries.createPriceLine({{
                    price: 70,
                    color: '#EF5350',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: '70',
                }});
                rsiSeries.createPriceLine({{
                    price: 50,
                    color: '#787B86',
                    lineWidth: 1,
                    lineStyle: 1,
                    axisLabelVisible: false,
                    title: '',
                }});
                rsiSeries.createPriceLine({{
                    price: 30,
                    color: '#26A69A',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: '30',
                }});

                // Bidirectional Logical Range Sync
                let isSyncingRange = false;
                priceChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
                    if (isSyncingRange || !range) return;
                    isSyncingRange = true;
                    rsiChart.timeScale().setVisibleLogicalRange(range);
                    isSyncingRange = false;
                }});
                rsiChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
                    if (isSyncingRange || !range) return;
                    isSyncingRange = true;
                    priceChart.timeScale().setVisibleLogicalRange(range);
                    isSyncingRange = false;
                }});

                // Bidirectional Crosshair Sync
                priceChart.subscribeCrosshairMove(param => {{
                    try {{
                        if (!param || !param.time) {{
                            rsiChart.clearCrosshairPosition();
                        }} else {{
                            rsiChart.setCrosshairPosition(0, param.time, rsiSeries);
                        }}
                    }} catch (e) {{}}
                }});
                rsiChart.subscribeCrosshairMove(param => {{
                    try {{
                        if (!param || !param.time) {{
                            priceChart.clearCrosshairPosition();
                        }} else {{
                            priceChart.setCrosshairPosition(0, param.time, candleSeries);
                        }}
                    }} catch (e) {{}}
                }});
            }}

            // Quick lookup maps for instant crosshair updates
            const vwapMap = new Map(vwapData.map(d => [d.time, d.value]));
            const ema9Map = new Map(ema9Data.map(d => [d.time, d.value]));
            const ema21Map = new Map(ema21Data.map(d => [d.time, d.value]));
            const rsiMap = new Map(rsiData.map(d => [d.time, d.value]));

            const ohlcText = document.getElementById('ohlc-text');
            const vwapVal = document.getElementById('vwap-legend-val');
            const ema9Val = document.getElementById('ema9-legend-val');
            const ema21Val = document.getElementById('ema21-legend-val');
            const rsiVal = document.getElementById('rsi-legend-val');

            function setLegendValues(candle, t) {{
                if (candle) {{
                    ohlcText.innerText = `O: ${{candle.open.toFixed(2)}}  H: ${{candle.high.toFixed(2)}}  L: ${{candle.low.toFixed(2)}}  C: ${{candle.close.toFixed(2)}}`;
                }}
                if (vwapVal) {{
                    const v = vwapMap.get(t);
                    vwapVal.innerText = (v !== undefined) ? v.toFixed(2) : '-';
                }}
                if (ema9Val) {{
                    const e9 = ema9Map.get(t);
                    ema9Val.innerText = (e9 !== undefined) ? e9.toFixed(2) : '-';
                }}
                if (ema21Val) {{
                    const e21 = ema21Map.get(t);
                    ema21Val.innerText = (e21 !== undefined) ? e21.toFixed(2) : '-';
                }}
                if (rsiVal) {{
                    const r = rsiMap.get(t);
                    rsiVal.innerText = (r !== undefined) ? r.toFixed(1) : '-';
                }}
            }}

            // Initial default legend values
            if (candleData.length > 0) {{
                const last = candleData[candleData.length - 1];
                setLegendValues(last, last.time);
            }}

            priceChart.subscribeCrosshairMove(param => {{
                if (!param || !param.time || !param.seriesData.get(candleSeries)) {{
                    if (candleData.length > 0) {{
                        const last = candleData[candleData.length - 1];
                        setLegendValues(last, last.time);
                    }}
                    return;
                }}
                const c = param.seriesData.get(candleSeries);
                setLegendValues(c, param.time);
            }});

            if (rsiChart && rsiSeries) {{
                rsiChart.subscribeCrosshairMove(param => {{
                    if (!param || !param.time) {{
                        if (candleData.length > 0) {{
                            const last = candleData[candleData.length - 1];
                            setLegendValues(last, last.time);
                        }}
                        return;
                    }}
                    if (rsiVal) {{
                        const r = rsiMap.get(param.time);
                        rsiVal.innerText = (r !== undefined) ? r.toFixed(1) : '-';
                    }}
                }});
            }}

            // Auto fit visible bars
            priceChart.timeScale().fitContent();
            if (rsiChart) {{
                rsiChart.timeScale().fitContent();
            }}

            // Responsive Resize
            window.addEventListener('resize', () => {{
                priceChart.resize(priceContainer.clientWidth, priceContainer.clientHeight);
                if (rsiChart) {{
                    const rsiContainer = document.getElementById('rsi-container');
                    rsiChart.resize(rsiContainer.clientWidth, rsiContainer.clientHeight);
                }}
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
    pattern_drawings: Optional[Dict[str, Any]] = None,
    show_sr: bool = False,
    show_cpr: bool = False,
    show_pdh_pdl: bool = False,
    show_trade_overlay: bool = False,
    show_vwap: bool = True,
    show_ema: bool = True,
    show_rsi: bool = True,
    height: int = 500
):
    """
    Renders pure, plain Angel One SmartAPI chart with optional automatic pattern drawings,
    intraday VWAP, EMA 9/21, and synchronized RSI indicator pane using native TradingView Lightweight Charts engine.
    """
    render_tradingview_confluence_chart(
        df=df,
        symbol=symbol,
        interval=interval,
        trade_plan=trade_plan,
        pattern_drawings=pattern_drawings,
        show_sr=show_sr,
        show_cpr=show_cpr,
        show_pdh_pdl=show_pdh_pdl,
        show_trade_overlay=show_trade_overlay,
        show_vwap=show_vwap,
        show_ema=show_ema,
        show_rsi=show_rsi,
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
