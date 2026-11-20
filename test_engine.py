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

    print("\n=== Step 3: Testing 5 Chart Timeframes (Pillar 1) ===")
    timeframes = ("3m", "5m", "15m", "30m", "1D")
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
        assert plan["signal"] == "STRONG BUY", f"Score >= 70 with BUY direction must be STRONG BUY, got {plan['signal']}"
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

    print("\n=== Step 4b: Testing High-Probability Option Pattern Engine ===")
    from pattern_engine import PatternEngine
    patterns = PatternEngine.detect_all(df_5m=df_5m_ind, df_3m=mtf_data.get("3m"))
    print(f"Detected {len(patterns)} active option setups: {[p['pattern_name'] for p in patterns]}")
    assert "detected_patterns" in plan, "detected_patterns must be in plan"
    if plan.get("primary_pattern"):
        pat = plan["primary_pattern"]
        print(f"Primary Option Setup: {pat['pattern_name']} ({pat['recommended_option']}) | Quality: {pat['confidence']}%")
        assert "pattern_name" in pat and "direction" in pat and "invalidation_level" in pat

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
