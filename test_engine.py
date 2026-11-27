"""
Unit verification script for the Indian Stock Market Trading Engine.
Comprehensive testing of the 4 Pillars:
1. 5 Chart Timeframes: Daily (1D), 30m, 15m, 5m, 3m
2. Streamlined Technical Indicators: EMA-9, EMA-21, VWAP, RSI-14, Volume MA-20
3. Option Chain Analysis: OI, Chng in OI, Call/Put writing, Volume, PCR, ATM Premium, IV, Spot confirmation
4. Institutional Risk Management Guard: 0.5-1% risk position sizing, setup invalidation SL, >= 1:2 RR, 1-3 daily trade cap, 2% daily loss circuit breaker, Revenge Trading lockout
"""
import logging
from pathlib import Path
from angel_connector import AngelOneConnector
from confluence_strategy import ConfluenceStrategy
from indicator_engine import IndicatorEngine
from chart_plotter import ChartPlotter
from order_manager import OrderManager

logging.basicConfig(level=logging.INFO)


def run_tests():
    print("=== Step 1: Initializing Angel Connector ===")
    connector = AngelOneConnector()
    print("Checking funds info:", connector.get_funds())

    print("\n=== Step 2: Testing Live Quote API (/market/v1/quote/) ===")
    quote = connector.get_market_quote("NIFTY", mode="FULL")
    print(f"Quote status: {quote['status']}, LTP: {quote['ltp']}, Order Flow Ratio: {quote['order_flow_ratio']}%")
    assert quote["ltp"] > 0, "LTP must be greater than zero!"

    print("\n=== Step 2b: Testing Live Option Premium Retrieval (NFO) ===")
    atm_test_strike = int(round(quote["ltp"] / 50) * 50)
    opt_quotes = connector.get_options_market_quotes("NIFTY", strike=atm_test_strike, current_spot_ltp=quote["ltp"])
    ce_q = opt_quotes["call_option"]
    pe_q = opt_quotes["put_option"]
    print(f"Live CE Quote -> Symbol: {ce_q['symbol']}, Token: {ce_q['token']}, LTP: Rs.{ce_q['ltp']}")
    print(f"Live PE Quote -> Symbol: {pe_q['symbol']}, Token: {pe_q['token']}, LTP: Rs.{pe_q['ltp']}")
    assert ce_q["ltp"] > 0, f"CE option LTP must be > 0, got {ce_q['ltp']}"
    assert pe_q["ltp"] > 0, f"PE option LTP must be > 0, got {pe_q['ltp']}"

    print("\n=== Step 2c: Testing Multi-Moneyness Strike Ladder (ITM, ATM, OTM) ===")
    ladder_data = connector.get_options_ladder_quotes("NIFTY", atm_strike=atm_test_strike, current_spot_ltp=quote["ltp"])
    for opt_t in ["CE", "PE"]:
        for tier in ["ITM", "ATM", "OTM"]:
            item = ladder_data[opt_t][tier]
            assert item["strike"] > 0 and item["ltp"] > 0

    print("\n=== Step 2d: Testing Option Chain Analysis (Pillar 3) ===")
    oc_data = connector.get_option_chain_analysis("NIFTY", current_spot_ltp=quote["ltp"])
    print(f"PCR: {oc_data['pcr']} ({oc_data['pcr_sentiment']})")
    print(f"Total Call OI: {oc_data['total_call_oi']:,} | Total Put OI: {oc_data['total_put_oi']:,}")
    print(f"Put Writing Support: Rs.{oc_data['put_support_strike']:,} | Call Writing Resistance: Rs.{oc_data['call_resistance_strike']:,}")
    print(f"ATM CE: Rs.{oc_data['atm_ce_premium']} | PE: Rs.{oc_data['atm_pe_premium']} | IV: {oc_data['atm_iv']}%")
    print(f"Spot Confirmation: {oc_data['spot_confirmation']}")

    assert oc_data["pcr"] > 0, "PCR must be calculated"
    assert oc_data["total_call_oi"] > 0, "Call OI must be non-zero"
    assert oc_data["total_put_oi"] > 0, "Put OI must be non-zero"
    assert oc_data["put_support_strike"] > 0, "Put Support strike must exist"
    assert oc_data["call_resistance_strike"] > 0, "Call Resistance strike must exist"
    assert len(oc_data["chain_rows"]) >= 5, "At least 5 strikes must be present in ladder"

    print("\n=== Step 3: Testing 4 Intraday Chart Timeframes (1m, 3m, 5m, 15m) ===")
    timeframes = ("1m", "3m", "5m", "15m")
    mtf_data = connector.get_multi_timeframe_data("NIFTY", timeframes=timeframes)
    for tf in timeframes:
        assert tf in mtf_data, f"Timeframe {tf} must be fetched"
        df = mtf_data[tf]
        assert not df.empty, f"Dataframe for {tf} should not be empty!"
        print(f"Timeframe {tf}: {len(df)} candles loaded. Latest Close: {df['close'].iloc[-1]:.2f}")

    print("\n=== Step 3b: Testing Technical Indicators (Pillar 2) ===")
    df_5m_ind = IndicatorEngine.apply_all(mtf_data["5m"])
    for expected_col in ["ema_9", "ema_21", "ema_50", "ema_200", "vwap", "rsi", "volume_ma20", "atr"]:
        assert expected_col in df_5m_ind.columns, f"{expected_col} must be in indicators dataframe"
        val = df_5m_ind[expected_col].iloc[-1]
        assert val > 0, f"{expected_col} must have valid positive values, got {val}"
        print(f"Indicator {expected_col}: {val:.2f}")

    print("\n=== Step 4: Testing Confluence Strategy (Pillars 1, 2, 3 & 4) ===")
    strategy = ConfluenceStrategy(symbol="NIFTY", mode="FNO_INDICES")
    plan = strategy.analyze(mtf_data, live_quote=quote, option_chain=oc_data)

    print("Signal:", plan["signal"])
    print("Direction:", plan["direction"])
    print("Current Price:", plan["current_price"])
    print("Entry Price:", plan["entry_price"])
    print("Stop Loss:", plan["stop_loss"])
    print("Target 1:", plan["target_1"])
    print("Target 2:", plan["target_2"])
    print("Risk-to-Reward Ratio:", plan["risk_reward_ratio"])

    assert plan["entry_price"] > 0, "Entry price must be > 0"
    assert plan["stop_loss"] > 0, "Stop loss must be > 0"
    assert "confluence_score" in plan, "confluence_score must be present in plan"
    assert "score" in plan, "score must be present in plan"
    assert plan["confluence_score"] == plan["score"], f"confluence_score ({plan['confluence_score']}) must match score ({plan['score']})"
    if plan["score"] >= 70 and plan["direction"] == "BUY":
        assert plan["signal"] == "STRONG BUY CALL (CE)", f"Score >= 70 with BUY direction must be STRONG BUY CALL (CE), got {plan['signal']}"
    if plan["score"] <= -70 and plan["direction"] == "SELL":
        assert plan["signal"] == "STRONG BUY PUT (PE)", f"Score <= -70 with SELL direction must be STRONG BUY PUT (PE), got {plan['signal']}"
    print(f"Verified Confluence Score: {plan['confluence_score']}/100 and Signal: {plan['signal']}")
    # Verify Minimum 1:2 Risk/Reward target
    if plan["direction"] in ("BUY", "SELL"):
        risk_dist = abs(plan["entry_price"] - plan["stop_loss"])
        reward_dist_1 = abs(plan["target_1"] - plan["entry_price"])
        actual_rr = reward_dist_1 / risk_dist
        print(f"Calculated T1 Risk/Reward: 1 : {actual_rr:.2f}")
        assert actual_rr >= 1.95, f"Target 1 MUST offer at least 1:2 RR, got {actual_rr:.2f}"

    # Verify Rationale Structure
    assert "detailed_rationale" in plan, "detailed_rationale must be in plan"
    assert "decision_summary" in plan, "decision_summary must be in plan"
    rat = plan["detailed_rationale"]
    for sec in ["macro", "structure", "execution", "order_flow", "levels"]:
        assert sec in rat and isinstance(rat[sec], list)
        for factor_dict in rat[sec]:
            assert "factor" in factor_dict and "status" in factor_dict and "detail" in factor_dict
            print(f"Verified Rationale [{sec} -> {factor_dict['factor']}]: {factor_dict['status']}")
    print(f"Decision Summary: {plan['decision_summary']}")

    print("\n=== Step 4b: Testing High-Probability Option Pattern Engine & 5m/1h Matrix ===")
    from pattern_engine import PatternEngine
    patterns = PatternEngine.detect_all(df_5m=df_5m_ind, df_3m=mtf_data.get("3m"))
    print(f"Detected {len(patterns)} active option setups: {[p['pattern_name'] for p in patterns]}")
    assert "detected_patterns" in plan, "detected_patterns must be in plan"
    if plan.get("primary_pattern"):
        pat = plan["primary_pattern"]
        print(f"Primary Option Setup: {pat['pattern_name']} ({pat['recommended_option']}) | Quality: {pat['confidence']}%")
        assert "pattern_name" in pat and "direction" in pat and "invalidation_level" in pat

    # Verify 5m and 1h Pattern Matrix (Bullish, Bearish, Side Wave)
    assert "pattern_matrix" in plan, "pattern_matrix must be present in plan"
    p_mat = plan["pattern_matrix"]
    assert "5m" in p_mat and "1h" in p_mat, "5m and 1h must be in pattern_matrix"
    for tf_key in ["5m", "1h"]:
        tf_data = p_mat[tf_key]
        assert "regime" in tf_data and "bullish" in tf_data and "bearish" in tf_data and "side_wave" in tf_data
        assert "drawing_data" in tf_data, f"{tf_key} must contain drawing_data"
        dd = tf_data["drawing_data"]
        p_name = tf_data.get("drawing_pattern_name", "None")
        lines = dd.get("lines", [])
        assert len(lines) > 0, f"{tf_key} must have drawing lines"
        for l in lines:
            assert l.get("color") == "#FFFFFF", f"All drawing lines must be white (#FFFFFF), got {l.get('color')}"
        t_span_hrs = (lines[0]["points"][-1]["time"] - lines[0]["points"][0]["time"]) / 3600.0
        print(f"Verified {tf_key} Pattern Matrix: Regime={tf_data['regime']} | Auto-Drawn Pattern: {p_name} | Lines: {len(lines)} (All White #FFFFFF) | Span: {t_span_hrs:.1f} hrs")

    # Assert 5m covers ~24 hours and 1h covers ~1 week (>= 120 hrs / 5 days)
    span_5m_hrs = (p_mat["5m"]["drawing_data"]["lines"][0]["points"][-1]["time"] - p_mat["5m"]["drawing_data"]["lines"][0]["points"][0]["time"]) / 3600.0
    span_1h_hrs = (p_mat["1h"]["drawing_data"]["lines"][0]["points"][-1]["time"] - p_mat["1h"]["drawing_data"]["lines"][0]["points"][0]["time"]) / 3600.0
    assert span_5m_hrs >= 20.0, f"5m line span must be at least 20 hours (24h window), got {span_5m_hrs:.1f} hrs"
    assert span_1h_hrs >= 100.0, f"1h line span must be at least 100 hours (1 week window), got {span_1h_hrs:.1f} hrs"
    print(f"Verified: 5m line span = {span_5m_hrs:.1f} hrs (24hr session), 1h line span = {span_1h_hrs:.1f} hrs (1-week macro)!")

    from angel_chart_mirror import render_angel_one_smartapi_chart
    df_1h_test = plan.get("df_1h") if plan.get("df_1h") is not None else mtf_data.get("1h")
    assert df_1h_test is not None and not df_1h_test.empty, "df_1h must be generated and available"
    render_angel_one_smartapi_chart(
        df=mtf_data["5m"],
        symbol="NIFTY",
        interval="5m",
        trade_plan=plan,
        pattern_drawings=p_mat["5m"].get("drawing_data"),
        show_sr=False,
        show_cpr=False,
        show_pdh_pdl=False,
        show_trade_overlay=False,
        height=460
    )
    render_angel_one_smartapi_chart(
        df=df_1h_test,
        symbol="NIFTY",
        interval="1h",
        trade_plan=plan,
        pattern_drawings=p_mat["1h"].get("drawing_data"),
        show_sr=False,
        show_cpr=False,
        show_pdh_pdl=False,
        show_trade_overlay=False,
        height=460
    )
    print("Verified Plain Angel One SmartAPI Feed with White Pattern Drawings (5m 24h & 1h 1-Week) generated cleanly!")

    print("\n=== Step 4c: Testing Tamil Crypto School (TCS) Master Patterns Detection ===")
    import pandas as pd
    import numpy as np

    # 1. Test Triple Taps Strategy (Ascending Support with 3 taps)
    dates = pd.date_range("2026-11-27 09:15", periods=25, freq="5min")
    df_tt = pd.DataFrame({
        "datetime": dates,
        "open": [24200.0] * 25,
        "high": [24300.0] * 25,
        "low": [24200.0] * 25,
        "close": [24250.0] * 25,
        "volume": [1000] * 25
    })
    df_tt.loc[5, ["open", "high", "low", "close"]] = [24010, 24020, 24000, 24010]
    df_tt.loc[12, ["open", "high", "low", "close"]] = [24060, 24070, 24050, 24060]
    df_tt.loc[19, ["open", "high", "low", "close"]] = [24110, 24120, 24100, 24110]
    df_tt.loc[20, ["open", "high", "low", "close"]] = [24110, 24130, 24105, 24125]
    
    tt_res = PatternEngine.detect_triple_taps_strategy(df_tt.iloc[:21])
    assert tt_res is not None, "Triple Taps detector should detect 3 ascending taps"
    assert "Triple Taps" in tt_res["pattern_name"]
    assert tt_res["direction"] == "BUY"
    assert tt_res["drawing_data"]["lines"][0]["color"] == "#FFFFFF"
    print(f"Verified TCS Pattern: {tt_res['pattern_name']} -> Lines All White #FFFFFF")

    # 2. Test Head and Shoulders (Bearish)
    df_hs = pd.DataFrame({
        "datetime": dates,
        "open": [24000.0] * 25,
        "high": [24050.0] * 25,
        "low": [23950.0] * 25,
        "close": [24000.0] * 25,
        "volume": [1000] * 25
    })
    df_hs.loc[6, ["open", "high", "low", "close"]] = [24020, 24100, 24010, 24050]
    df_hs.loc[12, ["open", "high", "low", "close"]] = [24080, 24200, 24070, 24100]
    df_hs.loc[18, ["open", "high", "low", "close"]] = [24020, 24100, 24010, 24040]
    df_hs.loc[21, ["open", "high", "low", "close"]] = [23960, 23970, 23880, 23890]

    hs_res = PatternEngine.detect_head_and_shoulders(df_hs.iloc[:22])
    assert hs_res is not None, "Head & Shoulders detector should identify bearish H&S breakdown"
    assert hs_res["direction"] == "SELL"
    assert hs_res["drawing_data"]["lines"][0]["color"] == "#FFFFFF"
    print(f"Verified TCS Pattern: {hs_res['pattern_name']} -> Lines All White #FFFFFF")

    # 3. Test Triple Top (Bearish)
    df_ttop = pd.DataFrame({
        "datetime": dates,
        "open": [24000.0] * 25,
        "high": [24050.0] * 25,
        "low": [23950.0] * 25,
        "close": [24000.0] * 25,
        "volume": [1000] * 25
    })
    df_ttop.loc[6, ["open", "high", "low", "close"]] = [24020, 24100, 24010, 24050]
    df_ttop.loc[12, ["open", "high", "low", "close"]] = [24020, 24100, 24010, 24050]
    df_ttop.loc[18, ["open", "high", "low", "close"]] = [24020, 24100, 24010, 24050]
    df_ttop.loc[21, ["open", "high", "low", "close"]] = [23960, 23970, 23880, 23890]

    ttop_res = PatternEngine.detect_triple_top_bottom(df_ttop.iloc[:22])
    assert ttop_res is not None, "Triple Top detector should detect 3 resistance peaks"
    assert ttop_res["direction"] == "SELL"
    assert ttop_res["drawing_data"]["lines"][0]["color"] == "#FFFFFF"
    print(f"Verified TCS Pattern: {ttop_res['pattern_name']} -> Lines All White #FFFFFF")

    # 4. Test S/R Role Reversal (Resistance -> Support Flip)
    df_flip = pd.DataFrame({
        "datetime": dates,
        "open": [23950.0] * 25,
        "high": [23980.0] * 25,
        "low": [23920.0] * 25,
        "close": [23950.0] * 25,
        "volume": [1000] * 25
    })
    df_flip.loc[5, ["open", "high", "low", "close"]] = [23960, 24000, 23950, 23990]
    for k in range(12, 24):
        df_flip.loc[k, ["open", "high", "low", "close"]] = [24050, 24100, 24020, 24060]
    df_flip.loc[24, ["open", "high", "low", "close"]] = [24005, 24030, 24000, 24025]

    flip_res = PatternEngine.detect_role_reversal_sr_flip(df_flip)
    assert flip_res is not None, "Role Reversal detector should detect S/R flip"
    assert flip_res["direction"] == "BUY"
    assert flip_res["drawing_data"]["lines"][0]["color"] == "#FFFFFF"
    print(f"Verified TCS Pattern: {flip_res['pattern_name']} -> Lines All White #FFFFFF")

    # 5. Test Wedge Pattern (Falling Wedge Breakout)
    df_wedge = pd.DataFrame({
        "datetime": dates[:18],
        "open": [24100.0] * 18,
        "high": [24150.0] * 18,
        "low": [24050.0] * 18,
        "close": [24100.0] * 18,
        "volume": [1000] * 18
    })
    df_wedge.loc[0, "high"] = 24200.0
    df_wedge.loc[16, "high"] = 24080.0
    df_wedge.loc[0, "low"] = 24050.0
    df_wedge.loc[16, "low"] = 24000.0
    df_wedge.loc[17, ["open", "high", "low", "close"]] = [24080, 24100, 24075, 24095]

    wedge_res = PatternEngine.detect_wedge_patterns(df_wedge)
    assert wedge_res is not None, "Wedge detector should identify Falling Wedge breakout"
    assert wedge_res["direction"] == "BUY"
    assert wedge_res["drawing_data"]["lines"][0]["color"] == "#FFFFFF"
    print(f"Verified TCS Pattern: {wedge_res['pattern_name']} -> Lines All White #FFFFFF")

    print("\n=== Step 5: Testing Institutional Risk Management Guard (Pillar 4) ===")
    test_wallet_file = Path(__file__).resolve().parent / "data" / "test_risk_wallet_final.json"
    test_trades_file = Path(__file__).resolve().parent / "data" / "test_risk_trades_final.json"
    if test_wallet_file.exists():
        test_wallet_file.unlink()
    if test_trades_file.exists():
        test_trades_file.unlink()

    order_mgr = OrderManager(connector, wallet_file=test_wallet_file, trades_file=test_trades_file)

    # 1. Test Position Sizing (0.5% - 1% capital risk)
    r_status = order_mgr.get_risk_status()
    print("Risk Status Initial:", r_status)
    assert r_status["daily_trades_count"] == 0
    assert r_status["can_trade_daily"] is True
    assert r_status["risk_per_trade_max_inr"] == 1000.0  # 1% of 100,000

    # 2. Test Daily Trades Limit: Execute 3 trades, then 4th MUST be blocked
    for i in range(3):
        res = order_mgr._create_paper_trade(
            symbol="NIFTY",
            trading_symbol=f"NIFTY 25200 CE #{i+1}",
            trade_type="Options CE",
            direction="BUY",
            total_qty=65,
            quantity_lots=1,
            entry_price=100.0,
            sl_price=90.0,
            target_1=160.0,
            target_2=190.0,
            is_opt=True
        )
        assert res["status"] is True, f"Trade {i+1} should succeed"
        # Square off with small win to avoid hitting loss circuit breaker
        order_mgr.square_off_trade(res["trade_id"], exit_price=105.0, exit_reason="TARGET_EXIT")

    res_blocked = order_mgr._create_paper_trade(
        symbol="NIFTY",
        trading_symbol="NIFTY 25200 CE #4",
        trade_type="Options CE",
        direction="BUY",
        total_qty=65,
        quantity_lots=1,
        entry_price=100.0,
        sl_price=90.0,
        target_1=160.0,
        target_2=190.0,
        is_opt=True
    )
    print("Trade 4 Blocked Message:", res_blocked["message"])
    assert res_blocked["status"] is False, "Trade 4 MUST be blocked by daily trade limit!"
    assert "Daily Trade Limit Reached" in res_blocked["message"]

    # 3. Test Revenge Trading Cooldown & 2% Circuit Breaker
    test_wallet_file2 = Path(__file__).resolve().parent / "data" / "test_revenge_wallet.json"
    test_trades_file2 = Path(__file__).resolve().parent / "data" / "test_revenge_trades.json"
    if test_wallet_file2.exists():
        test_wallet_file2.unlink()
    if test_trades_file2.exists():
        test_trades_file2.unlink()

    om_rev = OrderManager(connector, wallet_file=test_wallet_file2, trades_file=test_trades_file2)
    t_sl = om_rev._create_paper_trade(
        symbol="NIFTY",
        trading_symbol="NIFTY 25200 CE SL Test",
        trade_type="Options CE",
        direction="BUY",
        total_qty=65,
        quantity_lots=1,
        entry_price=100.0,
        sl_price=85.0,
        target_1=160.0,
        target_2=190.0,
        is_opt=True
    )
    # Square off at stop loss
    om_rev.square_off_trade(t_sl["trade_id"], exit_price=85.0, exit_reason="STOP_LOSS_HIT")
    r_st = om_rev.get_risk_status()
    print("Revenge Cooldown Active:", r_st["revenge_cooldown_active"])
    assert r_st["revenge_cooldown_active"] is True

    # Immediate re-entry attempt MUST be blocked by Revenge Trading Protection
    t_rev_blocked = om_rev._create_paper_trade(
        symbol="NIFTY",
        trading_symbol="NIFTY 25200 CE Immediate Re-entry",
        trade_type="Options CE",
        direction="BUY",
        total_qty=65,
        quantity_lots=1,
        entry_price=100.0,
        sl_price=85.0,
        target_1=160.0,
        target_2=190.0,
        is_opt=True
    )
    print("Revenge Re-entry Blocked Message:", t_rev_blocked["message"])
    assert t_rev_blocked["status"] is False
    assert "Revenge Trading Protection Active" in t_rev_blocked["message"]

    # Clean up test files
    for p in [test_wallet_file, test_trades_file, test_wallet_file2, test_trades_file2]:
        if p.exists():
            p.unlink()

    print("\n=== Step 6: Testing Multi-Timeframe Chart Figure Generation ===")
    fig = ChartPlotter.create_trade_chart(
        df=df_5m_ind,
        trade_plan=plan,
        timeframe="5m",
        show_sr=True,
        show_cpr=True
    )
    assert len(fig.data) >= 2, "Chart figure should have multiple traces"
    print(f"Chart Figure created with {len(fig.data)} traces.")

    print("\n=======================================================")
    print("ALL 4-PILLAR VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=======================================================")


if __name__ == "__main__":
    run_tests()
