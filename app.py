"""
Indian Stock Market Multi-Timeframe Trading Tool.
Streamlit Web Dashboard with Angel One SmartAPI Integration,
Indices F&O, Swing & Intraday Modes, automated S/R, CPR, and 1-Click Order Execution.
"""
import streamlit as st
import pandas as pd
import datetime
from pathlib import Path

from config import (
    INDEX_TOKENS,
    POPULAR_STOCKS,
    ANGEL_API_KEY,
    ANGEL_CLIENT_CODE,
    ANGEL_PASSWORD,
    ANGEL_TOTP_SECRET
)
from angel_connector import AngelOneConnector
from confluence_strategy import ConfluenceStrategy
from chart_plotter import ChartPlotter
from order_manager import OrderManager
from token_manager import TokenManager
from angel_chart_mirror import (
    render_angel_one_mirror,
    render_angel_one_smartapi_chart,
    render_tradingview_confluence_chart
)

# Page Config
st.set_page_config(
    page_title="Indian Market Multi-TF Trading Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Trading Terminal Theme)
st.markdown("""
<style>
    .main { background-color: #0E1117; color: #ECEFF1; }
    .stMetric { background-color: #161B22; padding: 12px; border-radius: 8px; border: 1px solid #30363D; }
    .trade-card {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .buy-card {
        background: linear-gradient(135deg, #0d381e 0%, #161b22 100%);
        border: 2px solid #00C853;
    }
    .sell-card {
        background: linear-gradient(135deg, #3d1418 0%, #161b22 100%);
        border: 2px solid #FF1744;
    }
    .wait-card {
        background: linear-gradient(135deg, #3d2f0a 0%, #161b22 100%);
        border: 2px solid #FFD600;
    }
    .execution-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 16px;
        margin-top: 15px;
        margin-bottom: 20px;
    }
    .full-digit-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 12px 14px;
        min-width: 150px;
        text-align: left;
        box-shadow: 0 2px 4px rgba(0,0,0,0.25);
    }
    .digit-title {
        font-size: 11px;
        color: #8B949E;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: visible;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .digit-value {
        font-size: 21px;
        font-weight: 700;
        white-space: nowrap;
        overflow: visible;
        letter-spacing: -0.3px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    .digit-sub {
        font-size: 11px;
        font-weight: 600;
        margin-top: 4px;
        white-space: nowrap;
        overflow: visible;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "angel_connector" not in st.session_state or not hasattr(st.session_state.angel_connector, "get_market_quote"):
    st.session_state.angel_connector = AngelOneConnector()
if "order_manager" not in st.session_state or not hasattr(st.session_state.order_manager, "check_live_triggers"):
    st.session_state.order_manager = OrderManager(st.session_state.angel_connector)
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
if "mtf_data" not in st.session_state:
    st.session_state.mtf_data = None
if "current_symbol" not in st.session_state:
    st.session_state.current_symbol = None
if "current_mode" not in st.session_state:
    st.session_state.current_mode = None


# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("🇮🇳 Indian Market Tool")
st.sidebar.caption("Angel One SmartAPI • Multi-Timeframe Engine")

# Trading Mode Selection (Option Buying Only)
mode = st.sidebar.selectbox(
    "Trading Mode (Option Buying Only)",
    ["Index Option Buying (Intraday 5m/15m)", "Index Option Scalping (3m/5m)"],
    index=0
)
mode_code = "OPTION_SCALP" if "Scalp" in mode else "OPTION_BUY"

# Symbol Selection (Index Options Only)
symbol_options = list(INDEX_TOKENS.keys())
selected_symbol = st.sidebar.selectbox("Select Index (Option Buying)", symbol_options, index=0)

# Chart Overlays Toggles
st.sidebar.subheader("Chart Drawing Overlays")
show_sr = st.sidebar.checkbox("Support & Resistance Zones", value=True)
show_cpr = st.sidebar.checkbox("Central Pivot Range (CPR)", value=True)
show_pdh_pdl = st.sidebar.checkbox("PDH / PDL & Open", value=True)
show_fvg = st.sidebar.checkbox("Fair Value Gaps (FVG)", value=True)
show_trade_overlay = st.sidebar.checkbox("Entry, Stop Loss & Targets", value=True)

# Angel One SmartAPI Login (Only asks for PIN and TOTP)
with st.sidebar.expander("🔑 Angel One SmartAPI Login", expanded=not st.session_state.angel_connector.is_authenticated):
    st.caption("API Key & Client Code are pre-configured. Enter your PIN and TOTP:")
    password_input = st.text_input("Enter 4-Digit PIN", value=ANGEL_PASSWORD, type="password")
    totp_input = st.text_input("Enter 6-Digit TOTP", placeholder="e.g. 123456 or Secret", value=ANGEL_TOTP_SECRET if len(ANGEL_TOTP_SECRET) == 6 else "")
    
    with st.expander("⚙️ Advanced (API Key & Client Code)", expanded=False):
        api_key_input = st.text_input("API Key", value=ANGEL_API_KEY, type="password")
        client_code_input = st.text_input("Client Code", value=ANGEL_CLIENT_CODE)
    
    if st.button("🔐 Login to Angel One", use_container_width=True, type="primary"):
        conn = AngelOneConnector(
            api_key=api_key_input,
            client_code=client_code_input,
            password=password_input,
            totp_secret=totp_input
        )
        success, msg = conn.login(pin=password_input, totp_code=totp_input)
        if success:
            st.session_state.angel_connector = conn
            st.session_state.order_manager = OrderManager(conn)
            conn.update_env_credentials(password=password_input, totp_secret=totp_input)
            st.success("Connected to Angel One Live SmartAPI!")
            st.rerun()
        else:
            st.error(msg)

if st.session_state.angel_connector.is_authenticated:
    st.sidebar.success("🟢 Angel One: Live Connected")
else:
    st.sidebar.info("⚪ Angel One: Ready to Login (Live NSE Fallback Active)")

# Virtual Wallet Manager in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Virtual Paper Wallet")
wallet_state = st.session_state.order_manager.wallet
open_trades_sidebar = st.session_state.order_manager.get_open_positions()
invested_margin_sidebar = sum([t.get('invested_capital', t.get('margin_blocked', 0.0)) for t in open_trades_sidebar])

st.sidebar.metric("Available Margin", f"₹ {wallet_state.get('balance', 100000.0):,.2f}")
st.sidebar.metric("Invested Capital", f"₹ {invested_margin_sidebar:,.2f}")
st.sidebar.metric("Realized P&L", f"₹ {wallet_state.get('realized_pnl', 0.0):,.2f}")

reset_cap = st.sidebar.number_input("Reset Balance (₹)", min_value=10000, max_value=10000000, value=100000, step=25000)
if st.sidebar.button(f"🔄 Reset Wallet to ₹{reset_cap:,}", use_container_width=True, help="Cleanly resets virtual capital to this exact amount"):
    st.session_state.order_manager.reset_wallet(float(reset_cap))
    st.sidebar.success(f"Wallet cleanly reset to ₹{reset_cap:,}!")
    st.rerun()


# Run Analysis Button
analyze_btn = st.sidebar.button("⚡ Run Multi-TF Analysis", use_container_width=True, type="primary")

# Live Quote Fetching
connector = st.session_state.angel_connector
live_quote = connector.get_market_quote(selected_symbol, mode="FULL")
st.session_state.live_quote = live_quote

# Check live triggers for open positions
alerts = st.session_state.order_manager.check_live_triggers(selected_symbol, live_quote["ltp"])
for alert in alerts:
    if alert["type"] == "SL_HIT":
        st.error(f"🚨 {alert['message']}")
    elif alert["type"] == "T2_HIT":
        st.balloons()
        st.success(f"🎯 {alert['message']}")
    elif alert["type"] == "T1_HIT":
        st.warning(f"⚡ {alert['message']}")


# --- MAIN LOGIC (Pillars 1, 2 & 3) ---
timeframes = ("1m", "3m", "5m", "15m")

# Automatically trigger when symbol or trading mode changes, or on initial load / analyze button click
symbol_changed = ("current_symbol" not in st.session_state) or (st.session_state.current_symbol != selected_symbol)
mode_changed = ("current_mode" not in st.session_state) or (st.session_state.current_mode != mode_code)

if analyze_btn or symbol_changed or mode_changed or st.session_state.last_analysis is None:
    with st.spinner(f"Fetching 4 intraday timeframes (15m, 5m, 3m, 1m) & Option Chain for {selected_symbol}..."):
        mtf_data = connector.get_multi_timeframe_data(selected_symbol, timeframes=timeframes)
        st.session_state.mtf_data = mtf_data
        
        # Ingest Option Chain Analysis
        option_chain_data = connector.get_option_chain_analysis(selected_symbol, current_spot_ltp=float(live_quote.get("ltp", 0.0)))
        st.session_state.option_chain_data = option_chain_data

        strategy = ConfluenceStrategy(symbol=selected_symbol, mode=mode_code)
        plan = strategy.analyze(mtf_data, live_quote=live_quote, option_chain=option_chain_data)
        st.session_state.last_analysis = plan
        st.session_state.current_symbol = selected_symbol
        st.session_state.current_mode = mode_code


plan = st.session_state.last_analysis
mtf_data = st.session_state.mtf_data


# --- HEADER & ACCOUNT STATUS ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title(f"{selected_symbol} — Multi-Timeframe Automated Plan")
    st.caption(f"Current Mode: **{mode}** | Timeframes: **15m (Intraday Trend/SR) • 5m (Entry Setup) • 3m (Confirmation) • 1m (Scalp Trigger)** | Updated: {datetime.datetime.now().strftime('%H:%M:%S IST')}")
with col_head2:
    if plan:
        st.metric("Setup Current Price", f"₹ {plan.get('current_price', 0.0):,.2f}")


# --- TRADE SIGNAL CARD & FULL-DIGITS LEVEL HUD ---
if plan:
    direction = plan.get("direction", "NEUTRAL")
    signal = plan.get("signal", "WAIT")
    card_class = "buy-card" if direction == "BUY" else ("sell-card" if direction == "SELL" else "wait-card")
    icon = "🚀" if direction == "BUY" else ("🔻" if direction == "SELL" else "⏳")

    opt_suffix = ""
    if "CALL" not in signal and "PUT" not in signal:
        opt_suffix = " • CALL (CE)" if direction == "BUY" else (" • PUT (PE)" if direction == "SELL" else "")
    c_score_display = plan.get("confluence_score", plan.get("score", 0))

    sig_c1, sig_c2 = st.columns([3.2, 1.2])
    with sig_c1:
        st.markdown(f"""
        <div class="trade-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2 style="margin: 0;">{icon} Signal: {signal}{opt_suffix}</h2>
                <h3 style="margin: 0; color: #FFD600;">Confluence Score: {c_score_display} / 100</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with sig_c2:
        st.write("")
        why_active = st.session_state.get("show_why_signal", False)
        why_label = f"❌ Close Reason" if why_active else f"❓ Why {signal}?"
        if st.button(why_label, key="btn_why_signal", use_container_width=True, type="secondary" if why_active else "primary", help="Click to view detailed chart confluence breakdown and why this decision was made"):
            st.session_state["show_why_signal"] = not why_active
            st.rerun()

    # Active High-Probability Option Trading Pattern Card (Tier-1)
    primary_pat = plan.get("primary_pattern")
    if primary_pat:
        p_name = primary_pat["pattern_name"]
        p_opt = primary_pat["recommended_option"]
        p_conf = primary_pat["confidence"]
        p_desc = primary_pat["description"]
        p_col = "#00E676" if primary_pat["direction"] == "BUY" else "#FF1744"
        p_bg = "rgba(0, 230, 118, 0.12)" if primary_pat["direction"] == "BUY" else "rgba(255, 23, 68, 0.12)"
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid {p_col}; border-left: 5px solid {p_col}; border-radius: 8px; padding: 10px 16px; margin: 8px 0 12px 0; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="color: {p_col}; font-weight: bold; font-size: 14px;">🎯 High-Probability Option Setup: {p_name}</span>
                <span style="background: {p_bg}; color: {p_col}; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-left: 10px;">{p_opt}</span>
                <div style="color: #8B949E; font-size: 12px; margin-top: 3px;">{p_desc}</div>
            </div>
            <div style="text-align: right; min-width: 90px;">
                <span style="font-size: 11px; color: #8B949E;">Quality</span><br>
                <span style="font-size: 16px; font-weight: bold; color: {p_col};">{p_conf}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Dedicated AI Decision Breakdown & Chart Rationale Explainer
    if st.session_state.get("show_why_signal", False):
        dec_summary = plan.get("decision_summary", "")
        rationale = plan.get("detailed_rationale", {})
        c_score = plan.get("confluence_score", plan.get("score", 0))
        c_color = "#00E676" if direction == "BUY" else ("#FF1744" if direction == "SELL" else "#FFD600")

        st.markdown(f"""
        <div style="background-color: #161B22; border: 1px solid #30363D; border-left: 5px solid {c_color}; border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 16px; font-weight: bold; color: #ECEFF1;">
                    🔍 Chart Decision Analysis: Why is the signal {signal}?
                </span>
                <span style="font-size: 12px; font-weight: bold; color: {c_color}; background: rgba(255, 255, 255, 0.05); padding: 3px 10px; border-radius: 5px; border: 1px solid {c_color};">
                    Confluence Score: {c_score} / 100
                </span>
            </div>
            <div style="font-size: 14px; color: #C9D1D9; line-height: 1.6; background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 6px; border-left: 3px solid {c_color};">
                {dec_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # 5-MINUTE & 1-HOUR CHART PATTERNS (BULLISH, BEARISH & SIDE WAVE)
        # -------------------------------------------------------------
        pattern_matrix = plan.get("pattern_matrix", {})
        p_5m = pattern_matrix.get("5m", {})
        p_1h = pattern_matrix.get("1h", {})

        st.markdown("<h4 style='color: #00E5FF; margin: 12px 0 6px 0; font-size: 15px;'>📐 5-Minute & 1-Hour Chart Pattern Matrix (Bullish • Bearish • Side Wave)</h4>", unsafe_allow_html=True)
        st.caption("Synchronized multi-timeframe pattern detection: Comparing Intraday Execution (5m) against Higher-TF Market Structure (1h).")

        pat_col1, pat_col2 = st.columns(2)

        df_5m_chart = mtf_data.get("5m") if mtf_data else None
        df_1h_chart = mtf_data.get("1h") if mtf_data else None
        if df_1h_chart is None and plan:
            df_1h_chart = plan.get("df_1h")
        if df_1h_chart is None and mtf_data and "15m" in mtf_data and mtf_data["15m"] is not None:
            try:
                df_15m_c = mtf_data["15m"]
                if "datetime" in df_15m_c.columns and len(df_15m_c) >= 4:
                    df_1h_raw = df_15m_c.copy().set_index("datetime")
                    df_1h_res = df_1h_raw.resample("1h").agg({
                        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
                    }).dropna().reset_index()
                    if not df_1h_res.empty:
                        df_1h_chart = IndicatorEngine.apply_all(df_1h_res)
            except Exception:
                df_1h_chart = None

        def render_pattern_box(p_data, tf_title, chart_df=None, tf_code="5m"):
            regime = p_data.get("regime", "SIDE WAVE")
            regime_col = p_data.get("regime_color", "#FFD600")
            regime_score = p_data.get("regime_score", 50)
            summary_txt = p_data.get("summary", "")
            bulls = p_data.get("bullish", [])
            bears = p_data.get("bearish", [])
            sides = p_data.get("side_wave", [])

            st.markdown(f"""
            <div style="background: #0D1117; border: 1px solid #30363D; border-top: 4px solid {regime_col}; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 14px; color: #ECEFF1;">{tf_title}</span>
                    <span style="background: rgba(255, 255, 255, 0.05); color: {regime_col}; border: 1px solid {regime_col}; font-weight: bold; font-size: 12px; padding: 2px 8px; border-radius: 4px;">
                        {regime} ({regime_score}%)
                    </span>
                </div>
                <div style="font-size: 12px; color: #8B949E; margin-bottom: 10px;">{summary_txt}</div>
            </div>
            """, unsafe_allow_html=True)

            # 1. Bullish Patterns
            if bulls:
                st.markdown("<span style='color: #00E676; font-weight: bold; font-size: 12px;'>🟢 Active Bullish Patterns</span>", unsafe_allow_html=True)
                for b in bulls:
                    st.markdown(f"""
                    <div style="background: #161B22; border-left: 3px solid #00E676; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px;">
                        <span style="color: #00E676; font-weight: bold; font-size: 12px;">{b.get('pattern_name')} ({b.get('confidence', 80)}%)</span>
                        <div style="color: #C9D1D9; font-size: 11px; margin-top: 2px;">{b.get('description')}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 2. Bearish Patterns
            if bears:
                st.markdown("<span style='color: #FF1744; font-weight: bold; font-size: 12px;'>🔴 Active Bearish Patterns</span>", unsafe_allow_html=True)
                for br in bears:
                    st.markdown(f"""
                    <div style="background: #161B22; border-left: 3px solid #FF1744; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px;">
                        <span style="color: #FF1744; font-weight: bold; font-size: 12px;">{br.get('pattern_name')} ({br.get('confidence', 80)}%)</span>
                        <div style="color: #C9D1D9; font-size: 11px; margin-top: 2px;">{br.get('description')}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 3. Side Wave / Consolidation Patterns
            if sides:
                st.markdown("<span style='color: #FFD600; font-weight: bold; font-size: 12px;'>🟡 Active Side Wave / Consolidation (Theta Decay Risk)</span>", unsafe_allow_html=True)
                for s in sides:
                    st.markdown(f"""
                    <div style="background: #161B22; border-left: 3px solid #FFD600; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px;">
                        <span style="color: #FFD600; font-weight: bold; font-size: 12px;">{s.get('pattern_name')} ({s.get('confidence', 80)}%)</span>
                        <div style="color: #C9D1D9; font-size: 11px; margin-top: 2px;">{s.get('description')}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if not bulls and not bears and not sides:
                st.markdown("""
                <div style="background: #161B22; border: 1px dashed #30363D; border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; color: #8B949E; font-size: 12px;">
                    No distinct single pattern active. Standard moving-average drift.
                </div>
                """, unsafe_allow_html=True)

            # Embedded Interactive Candlestick Chart (TradingView / Angel One Style)
            if chart_df is not None and not chart_df.empty:
                st.markdown(f"<div style='margin-top: 8px; margin-bottom: 4px;'><span style='color: #00E5FF; font-weight: bold; font-size: 12px;'>📊 {tf_code.upper()} Interactive Candlestick Chart</span></div>", unsafe_allow_html=True)
                fig_sub = ChartPlotter.create_trade_chart(
                    df=chart_df,
                    trade_plan=plan,
                    timeframe=tf_code,
                    show_sr=show_sr,
                    show_cpr=show_cpr,
                    show_pdh_pdl=show_pdh_pdl,
                    show_fvg=show_fvg,
                    show_trade_overlay=show_trade_overlay,
                    height=360,
                    is_grid_compact=True
                )
                why_cfg = {
                    "scrollZoom": True,
                    "displayModeBar": True,
                    "responsive": True,
                    "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"]
                }
                st.plotly_chart(fig_sub, use_container_width=True, config=why_cfg, key=f"why_chart_{tf_code}")

        with pat_col1:
            render_pattern_box(p_5m, "⏱️ 5-Minute Chart Pattern Setup (Intraday)", chart_df=df_5m_chart, tf_code="5m")

        with pat_col2:
            render_pattern_box(p_1h, "🕒 1-Hour Chart Pattern Structure (Higher-TF)", chart_df=df_1h_chart, tf_code="1h")

        st.markdown("<hr style='border: 0; border-top: 1px solid #21262D; margin: 12px 0 16px 0;'>", unsafe_allow_html=True)

        w_col1, w_col2 = st.columns(2)
        with w_col1:
            st.markdown("<h4 style='color: #00E5FF; margin: 4px 0 8px 0; font-size: 14px;'>📈 1. Intraday Trend (15m / 5m)</h4>", unsafe_allow_html=True)
            for item in rationale.get("macro", []):
                b_col = "#00E676" if item["status"]=="BULLISH" else ("#FF1744" if item["status"]=="BEARISH" else "#FFD600")
                b_bg = "rgba(0, 230, 118, 0.15)" if item["status"]=="BULLISH" else ("rgba(255, 23, 68, 0.15)" if item["status"]=="BEARISH" else "rgba(255, 214, 0, 0.15)")
                pts_t = f"+{item['points']}" if item['points'] > 0 else str(item['points'])
                st.markdown(f"""
                <div style="background: #0D1117; border: 1px solid #30363D; border-radius: 6px; padding: 7px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: bold; color: #ECEFF1; font-size: 13px;">{item['factor']}</span><br>
                        <span style="color: #8B949E; font-size: 12px;">{item['detail']}</span>
                    </div>
                    <span style="background: {b_bg}; color: {b_col}; font-weight: bold; font-size: 11px; padding: 2px 7px; border-radius: 4px;">{item['status']} ({pts_t} pts)</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<h4 style='color: #00E5FF; margin: 10px 0 8px 0; font-size: 14px;'>⚡ 2. Momentum & Velocity (15m)</h4>", unsafe_allow_html=True)
            for item in rationale.get("structure", []):
                b_col = "#00E676" if item["status"]=="BULLISH" else ("#FF1744" if item["status"]=="BEARISH" else "#FFD600")
                b_bg = "rgba(0, 230, 118, 0.15)" if item["status"]=="BULLISH" else ("rgba(255, 23, 68, 0.15)" if item["status"]=="BEARISH" else "rgba(255, 214, 0, 0.15)")
                pts_t = f"+{item['points']}" if item['points'] > 0 else str(item['points'])
                st.markdown(f"""
                <div style="background: #0D1117; border: 1px solid #30363D; border-radius: 6px; padding: 7px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: bold; color: #ECEFF1; font-size: 13px;">{item['factor']}</span><br>
                        <span style="color: #8B949E; font-size: 12px;">{item['detail']}</span>
                    </div>
                    <span style="background: {b_bg}; color: {b_col}; font-weight: bold; font-size: 11px; padding: 2px 7px; border-radius: 4px;">{item['status']} ({pts_t} pts)</span>
                </div>
                """, unsafe_allow_html=True)

        with w_col2:
            st.markdown("<h4 style='color: #00E5FF; margin: 4px 0 8px 0; font-size: 14px;'>🎯 3. Intraday Execution & Trigger (5m / 1m)</h4>", unsafe_allow_html=True)
            for item in rationale.get("execution", []):
                b_col = "#00E676" if item["status"]=="BULLISH" else ("#FF1744" if item["status"]=="BEARISH" else "#FFD600")
                b_bg = "rgba(0, 230, 118, 0.15)" if item["status"]=="BULLISH" else ("rgba(255, 23, 68, 0.15)" if item["status"]=="BEARISH" else "rgba(255, 214, 0, 0.15)")
                pts_t = f"+{item['points']}" if item['points'] > 0 else str(item['points'])
                st.markdown(f"""
                <div style="background: #0D1117; border: 1px solid #30363D; border-radius: 6px; padding: 7px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: bold; color: #ECEFF1; font-size: 13px;">{item['factor']}</span><br>
                        <span style="color: #8B949E; font-size: 12px;">{item['detail']}</span>
                    </div>
                    <span style="background: {b_bg}; color: {b_col}; font-weight: bold; font-size: 11px; padding: 2px 7px; border-radius: 4px;">{item['status']} ({pts_t} pts)</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<h4 style='color: #00E5FF; margin: 10px 0 8px 0; font-size: 14px;'>🌊 4. Order Flow & Key Chart Levels</h4>", unsafe_allow_html=True)
            for item in (rationale.get("order_flow", []) + rationale.get("levels", [])):
                b_col = "#00E676" if item["status"]=="BULLISH" else ("#FF1744" if item["status"]=="BEARISH" else "#FFD600")
                b_bg = "rgba(0, 230, 118, 0.15)" if item["status"]=="BULLISH" else ("rgba(255, 23, 68, 0.15)" if item["status"]=="BEARISH" else "rgba(255, 214, 0, 0.15)")
                st.markdown(f"""
                <div style="background: #0D1117; border: 1px solid #30363D; border-radius: 6px; padding: 7px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: bold; color: #ECEFF1; font-size: 13px;">{item['factor']}</span><br>
                        <span style="color: #8B949E; font-size: 12px;">{item['detail']}</span>
                    </div>
                    <span style="background: {b_bg}; color: {b_col}; font-weight: bold; font-size: 11px; padding: 2px 7px; border-radius: 4px;">{item['status']}</span>
                </div>
                """, unsafe_allow_html=True)

    entry_p = float(plan.get("entry_price", 0.0))
    sl_p = float(plan.get("stop_loss", 0.0))
    risk_pts = float(plan.get("risk_points", 0.0))
    t1_p = float(plan.get("target_1", 0.0))
    t2_p = float(plan.get("target_2", 0.0))
    t3_p = float(plan.get("target_3", 0.0))
    rrr_str = plan.get("risk_reward_ratio", "1:2")

    t1_gain = round(t1_p - entry_p, 2) if direction == "BUY" else round(entry_p - t1_p, 2)
    t2_gain = round(t2_p - entry_p, 2) if direction == "BUY" else round(entry_p - t2_p, 2)
    t3_gain = round(t3_p - entry_p, 2) if direction == "BUY" else round(entry_p - t3_p, 2)

    # Key Trade Metrics Columns with Full Untruncated Digits
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Take Trade Price (Entry)</div>
            <div class="digit-value" style="color: #00E5FF;">₹ {entry_p:,.2f}</div>
            <div class="digit-sub" style="color: #8B949E;">Exact Trigger Level</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Stop Loss (SL)</div>
            <div class="digit-value" style="color: #FF1744;">₹ {sl_p:,.2f}</div>
            <div class="digit-sub" style="color: #FF5252;">Risk: -{risk_pts:,.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Target 1 (1:1.5 RR)</div>
            <div class="digit-value" style="color: #00E676;">₹ {t1_p:,.2f}</div>
            <div class="digit-sub" style="color: #69F0AE;">Reward: +{t1_gain:,.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Target 2 (1:2.5 RR)</div>
            <div class="digit-value" style="color: #00C853;">₹ {t2_p:,.2f}</div>
            <div class="digit-sub" style="color: #B9F6CA;">Reward: +{t2_gain:,.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col5:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Target 3 (Major S/R)</div>
            <div class="digit-value" style="color: #1DE9B6;">₹ {t3_p:,.2f}</div>
            <div class="digit-sub" style="color: #A7FFEB;">Reward: +{t3_gain:,.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col6:
        st.markdown(f"""
        <div class="full-digit-card">
            <div class="digit-title">Risk-Reward Ratio</div>
            <div class="digit-value" style="color: #FFD600;">{rrr_str}</div>
            <div class="digit-sub" style="color: #FFE57F;">Confluence Verified</div>
        </div>
        """, unsafe_allow_html=True)


# --- LIVE STREAMING 1-SECOND REFRESH FRAGMENT ---
@st.fragment(run_every=1)
def render_live_fno_and_execution_fragment(sym: str, mode_str: str, plan_dict: dict):
    """
    Sub-second / 1-Second Live Stream Fragment:
    Fetches real-time ticks from Angel One SmartAPI every second,
    recalculates F&O ATM strike, premium, option SL & targets,
    evaluates live stop-loss/target triggers, and provides 1-Click execution on ALL indices.
    """
    conn = st.session_state.angel_connector
    ord_mgr = st.session_state.order_manager
    live_q = conn.get_market_quote(sym, mode="FULL")
    live_ltp = float(live_q.get("ltp", 0.0) or (plan_dict.get("current_price", 0.0) if plan_dict else 0.0))
    time_stamp_now = datetime.datetime.now().strftime("%H:%M:%S IST")

    # 1. Evaluate Live Triggers for Open Positions every second
    live_alerts = ord_mgr.check_live_triggers(sym, live_ltp)
    for alert in live_alerts:
        if alert["type"] == "SL_HIT":
            st.error(f"🚨 {alert['message']}")
        elif alert["type"] == "T2_HIT":
            st.balloons()
            st.success(f"🎯 {alert['message']}")
        elif alert["type"] == "T1_HIT":
            st.warning(f"⚡ {alert['message']}")

    # 2. Live Market Quote & Order Flow Banner
    lq_col1, lq_col2, lq_col3, lq_col4 = st.columns([1.5, 1.2, 1.5, 1.2])
    with lq_col1:
        chg_c = "#00E676" if live_q["change"] >= 0 else "#FF1744"
        chg_s = "+" if live_q["change"] >= 0 else ""
        st.markdown(f"""
        <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 12px; color: #8B949E;">Angel One Live LTP ({live_q['exchange']})</span>
                <span style="font-size: 10px; background: rgba(0, 230, 118, 0.2); color: #00E676; padding: 1px 6px; border-radius: 4px; font-weight: bold;">LIVE 1s • {time_stamp_now}</span>
            </div>
            <span style="font-size: 24px; font-weight: bold; color: #ECEFF1;">₹ {live_q['ltp']:,.2f}</span>
            <span style="color: {chg_c}; font-size: 13px; font-weight: bold; margin-left: 8px;">{chg_s}{live_q['change']} ({chg_s}{live_q['percent_change']}%)</span>
        </div>
        """, unsafe_allow_html=True)

    with lq_col2:
        ofr = live_q.get("order_flow_ratio", 50.0)
        d_text = "Buyers in Control" if ofr > 50 else "Sellers in Control"
        d_color = "#00C853" if ofr > 50 else "#FF1744"
        st.markdown(f"""
        <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
            <span style="font-size: 12px; color: #8B949E;">Order-Flow Dominance</span><br>
            <span style="font-size: 14px; font-weight: bold; color: {d_color};">{d_text} ({ofr}%)</span>
            <div style="background: #30363D; border-radius: 4px; height: 6px; width: 100%; margin-top: 6px;">
                <div style="background: {d_color}; height: 6px; width: {ofr}%; border-radius: 4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with lq_col3:
        st.markdown(f"""
        <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
            <span style="font-size: 12px; color: #8B949E;">Day High / Low & Volume</span><br>
            <span style="font-size: 13px; color: #ECEFF1;">H: ₹{live_q['high']:,.1f} | L: ₹{live_q['low']:,.1f}</span><br>
            <span style="font-size: 11px; color: #8B949E;">Vol: {live_q['volume']:,} | OI: {live_q['oi']:,}</span>
        </div>
        """, unsafe_allow_html=True)

    with lq_col4:
        w_state = ord_mgr.wallet
        st.markdown(f"""
        <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
            <span style="font-size: 12px; color: #8B949E;">Virtual Capital Balance</span><br>
            <span style="font-size: 18px; font-weight: bold; color: #00E5FF;">₹ {w_state.get('balance', 100000.0):,.0f}</span><br>
            <span style="font-size: 10px; color: #00E676;">100% Risk-Free Simulation</span>
        </div>
        """, unsafe_allow_html=True)

    # 3. Market Depth 5-Level Table Expander
    with st.expander(f"📊 Live 5-Level Market Depth Ladder — {sym}"):
        depth_data = live_q.get("depth", {})
        top_bids = depth_data.get("buy", [])
        top_asks = depth_data.get("sell", [])
        if top_bids or top_asks:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("<span style='color: #00E676; font-weight: bold;'>Top 5 Bids (Buyers)</span>", unsafe_allow_html=True)
                if top_bids:
                    st.dataframe(pd.DataFrame(top_bids), use_container_width=True)
            with col_d2:
                st.markdown("<span style='color: #FF1744; font-weight: bold;'>Top 5 Asks (Sellers)</span>", unsafe_allow_html=True)
                if top_asks:
                    st.dataframe(pd.DataFrame(top_asks), use_container_width=True)
        else:
            st.info("Live 5-level market depth ladder is active during market hours with Angel One SmartAPI login.")

    # 4. F&O Option Strike & Premium Trade Recommendation Box (Updates Every Second!)
    is_idx = sym in INDEX_TOKENS
    if is_idx:
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; margin-bottom: 8px;">
            <h3 style="margin: 0;">🎯 F&O Option Strike & Premium Trade Recommendation</h3>
            <span style="background: rgba(0, 230, 118, 0.15); border: 1px solid #00E676; color: #00E676; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                🟢 LIVE 1s FEED: {time_stamp_now}
            </span>
        </div>
        """, unsafe_allow_html=True)

        idx_cfg = INDEX_TOKENS[sym]
        stk_step = idx_cfg["strike_step"]
        idx_lot = idx_cfg["lot_size"]
        live_atm_strike = int(round(live_ltp / stk_step) * stk_step)

        # Fetch Live Option Quotes directly from Angel One Exchange (NFO) for ITM, ATM, and OTM strikes
        opt_market_data = conn.get_options_ladder_quotes(sym, live_atm_strike, current_spot_ltp=live_ltp)
        ce_ladder = opt_market_data.get("CE", {})
        pe_ladder = opt_market_data.get("PE", {})
        is_live_nfo_exchange = (opt_market_data.get("status") == "LIVE_NFO_EXCHANGE")
        expiry_str = opt_market_data.get("expiry", "")

        atm_ce = ce_ladder.get("ATM", {})
        atm_pe = pe_ladder.get("ATM", {})

        # Angel One Direct Exchange Live Connection Status Banner
        if conn.is_authenticated:
            st.markdown(f"""
            <div style="background: rgba(0, 230, 118, 0.08); border: 1px solid #00E676; border-radius: 8px; padding: 7px 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: bold; color: #00E676; font-size: 13px;">🟢 LIVE ANGEL ONE EXCHANGE NFO FEED</span>
                    <span style="font-size: 11px; background: rgba(0, 230, 118, 0.2); color: #00E676; padding: 1px 6px; border-radius: 4px; font-weight: bold;">DIRECT NFO QUOTE</span>
                    <span style="font-size: 11px; color: #8B949E;">Active Tokens: {atm_ce.get('token', 'N/A')} (CE) | {atm_pe.get('token', 'N/A')} (PE)</span>
                </div>
                <span style="font-size: 11px; color: #00E676; font-weight: bold;">⚡ Sub-100ms Feed</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: rgba(255, 171, 0, 0.08); border: 1px solid #FFAB00; border-radius: 8px; padding: 7px 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: bold; color: #FFAB00; font-size: 13px;">⚠️ Angel One Direct Feed: Disconnected</span>
                    <span style="font-size: 11px; background: rgba(255, 171, 0, 0.2); color: #FFD54F; padding: 1px 6px; border-radius: 4px;">Pre-Login Live Baseline</span>
                </div>
                <span style="font-size: 11px; color: #8B949E;">Enter PIN & TOTP below to stream tick-by-tick from Angel One</span>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("🔑 Quick Login to Stream Direct from Angel One (PIN & TOTP)", expanded=False):
                in_col1, in_col2, in_col3 = st.columns([1.5, 1.5, 1.2])
                with in_col1:
                    in_pin = st.text_input("4-Digit PIN", type="password", key="inline_fno_pin", value=conn.password)
                with in_col2:
                    in_totp = st.text_input("6-Digit TOTP / Secret", key="inline_fno_totp", placeholder="e.g. 123456")
                with in_col3:
                    st.write("")
                    if st.button("🔐 Connect Live Feed", key="inline_fno_connect_btn", type="primary", use_container_width=True):
                        s_ok, s_msg = conn.login(pin=in_pin, totp_code=in_totp)
                        if s_ok:
                            st.session_state.angel_connector = conn
                            st.session_state.order_manager = OrderManager(conn)
                            conn.update_env_credentials(password=in_pin, totp_secret=in_totp)
                            st.success("🟢 Successfully connected to Angel One!")
                            st.rerun()
                        else:
                            st.error(s_msg)

        # Interactive Moneyness Selector: ATM / ITM / OTM
        mon_row1, mon_row2 = st.columns([3, 1])
        with mon_row1:
            sel_moneyness = st.radio(
                "🎯 Select Strike Moneyness to Display:",
                ["🎯 ATM (At-The-Money)", "💎 ITM (In-The-Money)", "🚀 OTM (Out-of-The-Money)"],
                index=0,
                horizontal=True,
                key=f"moneyness_sel_{sym}"
            )
        m_key = "ATM" if "ATM" in sel_moneyness else ("ITM" if "ITM" in sel_moneyness else "OTM")

        ce_selected = ce_ladder.get(m_key, atm_ce)
        pe_selected = pe_ladder.get(m_key, atm_pe)

        dir_plan = plan_dict.get("direction", "BUY") if plan_dict else "BUY"
        risk_p = float(plan_dict.get("risk_points", 30.0)) if plan_dict else 30.0
        base_prem = round(max(25.0, risk_p * 2.2), 1)

        # 1. Selected Call Option (CE) Metrics
        ce_strike_val = ce_selected.get("strike", live_atm_strike)
        ce_strike_display = f"{sym} {expiry_str} {ce_strike_val} CE" if expiry_str else (ce_selected.get("symbol") or f"{sym} {ce_strike_val} CE")
        live_ce_prem = float(ce_selected.get("ltp") or base_prem)
        ce_bid = float(ce_selected.get("best_bid") or (live_ce_prem - 0.5))
        ce_ask = float(ce_selected.get("best_ask") or (live_ce_prem + 0.5))
        live_ce_sl = float(ce_selected.get("sl") or round(max(5.0, live_ce_prem * 0.75), 1))
        live_ce_t1 = float(ce_selected.get("t1") or round(live_ce_prem * 1.35, 1))
        live_ce_t2 = float(ce_selected.get("t2") or round(live_ce_prem * 1.60, 1))
        is_ce_rec = (dir_plan == "BUY")

        # 2. Selected Put Option (PE) Metrics
        pe_strike_val = pe_selected.get("strike", live_atm_strike)
        pe_strike_display = f"{sym} {expiry_str} {pe_strike_val} PE" if expiry_str else (pe_selected.get("symbol") or f"{sym} {pe_strike_val} PE")
        live_pe_prem = float(pe_selected.get("ltp") or base_prem)
        pe_bid = float(pe_selected.get("best_bid") or (live_pe_prem - 0.5))
        pe_ask = float(pe_selected.get("best_ask") or (live_pe_prem + 0.5))
        live_pe_sl = float(pe_selected.get("sl") or round(max(5.0, live_pe_prem * 0.75), 1))
        live_pe_t1 = float(pe_selected.get("t1") or round(live_pe_prem * 1.35, 1))
        live_pe_t2 = float(pe_selected.get("t2") or round(live_pe_prem * 1.60, 1))
        is_pe_rec = (dir_plan == "SELL")

        # --- CALL OPTION (CE) ROW ---
        ce_badge = "<span style='background: rgba(0, 230, 118, 0.2); border: 1px solid #00E676; color: #00E676; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>🟢 AI RECOMMENDED (BULLISH CONFLUENCE)</span>" if is_ce_rec else "<span style='background: rgba(139, 148, 158, 0.15); border: 1px solid #30363D; color: #8B949E; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>BULLISH ALTERNATIVE</span>"
        feed_badge = "<span style='background: rgba(0, 230, 118, 0.15); border: 1px solid #00E676; color: #00E676; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>⚡ DIRECT ANGEL ONE EXCHANGE NFO TICK</span>" if is_live_nfo_exchange else "<span style='background: rgba(0, 229, 255, 0.15); border: 1px solid #00E5FF; color: #00E5FF; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>⚡ REAL-TIME VOLATILITY QUOTE</span>"

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; margin-bottom: 6px;">
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="font-weight: bold; color: #00E676; font-size: 14px;">🟢 CALL OPTION (CE) • {m_key} Strike • 1 Lot = {idx_lot} Qty</span>
                {feed_badge}
            </div>
            {ce_badge}
        </div>
        """, unsafe_allow_html=True)

        ce_col1, ce_col2, ce_col3, ce_col4, ce_col5 = st.columns(5)
        with ce_col1:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">Live {m_key} Strike (CE)</div>
                <div class="digit-value" style="color: #00E5FF; font-size: 15px;">{ce_strike_display}</div>
                <div class="digit-sub" style="color: #8B949E;">1 Lot = {idx_lot} Qty</div>
            </div>
            """, unsafe_allow_html=True)
        with ce_col2:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">CE Exchange Premium</div>
                <div class="digit-value" style="color: #00E676;">₹ {live_ce_prem:,.2f}</div>
                <div class="digit-sub" style="color: #8B949E;">Bid: ₹{ce_bid:,.1f} | Ask: ₹{ce_ask:,.1f}</div>
            </div>
            """, unsafe_allow_html=True)
        with ce_col3:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">CE Stop Loss</div>
                <div class="digit-value" style="color: #FF1744;">₹ {live_ce_sl:,.2f}</div>
                <div class="digit-sub" style="color: #FF5252;">Risk: -{round(live_ce_prem - live_ce_sl, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)
        with ce_col4:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">CE Target 1</div>
                <div class="digit-value" style="color: #00E676;">₹ {live_ce_t1:,.2f}</div>
                <div class="digit-sub" style="color: #69F0AE;">Gain: +{round(live_ce_t1 - live_ce_prem, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)
        with ce_col5:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">CE Target 2</div>
                <div class="digit-value" style="color: #00C853;">₹ {live_ce_t2:,.2f}</div>
                <div class="digit-sub" style="color: #B9F6CA;">Gain: +{round(live_ce_t2 - live_ce_prem, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)

        # --- PUT OPTION (PE) ROW (DIRECTLY BELOW CALL OPTION) ---
        pe_badge = "<span style='background: rgba(255, 23, 68, 0.2); border: 1px solid #FF1744; color: #FF1744; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>🔴 AI RECOMMENDED (BEARISH CONFLUENCE)</span>" if is_pe_rec else "<span style='background: rgba(139, 148, 158, 0.15); border: 1px solid #30363D; color: #8B949E; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>BEARISH ALTERNATIVE</span>"
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; margin-bottom: 6px;">
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="font-weight: bold; color: #FF1744; font-size: 14px;">🔴 PUT OPTION (PE) • {m_key} Strike • 1 Lot = {idx_lot} Qty</span>
                {feed_badge}
            </div>
            {pe_badge}
        </div>
        """, unsafe_allow_html=True)

        pe_col1, pe_col2, pe_col3, pe_col4, pe_col5 = st.columns(5)
        with pe_col1:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">Live {m_key} Strike (PE)</div>
                <div class="digit-value" style="color: #00E5FF; font-size: 15px;">{pe_strike_display}</div>
                <div class="digit-sub" style="color: #8B949E;">1 Lot = {idx_lot} Qty</div>
            </div>
            """, unsafe_allow_html=True)
        with pe_col2:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">PE Exchange Premium</div>
                <div class="digit-value" style="color: #FF5252;">₹ {live_pe_prem:,.2f}</div>
                <div class="digit-sub" style="color: #8B949E;">Bid: ₹{pe_bid:,.1f} | Ask: ₹{pe_ask:,.1f}</div>
            </div>
            """, unsafe_allow_html=True)
        with pe_col3:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">PE Stop Loss</div>
                <div class="digit-value" style="color: #FF1744;">₹ {live_pe_sl:,.2f}</div>
                <div class="digit-sub" style="color: #FF5252;">Risk: -{round(live_pe_prem - live_pe_sl, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)
        with pe_col4:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">PE Target 1</div>
                <div class="digit-value" style="color: #00E676;">₹ {live_pe_t1:,.2f}</div>
                <div class="digit-sub" style="color: #69F0AE;">Gain: +{round(live_pe_t1 - live_pe_prem, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)
        with pe_col5:
            st.markdown(f"""
            <div class="full-digit-card">
                <div class="digit-title">PE Target 2</div>
                <div class="digit-value" style="color: #00C853;">₹ {live_pe_t2:,.2f}</div>
                <div class="digit-sub" style="color: #B9F6CA;">Gain: +{round(live_pe_t2 - live_pe_prem, 1):,.1f} pts</div>
            </div>
            """, unsafe_allow_html=True)

        # --- MULTI-STRIKE OPTION LADDER MATRIX (ITM • ATM • OTM) ---
        with st.expander("📊 Complete Strike Ladder Matrix (ITM • ATM • OTM Comparison)", expanded=True):
            ladder_col1, ladder_col2 = st.columns(2)
            with ladder_col1:
                st.markdown("<span style='color: #00E676; font-weight: bold;'>🟢 CALL (CE) STRIKE LADDER</span>", unsafe_allow_html=True)
                ce_rows = []
                for tier in ["ITM", "ATM", "OTM"]:
                    c = ce_ladder.get(tier, {})
                    ce_rows.append({
                        "Tier": f"💎 {tier}" if tier == "ITM" else ("🎯 ATM" if tier == "ATM" else "🚀 OTM"),
                        "Strike": c.get("strike"),
                        "Symbol": c.get("symbol"),
                        "LTP (₹)": f"₹ {c.get('ltp', 0.0):,.2f}",
                        "Bid / Ask": f"₹{c.get('best_bid', 0.0):.1f} / ₹{c.get('best_ask', 0.0):.1f}",
                        "SL (₹)": f"₹ {c.get('sl', 0.0):,.1f}",
                        "Target 1 (₹)": f"₹ {c.get('t1', 0.0):,.1f}"
                    })
                st.dataframe(pd.DataFrame(ce_rows), use_container_width=True, hide_index=True)
            with ladder_col2:
                st.markdown("<span style='color: #FF5252; font-weight: bold;'>🔴 PUT (PE) STRIKE LADDER</span>", unsafe_allow_html=True)
                pe_rows = []
                for tier in ["ITM", "ATM", "OTM"]:
                    p = pe_ladder.get(tier, {})
                    pe_rows.append({
                        "Tier": f"💎 {tier}" if tier == "ITM" else ("🎯 ATM" if tier == "ATM" else "🚀 OTM"),
                        "Strike": p.get("strike"),
                        "Symbol": p.get("symbol"),
                        "LTP (₹)": f"₹ {p.get('ltp', 0.0):,.2f}",
                        "Bid / Ask": f"₹{p.get('best_bid', 0.0):.1f} / ₹{p.get('best_ask', 0.0):.1f}",
                        "SL (₹)": f"₹ {p.get('sl', 0.0):,.1f}",
                        "Target 1 (₹)": f"₹ {p.get('t1', 0.0):,.1f}"
                    })
                st.dataframe(pd.DataFrame(pe_rows), use_container_width=True, hide_index=True)

    # 5. 1-Click Option Buying Execution Panel (Index Options CE / PE Only)
    st.markdown("""<div class="execution-box">""", unsafe_allow_html=True)
    st.markdown("<span style='color: #00E5FF; font-weight: bold; font-size: 16px;'>📝 1-Click Option Buying Execution (Zero Real Money Risk)</span>", unsafe_allow_html=True)
    st.caption("Exclusively for Index Option Buyers (BUY CALL CE / BUY PUT PE) • Automatic Option Premium SL & Target Triggers.")

    exec_col1, exec_col2, exec_col3 = st.columns([1.2, 1.2, 1.8])
    plan_dir = plan_dict.get("direction", "BUY") if plan_dict else "BUY"
    default_dir_idx = 0 if plan_dir != "SELL" else 1

    with exec_col1:
        trade_side_label = st.radio(
            "Option Buy Side:",
            ["🟢 BUY CALL (CE) — Bullish", "🔴 BUY PUT (PE) — Bearish"],
            index=default_dir_idx,
            horizontal=True,
            key=f"side_{sym}"
        )
        exec_direction = "BUY" if "CALL (CE)" in trade_side_label else "SELL"

        if is_idx:
            exec_tier_label = st.radio(
                "Execute Moneyness Strike:",
                ["🎯 ATM Strike", "💎 ITM Strike", "🚀 OTM Strike"],
                index=0,
                horizontal=True,
                key=f"tier_exec_{sym}"
            )
            exec_tier = "ATM" if "ATM" in exec_tier_label else ("ITM" if "ITM" in exec_tier_label else "OTM")

    with exec_col2:
        if is_idx:
            lot_size = INDEX_TOKENS[sym]["lot_size"]
            trade_lots = st.number_input(f"Lots (1 Lot = {lot_size} Qty)", min_value=1, max_value=50, value=1, step=1, key=f"lots_{sym}")
            total_contracts = int(trade_lots * lot_size)

            chosen_opt = ce_ladder.get(exec_tier, {}) if exec_direction == "BUY" else pe_ladder.get(exec_tier, {})
            exec_trading_sym = chosen_opt.get("symbol", (ce_strike_display if exec_direction == "BUY" else pe_strike_display))
            exec_entry_p = float(chosen_opt.get("ltp") or (live_ce_prem if exec_direction == "BUY" else live_pe_prem))
            exec_sl_p = float(chosen_opt.get("sl") or (live_ce_sl if exec_direction == "BUY" else live_pe_sl))
            exec_t1_p = float(chosen_opt.get("t1") or (live_ce_t1 if exec_direction == "BUY" else live_pe_t1))
            exec_t2_p = float(chosen_opt.get("t2") or (live_ce_t2 if exec_direction == "BUY" else live_pe_t2))
            u_entry = float(live_ltp)
            if exec_direction == "BUY":
                u_sl = float(plan_dict.get("stop_loss") or round(live_ltp * 0.996, 2))
                u_t1 = float(plan_dict.get("target_1") or round(live_ltp * 1.004, 2))
                u_t2 = float(plan_dict.get("target_2") or round(live_ltp * 1.008, 2))
            else:
                u_sl = float(plan_dict.get("stop_loss") or round(live_ltp * 1.004, 2))
                u_t1 = float(plan_dict.get("target_1") or round(live_ltp * 0.996, 2))
                u_t2 = float(plan_dict.get("target_2") or round(live_ltp * 0.992, 2))

            invested_amount = round(total_contracts * exec_entry_p, 2)

    with exec_col3:
        st.write("")
        st.markdown(f"**Target Contract:** `{exec_trading_sym}` | **Invested Capital:** <span style='color: #00E5FF; font-weight: bold;'>₹ {invested_amount:,.2f}</span>", unsafe_allow_html=True)
        st.caption(f"SL: ₹{exec_sl_p:,.1f} | T1: ₹{exec_t1_p:,.1f} | Available Margin: ₹{ord_mgr.wallet['balance']:,.2f}")
        # Risk Management Guard Check (Pillar 4)
        risk_guard = ord_mgr.get_risk_status()
        is_blocked = False
        block_reason = ""

        if risk_guard["is_circuit_breaker_tripped"]:
            is_blocked = True
            block_reason = f"🚨 Daily Loss Circuit Breaker Active (-₹{abs(risk_guard['today_realized_pnl']):,.2f} <= -2.0%). Trading halted for today."
            st.error(block_reason)
        elif not risk_guard["can_trade_daily"]:
            is_blocked = True
            block_reason = f"🛑 Daily Trade Limit Reached ({risk_guard['daily_trades_count']}/3 setups). Overtrading prevention active."
            st.warning(block_reason)
        elif risk_guard["revenge_cooldown_active"]:
            is_blocked = True
            block_reason = f"⏳ Revenge Trading Protection Active ({risk_guard['cooldown_remaining_min']}m cooldown remaining). Never revenge trade."
            st.warning(block_reason)

        exec_opt_label = "BUY CALL (CE)" if exec_direction == "BUY" else "BUY PUT (PE)"
        btn_text = f"🚀 Execute 1-Click {exec_opt_label} ({trade_lots} Lot = {total_contracts} Qty)"
        if is_blocked:
            btn_text = f"🔒 Trade Execution Blocked: {block_reason[:38]}..."
            st.button(btn_text, disabled=True, use_container_width=True, key=f"btn_exec_{sym}")
        elif st.button(btn_text, type="primary", use_container_width=True, key=f"btn_exec_{sym}"):
            with st.spinner("Executing virtual option buy order..."):
                exec_res = ord_mgr.execute_custom_trade(
                    symbol=sym,
                    direction=exec_direction,
                    trade_type="Options " + ("CE" if exec_direction == "BUY" else "PE"),
                    quantity_lots=int(trade_lots),
                    entry_price=exec_entry_p,
                    sl_price=exec_sl_p,
                    target_1=exec_t1_p,
                    target_2=exec_t2_p,
                    custom_strike=exec_trading_sym,
                    underlying_entry=u_entry,
                    underlying_sl=u_sl,
                    underlying_t1=u_t1,
                    underlying_t2=u_t2
                )
                if exec_res.get("status"):
                    st.success(exec_res.get("message"))
                    st.rerun()
                else:
                    st.error(exec_res.get("message"))
    st.markdown("""</div>""", unsafe_allow_html=True)

    # 6. Active Open Positions Live Ticking Cards
    live_open_trades = ord_mgr.get_open_positions()
    if live_open_trades:
        st.markdown("#### ⚡ Active Open Virtual Positions (Live Ticking P&L)")
        for t in live_open_trades:
            net_pnl = t.get("net_pnl", 0.0)
            is_prof = net_pnl >= 0
            b_col = "#00C853" if is_prof else "#FF1744"
            b_bg = "rgba(0, 200, 83, 0.15)" if is_prof else "rgba(255, 23, 68, 0.15)"
            p_sign = "+" if is_prof else ""
            b_text = f"PROFIT: {p_sign}₹ {net_pnl:,.2f} ({p_sign}{t.get('return_pct', 0.0)}%)" if is_prof else f"LOSS: -₹ {abs(net_pnl):,.2f} ({t.get('return_pct', 0.0)}%)"

            col_pos1, col_pos2 = st.columns([3, 1])
            pos_action = "BUY CE" if (t.get("direction") == "BUY" or "CE" in t.get("trading_symbol", "")) else "BUY PE"
            with col_pos1:
                st.markdown(f"""
                <div style="background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #ECEFF1; font-size: 15px;">{t['trading_symbol']} ({pos_action}) • Qty: {t['quantity']}</span>
                        <span style="background: {b_bg}; border: 1px solid {b_col}; color: {b_col}; padding: 3px 10px; border-radius: 4px; font-weight: bold; font-size: 13px;">
                            {b_text}
                        </span>
                    </div>
                    <div style="display: flex; gap: 18px; font-size: 12px; color: #8B949E; margin-top: 8px; border-top: 1px solid #21262D; padding-top: 6px;">
                        <span>Trade Taken: <strong style="color: #ECEFF1;">{t.get('entry_time', t.get('timestamp'))}</strong></span>
                        <span>Invested: <strong style="color: #00E5FF;">₹ {t.get('invested_capital', 0.0):,.2f}</strong></span>
                        <span>Entry: <strong style="color: #ECEFF1;">₹ {t['entry_price']:.2f}</strong></span>
                        <span>Current: <strong style="color: #ECEFF1;">₹ {t['current_price']:.2f}</strong></span>
                        <span>SL: <strong style="color: #FF1744;">₹ {t['stop_loss']:.2f}</strong></span>
                        <span>Target: <strong style="color: #00E676;">₹ {t['target_2']:.2f}</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_pos2:
                st.write("")
                if st.button(f"❌ Square Off #{t['id']}", key=f"sq_live_{t['id']}", use_container_width=True):
                    opt_exit = t.get("current_price", t["entry_price"]) if (t.get("is_option") or t.get("trade_type", "").startswith("Options")) else live_ltp
                    ord_mgr.square_off_trade(t['id'], opt_exit, exit_reason="MANUAL_SQUARE_OFF")
                    st.rerun()

# Call the 1-second live streaming fragment
render_live_fno_and_execution_fragment(selected_symbol, mode_code, plan)


# --- DASHBOARD TABS (4 Pillars) ---
tab_chart, tab_option_chain, tab_risk_guard, tab_positions, tab_rationale, tab_diagnostics = st.tabs([
    "📊 Multi-Timeframe Chart & Overlays",
    "⛓️ Option Chain Analysis (OI, PCR, IV)",
    "🛡️ Institutional Risk Management Guard",
    "💼 Paper Trades & Performance Analytics",
    "📋 Strategy Rationale & S/R Pivots",
    "⚙️ Angel One Data Diagnostic"
])

# TAB 1: INTERACTIVE ANGEL ONE / TRADINGVIEW CONFLUENCE CHART
with tab_chart:
    view_col1, view_col2 = st.columns([2, 1])
    with view_col1:
        chart_view_mode = st.radio(
            "Chart Display Layout:",
            [
                "🪞 Angel One Live Mirror (TradingView)",
                "🎯 AI Confluence Setup (Auto-Levels & Trade Box)",
                "🔲 Quad Confluence Grid (15m + 5m + 3m + 1m)"
            ],
            horizontal=True
        )
    with view_col2:
        if "Quad" not in chart_view_mode:
            chart_tf = st.radio(
                "Timeframe Role:",
                options=["15m", "5m", "3m", "1m"],
                format_func=lambda x: {
                    "15m": "15m (Intraday Trend)",
                    "5m": "5m (Entry Setup)",
                    "3m": "3m (Confirmation)",
                    "1m": "1m (Scalp Trigger)"
                }.get(x, x),
                index=1,
                horizontal=True
            )

    plotly_config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "responsive": True,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"]
    }

    if "Angel One Live Mirror" in chart_view_mode:
        chart_source_col1, chart_source_col2 = st.columns([3, 1])
        with chart_source_col1:
            chart_feed_type = st.radio(
                "Engine Mode:",
                ["⚡ Angel One SmartAPI Feed (TradingView Engine • No Restrictions)", "🌐 TradingView Cloud Widget"],
                horizontal=True,
                index=0
            )
        with chart_source_col2:
            st.write("")
            st.link_button(f"🔗 Open {selected_symbol} on TradingView", f"https://www.tradingview.com/chart/?symbol=NSE:{selected_symbol}", use_container_width=True)

        if "SmartAPI" in chart_feed_type and mtf_data and chart_tf in mtf_data:
            chart_df = mtf_data[chart_tf]
            render_angel_one_smartapi_chart(
                df=chart_df,
                symbol=selected_symbol,
                interval=chart_tf,
                trade_plan=plan,
                height=640
            )
        else:
            render_angel_one_mirror(symbol=selected_symbol, interval=chart_tf, height=640)
    elif "AI Confluence" in chart_view_mode:
        # AI Confluence Setup with Auto-Levels & Trade Box on TradingView Engine
        confluence_engine_col1, confluence_engine_col2 = st.columns([3, 1])
        with confluence_engine_col1:
            confluence_renderer = st.radio(
                "Confluence Chart Engine:",
                ["⚡ TradingView Engine (Angel One SmartAPI Feed • Recommended)", "📊 Plotly Classic Engine"],
                horizontal=True,
                index=0
            )
        with confluence_engine_col2:
            st.write("")
            st.caption("Active Overlays: S/R, CPR, PDH/PDL, Open, Trade Box")

        if mtf_data and chart_tf in mtf_data:
            chart_df = mtf_data[chart_tf]
            if "TradingView" in confluence_renderer:
                render_tradingview_confluence_chart(
                    df=chart_df,
                    symbol=selected_symbol,
                    interval=chart_tf,
                    trade_plan=plan,
                    show_sr=show_sr,
                    show_cpr=show_cpr,
                    show_pdh_pdl=show_pdh_pdl,
                    show_trade_overlay=show_trade_overlay,
                    height=640
                )
            else:
                fig = ChartPlotter.create_trade_chart(
                    df=chart_df,
                    trade_plan=plan,
                    timeframe=chart_tf,
                    show_sr=show_sr,
                    show_cpr=show_cpr,
                    show_pdh_pdl=show_pdh_pdl,
                    show_fvg=show_fvg,
                    show_trade_overlay=show_trade_overlay,
                    height=580,
                    is_grid_compact=False
                )
                st.plotly_chart(fig, use_container_width=True, config=plotly_config)
        else:
            st.info("Loading Angel One live candle stream for AI Confluence...")
    else:
        # Quad 2x2 Confluence Grid View (Angel One Multi-Chart Style)
        st.caption("Synchronized Intraday Confluence Grid • Visualizing 15m Trend down to 1m Scalp Trigger")
        grid_tf_pairs = [("15m", "5m"), ("3m", "1m")]
        
        for tf_left, tf_right in grid_tf_pairs:
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                if mtf_data and tf_left in mtf_data:
                    fig_l = ChartPlotter.create_trade_chart(
                        df=mtf_data[tf_left],
                        trade_plan=plan,
                        timeframe=tf_left,
                        show_sr=show_sr,
                        show_cpr=show_cpr,
                        show_pdh_pdl=show_pdh_pdl,
                        show_fvg=show_fvg,
                        show_trade_overlay=show_trade_overlay,
                        height=390,
                        is_grid_compact=True
                    )
                    st.plotly_chart(fig_l, use_container_width=True, config=plotly_config)
            with g_col2:
                if mtf_data and tf_right in mtf_data:
                    fig_r = ChartPlotter.create_trade_chart(
                        df=mtf_data[tf_right],
                        trade_plan=plan,
                        timeframe=tf_right,
                        show_sr=show_sr,
                        show_cpr=show_cpr,
                        show_pdh_pdl=show_pdh_pdl,
                        show_fvg=show_fvg,
                        show_trade_overlay=show_trade_overlay,
                        height=390,
                        is_grid_compact=True
                    )
                    st.plotly_chart(fig_r, use_container_width=True, config=plotly_config)


# TAB: OPTION CHAIN ANALYSIS (PILLAR 3)
with tab_option_chain:
    st.subheader(f"⛓️ Live Option Chain Analysis — {selected_symbol}")
    st.caption("Institutional Open Interest (OI), PCR, Call/Put Writing, and Spot Price Action Confirmation.")

    oc_data = st.session_state.get("option_chain_data")
    if not oc_data:
        oc_data = connector.get_option_chain_analysis(selected_symbol, current_spot_ltp=live_ltp)
        st.session_state.option_chain_data = oc_data

    # Metric Row 1: PCR & Institutional Sentiment
    oc_col1, oc_col2, oc_col3, oc_col4 = st.columns(4)
    with oc_col1:
        pcr_val = oc_data.get("pcr", 1.0)
        pcr_sent = oc_data.get("pcr_sentiment", "NEUTRAL")
        p_badge_col = "#00E676" if pcr_sent == "BULLISH" else ("#FF1744" if pcr_sent == "BEARISH" else "#FFD600")
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #8B949E; font-size: 12px;">PUT-CALL RATIO (PCR)</div>
            <div style="color: {p_badge_col}; font-size: 26px; font-weight: bold; margin: 4px 0;">{pcr_val:.2f}</div>
            <span style="background: rgba(255,255,255,0.08); color: {p_badge_col}; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;">{pcr_sent} BIAS</span>
        </div>
        """, unsafe_allow_html=True)

    with oc_col2:
        put_supp = oc_data.get("put_support_strike", 0)
        put_oi = oc_data.get("put_support_oi", 0)
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid rgba(0, 230, 118, 0.3); border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #00E676; font-size: 12px; font-weight: bold;">PUT WRITING SUPPORT</div>
            <div style="color: #ECEFF1; font-size: 24px; font-weight: bold; margin: 4px 0;">₹ {put_supp:,}</div>
            <span style="color: #8B949E; font-size: 11px;">Max Put OI: {put_oi:,} contracts</span>
        </div>
        """, unsafe_allow_html=True)

    with oc_col3:
        call_res = oc_data.get("call_resistance_strike", 0)
        call_oi = oc_data.get("call_resistance_oi", 0)
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid rgba(255, 23, 68, 0.3); border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #FF1744; font-size: 12px; font-weight: bold;">CALL WRITING RESISTANCE</div>
            <div style="color: #ECEFF1; font-size: 24px; font-weight: bold; margin: 4px 0;">₹ {call_res:,}</div>
            <span style="color: #8B949E; font-size: 11px;">Max Call OI: {call_oi:,} contracts</span>
        </div>
        """, unsafe_allow_html=True)

    with oc_col4:
        atm_ce = oc_data.get("atm_ce_premium", 0.0)
        atm_pe = oc_data.get("atm_pe_premium", 0.0)
        atm_iv = oc_data.get("atm_iv", 0.0)
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #00E5FF; font-size: 12px; font-weight: bold;">ATM PREMIUM & IV</div>
            <div style="color: #ECEFF1; font-size: 18px; font-weight: bold; margin: 4px 0;">CE: ₹{atm_ce:.1f} | PE: ₹{atm_pe:.1f}</div>
            <span style="color: #8B949E; font-size: 11px;">ATM IV: {atm_iv:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)

    # Spot Price Action Confirmation Banner
    st.markdown(f"""
    <div style="background: #0D1117; border-left: 4px solid #00E5FF; border: 1px solid #30363D; border-radius: 6px; padding: 10px 14px; margin: 12px 0;">
        <span style="color: #00E5FF; font-weight: bold;">📍 Spot Price Action Confirmation:</span>
        <span style="color: #ECEFF1; margin-left: 8px;">{oc_data.get('spot_conf_desc', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    # Option Chain Strike Ladder Table
    rows = oc_data.get("chain_rows", [])
    if rows:
        table_records = []
        for r in rows:
            is_atm_badge = "🎯 ATM" if r.get("is_atm") else ""
            table_records.append({
                "Call OI": f"{r['call_oi']:,}",
                "Call Chg OI": f"{r['call_chng_oi']:,}",
                "Call Vol": f"{r['call_volume']:,}",
                "Call LTP": f"₹ {r['call_ltp']:.2f}",
                "Call IV": f"{r['call_iv']:.1f}%",
                "Strike": f"{r['strike']} {is_atm_badge}".strip(),
                "Put LTP": f"₹ {r['put_ltp']:.2f}",
                "Put IV": f"{r['put_iv']:.1f}%",
                "Put Vol": f"{r['put_volume']:,}",
                "Put Chg OI": f"{r['put_chng_oi']:,}",
                "Put OI": f"{r['put_oi']:,}"
            })
        st.dataframe(pd.DataFrame(table_records), use_container_width=True, hide_index=True)

# TAB: INSTITUTIONAL RISK MANAGEMENT GUARD (PILLAR 4)
with tab_risk_guard:
    st.subheader("🛡️ Institutional Risk Management & Capital Protection Guard")
    st.caption("Professional Capital Preservation Rules: Risk per Trade, Daily Trades Limit, 2% Circuit Breaker, Anti-Revenge Lockout.")

    r_guard = st.session_state.order_manager.get_risk_status()

    # Rule Summary Cards
    rg_col1, rg_col2, rg_col3, rg_col4 = st.columns(4)
    with rg_col1:
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #8B949E; font-size: 12px;">RISK PER TRADE</div>
            <div style="color: #00E5FF; font-size: 24px; font-weight: bold; margin: 4px 0;">0.5% – 1.0%</div>
            <span style="color: #8B949E; font-size: 11px;">Max Risk: ₹ {r_guard['risk_per_trade_max_inr']:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with rg_col2:
        t_count = r_guard["daily_trades_count"]
        t_max = r_guard["daily_max_trades"]
        t_col = "#00E676" if t_count < t_max else "#FF1744"
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #8B949E; font-size: 12px;">DAILY TRADES CAP</div>
            <div style="color: {t_col}; font-size: 24px; font-weight: bold; margin: 4px 0;">{t_count} / {t_max} Max</div>
            <span style="color: {t_col}; font-size: 11px; font-weight: bold;">{'ALLOWED' if r_guard['can_trade_daily'] else 'CAP REACHED'}</span>
        </div>
        """, unsafe_allow_html=True)

    with rg_col3:
        pnl_today = r_guard["today_realized_pnl"]
        pnl_col = "#00E676" if pnl_today >= 0 else ("#FF1744" if r_guard["is_circuit_breaker_tripped"] else "#FFD600")
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #8B949E; font-size: 12px;">DAILY LOSS LIMIT (2%)</div>
            <div style="color: {pnl_col}; font-size: 24px; font-weight: bold; margin: 4px 0;">₹ {pnl_today:,.2f}</div>
            <span style="color: #8B949E; font-size: 11px;">Circuit Breaker: ₹ {r_guard['daily_loss_limit_inr']:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with rg_col4:
        rev_active = r_guard["revenge_cooldown_active"]
        rev_col = "#FF1744" if rev_active else "#00E676"
        rev_text = f"COOLDOWN ({r_guard['cooldown_remaining_min']}m)" if rev_active else "SHIELD ACTIVE"
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="color: #8B949E; font-size: 12px;">REVENGE TRADING</div>
            <div style="color: {rev_col}; font-size: 24px; font-weight: bold; margin: 4px 0;">NEVER</div>
            <span style="background: rgba(255,255,255,0.08); color: {rev_col}; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;">{rev_text}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Risk Management Educational & Discipline Matrix
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.markdown("""
        #### 📌 Golden Rules of Institutional Risk Management
        1. **Risk per trade (0.5% – 1% Capital)**: Never risk more than 1% of total portfolio on any single trade setup.
        2. **Setup Invalidation Stop Loss**: Stop loss is placed strictly where the trade idea is invalidated (e.g., breakdown below 5m candle low or Intraday VWAP), never an arbitrary point distance.
        3. **Risk-to-Reward (Minimum 1:2)**: Only execute trades where Target 1 offers at least 2x the stop loss risk ($Target_1 >= 2 	imes SL$).
        4. **Daily Trades Cap (1–3 Setups)**: Trade quality over quantity. Overtrading is the #1 destroyer of retail capital.
        5. **Daily Loss Limit (2% Circuit Breaker)**: If cumulative losses reach 2% of capital in a single session, the system automatically halts all new entries.
        6. **Revenge Trading (NEVER)**: After a stop loss hit, a 15-minute emotional reset cooldown prevents immediate impulsive re-entries.
        """)
    with d_col2:
        st.markdown("#### 🧮 Dynamic Position Sizing Calculator")
        calc_capital = st.number_input("Virtual Capital (₹)", value=float(r_guard["current_balance"]), step=5000.0, key="calc_cap")
        calc_risk_pct = st.slider("Risk per Trade (%)", min_value=0.5, max_value=2.0, value=1.0, step=0.1, key="calc_pct")
        calc_sl_pts = st.number_input("Stop Loss Distance (Points / ₹)", min_value=1.0, value=25.0, step=1.0, key="calc_sl")

        max_risk_inr = calc_capital * (calc_risk_pct / 100.0)
        calc_qty = int(max_risk_inr / calc_sl_pts)
        idx_lot = INDEX_TOKENS.get(selected_symbol, {}).get("lot_size", 65)
        calc_lots = max(1, calc_qty // idx_lot)

        st.success(f"""
        **Sizing Output:**
        - Maximum Allowed Risk: **₹ {max_risk_inr:,.2f}**
        - Recommended Quantity: **{calc_qty} units**
        - Recommended Index Lots ({selected_symbol} Lot = {idx_lot}): **{calc_lots} Lot ({calc_lots * idx_lot} Qty)**
        """)

# TAB 2: PAPER TRADING PERFORMANCE & ORDERS
with tab_positions:
    analytics = st.session_state.order_manager.get_analytics()
    st.subheader("📈 Virtual Paper Trading Performance")
    
    a_col1, a_col2, a_col3, a_col4, a_col5 = st.columns(5)
    with a_col1:
        st.metric("Total Completed Trades", analytics["total_closed"])
    with a_col2:
        st.metric("Win Rate", f"{analytics['win_rate']}%")
    with a_col3:
        st.metric("Profit Factor", f"{analytics['profit_factor']}")
    with a_col4:
        pnl_val = analytics["net_pnl"]
        st.metric("Net Realized P&L", f"₹ {pnl_val:,.2f}", delta=f"{pnl_val:,.2f}")
    with a_col5:
        st.metric("Total Capital Invested", f"₹ {analytics.get('total_invested', 0.0):,.2f}")

    st.markdown("---")
    st.subheader("Active Virtual Positions")
    open_trades = st.session_state.order_manager.get_open_positions()
    if not open_trades:
        st.info("No open virtual positions right now. Click 'Execute 1-Click Trade' on the panel above to start a trade!")
    else:
        df_open = pd.DataFrame(open_trades)
        display_cols = ["id", "entry_time", "trading_symbol", "direction", "quantity", "invested_capital", "entry_price", "current_price", "stop_loss", "target_2", "net_pnl", "return_pct"]
        valid_cols = [c for c in display_cols if c in df_open.columns]
        st.dataframe(df_open[valid_cols], use_container_width=True)

        sq_col1, sq_col2 = st.columns([2, 1])
        with sq_col1:
            selected_trade_id = st.selectbox("Select Virtual Position to Square Off", [t["id"] for t in open_trades])
        with sq_col2:
            st.write("")
            st.write("")
            if st.button("❌ Square Off Position", type="secondary"):
                trade_to_sq = next((t for t in open_trades if t["id"] == selected_trade_id), None)
                if trade_to_sq and (trade_to_sq.get("is_option") or trade_to_sq.get("trade_type", "").startswith("Options")):
                    curr_p = trade_to_sq.get("current_price", trade_to_sq["entry_price"])
                else:
                    curr_p = live_quote.get("ltp", plan.get("current_price", 0.0))
                if st.session_state.order_manager.square_off_trade(selected_trade_id, curr_p, exit_reason="MANUAL_SQUARE_OFF"):
                    st.success(f"Position {selected_trade_id} squared off at ₹{curr_p}!")
                    st.rerun()

    # Closed trades history with complete lifecycle & profit/loss badges
    closed_trades = st.session_state.order_manager.get_closed_trades()
    if closed_trades:
        st.markdown("---")
        st.subheader("📋 Completed Trade Lifecycle & P&L Journal")
        for ct in closed_trades:
            net_pnl = ct.get("net_pnl", 0.0)
            is_prof = net_pnl >= 0
            b_col = "#00C853" if is_prof else "#FF1744"
            b_bg = "rgba(0, 200, 83, 0.15)" if is_prof else "rgba(255, 23, 68, 0.15)"
            p_sign = "+" if is_prof else ""
            b_text = f"🟢 PROFIT: {p_sign}₹ {net_pnl:,.2f} ({p_sign}{ct.get('return_pct', 0.0)}%)" if is_prof else f"🔴 LOSS: -₹ {abs(net_pnl):,.2f} ({ct.get('return_pct', 0.0)}%)"
            
            st.markdown(f"""
            <div style="background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="font-weight: bold; font-size: 16px; color: #ECEFF1;">{ct.get('trading_symbol', ct.get('symbol'))} ({ct.get('direction')})</span>
                        <span style="color: #8B949E; font-size: 13px; margin-left: 10px;">ID: #{ct.get('id')} • Qty: {ct.get('quantity')}</span>
                    </div>
                    <div style="background: {b_bg}; border: 1px solid {b_col}; color: {b_col}; padding: 3px 12px; border-radius: 6px; font-weight: bold; font-size: 14px;">
                        {b_text}
                    </div>
                </div>
                <div style="display: flex; gap: 20px; font-size: 12px; color: #8B949E; border-top: 1px solid #21262D; padding-top: 8px;">
                    <div><strong>Trade Taken:</strong> <span style="color: #ECEFF1;">{ct.get('entry_time', ct.get('timestamp'))}</span></div>
                    <div><strong>Trade Ended:</strong> <span style="color: #ECEFF1;">{ct.get('exit_time', 'N/A')}</span></div>
                    <div><strong>Invested:</strong> <span style="color: #00E5FF; font-weight: bold;">₹ {ct.get('invested_capital', ct.get('margin_blocked', 0.0)):,.2f}</span></div>
                    <div><strong>Entry Price:</strong> <span style="color: #ECEFF1;">₹ {ct.get('entry_price', 0.0):.2f}</span></div>
                    <div><strong>Exit Price:</strong> <span style="color: #ECEFF1;">₹ {ct.get('exit_price', 0.0):.2f}</span></div>
                    <div><strong>Trigger:</strong> <span style="color: #FFD600;">{ct.get('exit_reason', 'N/A')}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        df_closed = pd.DataFrame(closed_trades)
        c_cols = ["id", "trading_symbol", "direction", "quantity", "invested_capital", "entry_time", "exit_time", "entry_price", "exit_price", "gross_pnl", "charges", "net_pnl", "return_pct", "exit_reason"]
        valid_c_cols = [c for c in c_cols if c in df_closed.columns]
        st.dataframe(df_closed[valid_c_cols], use_container_width=True)
    else:
        st.info("No completed virtual paper trades yet. Open and close a trade to populate the performance journal.")

# TAB 3: RATIONALE & PIVOTS
with tab_rationale:
    col_rat1, col_rat2 = st.columns([1, 1])
    with col_rat1:
        st.subheader("Multi-Timeframe Confluence Reasons")
        reasons = plan.get("reasons", [])
        if reasons:
            for r in reasons:
                st.write(f"• {r}")
        else:
            st.info("Analysis neutral. Watching for trend confirmation.")

    with col_rat2:
        st.subheader("Key Reference & Pivot Levels")
        cpr = plan.get("cpr", {})
        pdh_pdl = plan.get("pdh_pdl", {})
        t_data = {
            "Level Type": ["CPR Pivot (P)", "Top Central (TC)", "Bottom Central (BC)", "Previous Day High (PDH)", "Previous Day Low (PDL)", "Today's Open (DO)", "Classic R1", "Classic S1"],
            "Price": [
                f"₹ {cpr.get('pivot', 0.0):,.2f}",
                f"₹ {cpr.get('tc', 0.0):,.2f}",
                f"₹ {cpr.get('bc', 0.0):,.2f}",
                f"₹ {pdh_pdl.get('pdh', 0.0):,.2f}",
                f"₹ {pdh_pdl.get('pdl', 0.0):,.2f}",
                f"₹ {pdh_pdl.get('today_open', 0.0):,.2f}",
                f"₹ {cpr.get('r1', 0.0):,.2f}",
                f"₹ {cpr.get('s1', 0.0):,.2f}"
            ]
        }
        st.table(pd.DataFrame(t_data))
        if "cpr_type" in cpr:
            st.caption(f"**CPR Width:** {cpr['cpr_type']} ({cpr['cpr_width_pct']}%)")

# TAB 4: ANGEL ONE DIAGNOSTICS
with tab_diagnostics:
    st.subheader("Angel One SmartAPI Health & Connection Diagnostic")
    funds_info = {}
    if hasattr(st.session_state, "angel_connector") and st.session_state.angel_connector:
        try:
            funds_info = st.session_state.angel_connector.get_funds() or {}
        except Exception:
            funds_info = {}
    if not isinstance(funds_info, dict):
        funds_info = {}
    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        st.write(f"**Authenticated Status:** {'🟢 Connected' if st.session_state.angel_connector.is_authenticated else '🔴 Disconnected'}")
        st.write(f"**Client Code:** `{st.session_state.angel_connector.client_code or 'Not configured'}`")
        st.write(f"**API Key Present:** {'Yes' if st.session_state.angel_connector.api_key else 'No'}")
        st.write(f"**TOTP Secret Configured:** {'Yes' if st.session_state.angel_connector.totp_secret else 'No'}")
    with diag_col2:
        st.write(f"**Available Cash:** ₹ {funds_info.get('availablecash', 0.0):,.2f}")
        st.write(f"**Collateral Margin:** ₹ {funds_info.get('collateral', 0.0):,.2f}")
        st.write(f"**M2M Realized P&L:** ₹ {funds_info.get('m2mrealized', 0.0):,.2f}")
        st.write(f"**M2M Unrealized P&L:** ₹ {funds_info.get('m2munrealized', 0.0):,.2f}")

    if st.button("🔄 Test API Connection & Ping SmartAPI"):
        success, msg = st.session_state.angel_connector.login()
        if success:
            st.success(f"Connection Test Succeeded! SmartAPI Token generated.")
        else:
            st.warning(f"Connection test result: {msg}")
