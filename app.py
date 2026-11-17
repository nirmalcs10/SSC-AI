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


# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("🇮🇳 Indian Market Tool")
st.sidebar.caption("Angel One SmartAPI • Multi-Timeframe Engine")

# Trading Mode Selection
mode = st.sidebar.selectbox(
    "Trading Mode",
    ["Indices F&O (Options/Futures)", "Intraday Equity & Index", "Swing Trading"],
    index=0
)
mode_code = "FNO_INDICES" if "F&O" in mode else ("SWING" if "Swing" in mode else "INTRADAY")

# Symbol Selection
if "F&O" in mode:
    symbol_options = list(INDEX_TOKENS.keys())
else:
    symbol_options = list(INDEX_TOKENS.keys()) + list(POPULAR_STOCKS.keys())

selected_symbol = st.sidebar.selectbox("Select Symbol / Index", symbol_options, index=0)

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
st.sidebar.metric("Virtual Balance", f"₹ {wallet_state.get('balance', 100000.0):,.2f}")
st.sidebar.metric("Realized P&L", f"₹ {wallet_state.get('realized_pnl', 0.0):,.2f}")
if st.sidebar.button("🔄 Reset Wallet to ₹1,00,000", help="Resets virtual capital and trade history"):
    st.session_state.order_manager.reset_wallet(100000.0)
    st.sidebar.success("Wallet reset to ₹1,00,000!")
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


# --- MAIN LOGIC ---
timeframes = ("15m", "1h", "1D") if mode_code == "SWING" else ("1m", "5m", "15m", "1h")

if analyze_btn or st.session_state.last_analysis is None:
    with st.spinner(f"Fetching multi-timeframe candles (1m, 5m, 15m, 1h) for {selected_symbol}..."):
        mtf_data = connector.get_multi_timeframe_data(selected_symbol, timeframes=timeframes)
        st.session_state.mtf_data = mtf_data
        
        strategy = ConfluenceStrategy(symbol=selected_symbol, mode=mode_code)
        plan = strategy.analyze(mtf_data, live_quote=live_quote)
        st.session_state.last_analysis = plan


plan = st.session_state.last_analysis
mtf_data = st.session_state.mtf_data


# --- LIVE MARKET QUOTE & ORDER-FLOW BANNER ---
lq_col1, lq_col2, lq_col3, lq_col4 = st.columns([1.5, 1.2, 1.5, 1])
with lq_col1:
    chg_color = "#00E676" if live_quote["change"] >= 0 else "#FF1744"
    chg_sign = "+" if live_quote["change"] >= 0 else ""
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
        <span style="font-size: 13px; color: #8B949E;">Angel One Live LTP ({live_quote['exchange']})</span><br>
        <span style="font-size: 24px; font-weight: bold; color: #ECEFF1;">₹ {live_quote['ltp']:,.2f}</span>
        <span style="color: {chg_color}; font-size: 14px; font-weight: bold; margin-left: 8px;">{chg_sign}{live_quote['change']} ({chg_sign}{live_quote['percent_change']}%)</span>
    </div>
    """, unsafe_allow_html=True)

with lq_col2:
    of_ratio = live_quote.get("order_flow_ratio", 50.0)
    dom_text = "Buyers in Control" if of_ratio > 50 else "Sellers in Control"
    dom_color = "#00C853" if of_ratio > 50 else "#FF1744"
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
        <span style="font-size: 13px; color: #8B949E;">Order-Flow Dominance</span><br>
        <span style="font-size: 15px; font-weight: bold; color: {dom_color};">{dom_text} ({of_ratio}%)</span>
        <div style="background: #30363D; border-radius: 4px; height: 6px; width: 100%; margin-top: 6px;">
            <div style="background: {dom_color}; height: 6px; width: {of_ratio}%; border-radius: 4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with lq_col3:
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
        <span style="font-size: 13px; color: #8B949E;">Day High / Low & Volume</span><br>
        <span style="font-size: 14px; color: #ECEFF1;">H: ₹{live_quote['high']:,.1f} | L: ₹{live_quote['low']:,.1f}</span><br>
        <span style="font-size: 12px; color: #8B949E;">Vol: {live_quote['volume']:,} | OI: {live_quote['oi']:,}</span>
    </div>
    """, unsafe_allow_html=True)

with lq_col4:
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 10px 14px; border-radius: 8px; border: 1px solid #30363D;">
        <span style="font-size: 13px; color: #8B949E;">Virtual Capital Balance</span><br>
        <span style="font-size: 18px; font-weight: bold; color: #00E5FF;">₹ {wallet_state.get('balance', 100000.0):,.0f}</span><br>
        <span style="font-size: 11px; color: #00E676;">100% Risk-Free Simulation</span>
    </div>
    """, unsafe_allow_html=True)


# Market Depth 5-Level Table Expander
with st.expander(f"📊 Live 5-Level Market Depth Ladder — {selected_symbol}"):
    depth = live_quote.get("depth", {})
    bids = depth.get("buy", [])
    asks = depth.get("sell", [])
    
    if bids or asks:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown("<span style='color: #00E676; font-weight: bold;'>Top 5 Bids (Buyers)</span>", unsafe_allow_html=True)
            if bids:
                df_bids = pd.DataFrame(bids)
                df_bids.columns = [c.capitalize() for c in df_bids.columns]
                st.dataframe(df_bids, use_container_width=True)
        with col_d2:
            st.markdown("<span style='color: #FF1744; font-weight: bold;'>Top 5 Asks (Sellers)</span>", unsafe_allow_html=True)
            if asks:
                df_asks = pd.DataFrame(asks)
                df_asks.columns = [c.capitalize() for c in df_asks.columns]
                st.dataframe(df_asks, use_container_width=True)
    else:
        st.info("Live 5-level market depth ladder is active during market hours with Angel One SmartAPI login.")


# --- HEADER & ACCOUNT STATUS ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title(f"{selected_symbol} — Multi-Timeframe Automated Plan")
    st.caption(f"Current Mode: **{mode}** | Timeframes: **{', '.join(timeframes)}** | Updated: {datetime.datetime.now().strftime('%H:%M:%S IST')}")
with col_head2:
    if plan:
        st.metric("Setup Current Price", f"₹ {plan.get('current_price', 0.0):,.2f}")


# --- TRADE SIGNAL CARD ---
if plan:
    direction = plan.get("direction", "NEUTRAL")
    signal = plan.get("signal", "WAIT")
    card_class = "buy-card" if direction == "BUY" else ("sell-card" if direction == "SELL" else "wait-card")
    icon = "🚀" if direction == "BUY" else ("🔻" if direction == "SELL" else "⏳")

    st.markdown(f"""
    <div class="trade-card {card_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="margin: 0;">{icon} Signal: {signal} ({direction})</h2>
            <h3 style="margin: 0; color: #FFD600;">Confluence Score: {plan.get('confluence_score', 0)} / 100</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key Trade Metrics Columns
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1:
        st.metric("Take Trade Price (Entry)", f"₹ {plan.get('entry_price', 0.0):,.2f}")
    with m_col2:
        st.metric("Stop Loss (SL)", f"₹ {plan.get('stop_loss', 0.0):,.2f}", delta=f"-{plan.get('risk_points', 0.0)} pts", delta_color="inverse")
    with m_col3:
        st.metric("Target 1 (1:1.5 RR)", f"₹ {plan.get('target_1', 0.0):,.2f}")
    with m_col4:
        st.metric("Target 2 (1:2.5 RR)", f"₹ {plan.get('target_2', 0.0):,.2f}")
    with m_col5:
        st.metric("Target 3 (Major S/R)", f"₹ {plan.get('target_3', 0.0):,.2f}")
    with m_col6:
        st.metric("Risk-Reward Ratio", plan.get("risk_reward_ratio", "1:2"))

    # F&O Options Recommendation Box (for Index Trading)
    fno = plan.get("fno_recommendation")
    if fno:
        st.markdown("### 🎯 F&O Option Strike & Premium Trade Recommendation")
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
        with f_col1:
            st.metric("Recommended Strike", fno["strike"], help="ATM / slightly ITM Option contract")
        with f_col2:
            st.metric("Estimated Option Entry", f"₹ {fno['approx_premium']:.1f}")
        with f_col3:
            st.metric("Option Stop Loss", f"₹ {fno['option_stop_loss']:.1f}", delta=f"-{round(fno['approx_premium'] - fno['option_stop_loss'], 1)} pts", delta_color="inverse")
        with f_col4:
            st.metric("Option Target 1", f"₹ {fno['option_target_1']:.1f}")
        with f_col5:
            st.metric("Option Target 2", f"₹ {fno['option_target_2']:.1f}")

    # 1-Click Virtual Paper Trading Execution Panel
    if direction in ("BUY", "SELL"):
        st.markdown("""<div class="execution-box">""", unsafe_allow_html=True)
        st.markdown("<span style='color: #00E5FF; font-weight: bold; font-size: 16px;'>📝 1-Click Virtual Paper Trade Execution (Zero Real Money Risk)</span>", unsafe_allow_html=True)
        st.caption("Fills order on virtual balance with realistic Rs.20 brokerage + STT charges and automatic SL/Target exits.")
        exec_col1, exec_col2 = st.columns([1, 2])
        
        with exec_col1:
            default_qty = 1 if not fno else 1
            if fno:
                fno_lot_size = fno.get("lot_size", 65)
                qty_label = f"Lots (Options F&O) — 1 Lot = {fno_lot_size} Qty"
                trade_qty = st.number_input(qty_label, min_value=1, max_value=50, value=default_qty, step=1)
                total_units = int(trade_qty * fno_lot_size)
                approx_cap = total_units * float(fno.get("approx_premium", 0.0))
                st.caption(f"📦 **{total_units} Contracts** ({trade_qty} Lot × {fno_lot_size}) • Capital: **₹ {approx_cap:,.1f}**")
            else:
                trade_qty = st.number_input("Quantity (Shares)", min_value=1, max_value=5000, value=10, step=1)
                total_units = int(trade_qty)
        with exec_col2:
            st.write("")
            if fno:
                btn_label = f"🚀 Place Virtual {direction} Trade ({trade_qty} Lot = {total_units} Qty)"
            else:
                btn_label = f"🚀 Place Virtual {direction} Trade ({total_units} Shares)"
            if st.button(btn_label, type="primary", use_container_width=True):
                with st.spinner("Opening virtual position with Stop Loss & Target..."):
                    exec_res = st.session_state.order_manager.execute_trade_from_plan(
                        plan=plan,
                        quantity=int(trade_qty),
                        is_paper_trade=True
                    )
                    if exec_res.get("status"):
                        st.success(exec_res.get("message"))
                        st.rerun()
                    else:
                        st.error(exec_res.get("message"))
        st.markdown("""</div>""", unsafe_allow_html=True)


# --- DASHBOARD TABS ---
tab_chart, tab_positions, tab_rationale, tab_diagnostics = st.tabs([
    "📊 Multi-Timeframe Chart & Overlays",
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
                "🔲 Quad Confluence Grid (1h + 15m + 5m + 1m)"
            ],
            horizontal=True
        )
    with view_col2:
        if "Quad" not in chart_view_mode:
            chart_tf = st.radio(
                "Timeframe:",
                options=list(timeframes),
                index=1 if "5m" in timeframes else 0,
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
        st.caption("Synchronized Multi-Timeframe Confluence Grid • Visualizing Macro (1h) down to Micro Trigger (1m)")
        grid_tf_pairs = [("1h", "15m"), ("5m", "1m")]
        
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
        st.metric("Brokerage & Taxes Simulated", f"₹ {wallet_state.get('total_charges', 0.0):,.2f}")

    st.markdown("---")
    st.subheader("Active Virtual Positions")
    open_trades = st.session_state.order_manager.get_open_positions()
    if not open_trades:
        st.info("No open virtual positions right now. Click 'Place Virtual Trade' on the signal card above to start a trade!")
    else:
        df_open = pd.DataFrame(open_trades)
        display_cols = ["id", "timestamp", "trading_symbol", "direction", "quantity", "entry_price", "current_price", "stop_loss", "target_1", "target_2", "net_pnl"]
        valid_cols = [c for c in display_cols if c in df_open.columns]
        st.dataframe(df_open[valid_cols], use_container_width=True)

        sq_col1, sq_col2 = st.columns([2, 1])
        with sq_col1:
            selected_trade_id = st.selectbox("Select Virtual Position to Square Off", [t["id"] for t in open_trades])
        with sq_col2:
            st.write("")
            st.write("")
            if st.button("❌ Square Off Position", type="secondary"):
                curr_p = live_quote.get("ltp", plan.get("current_price", 0.0))
                if st.session_state.order_manager.square_off_trade(selected_trade_id, curr_p, exit_reason="MANUAL_SQUARE_OFF"):
                    st.success(f"Position {selected_trade_id} squared off at ₹{curr_p}!")
                    st.rerun()

    # Closed trades history
    closed_trades = st.session_state.order_manager.get_closed_trades()
    if closed_trades:
        st.markdown("---")
        st.subheader("Completed Trade Journal")
        df_closed = pd.DataFrame(closed_trades)
        c_cols = ["id", "timestamp", "exit_time", "trading_symbol", "direction", "entry_price", "exit_price", "exit_reason", "gross_pnl", "charges", "net_pnl"]
        valid_c_cols = [c for c in c_cols if c in df_closed.columns]
        st.dataframe(df_closed[valid_c_cols], use_container_width=True)

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
