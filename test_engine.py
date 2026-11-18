"""
Unit verification script for the Indian Stock Market Trading Engine.
Tests data retrieval, confluence strategy, chart rendering, and 1-Click Order Execution.
"""
from angel_connector import AngelOneConnector
from confluence_strategy import ConfluenceStrategy
from chart_plotter import ChartPlotter
from order_manager import OrderManager
import logging

logging.basicConfig(level=logging.INFO)

def run_tests():
    print("=== Step 1: Initializing Angel Connector ===")
    connector = AngelOneConnector()
    print("Checking funds info:", connector.get_funds())
    
    print("\n=== Step 2: Testing Live Quote API (/market/v1/quote/) ===")
    quote = connector.get_market_quote("NIFTY", mode="FULL")
    print(f"Quote status: {quote['status']}, LTP: {quote['ltp']}, Order Flow Ratio: {quote['order_flow_ratio']}%")
    print(f"Top Bid: {quote['depth']['buy'][0] if quote['depth']['buy'] else 'N/A'}")
    print(f"Top Ask: {quote['depth']['sell'][0] if quote['depth']['sell'] else 'N/A'}")
    assert quote["ltp"] > 0, "LTP must be greater than zero!"

    print("\n=== Step 2b: Testing Live Option Premium Retrieval from Angel One Exchange (NFO) ===")
    opt_quotes = connector.get_options_market_quotes("NIFTY", strike=25250, current_spot_ltp=quote["ltp"])
    print(f"Option Quotes Status: {opt_quotes['status']}")
    ce_q = opt_quotes["call_option"]
    pe_q = opt_quotes["put_option"]
    print(f"Live CE Quote -> Symbol: {ce_q['symbol']}, LTP: ₹{ce_q['ltp']}, Bid: ₹{ce_q['best_bid']}, Ask: ₹{ce_q['best_ask']}")
    print(f"Live PE Quote -> Symbol: {pe_q['symbol']}, LTP: ₹{pe_q['ltp']}, Bid: ₹{pe_q['best_bid']}, Ask: ₹{pe_q['best_ask']}")
    assert ce_q["ltp"] > 0, "CE option LTP must be greater than zero!"
    assert pe_q["ltp"] > 0, "PE option LTP must be greater than zero!"

    print("\n=== Step 3: Multi-Timeframe Candle Retrieval ===")
    mtf_data = connector.get_multi_timeframe_data("NIFTY", timeframes=("1m", "5m", "15m", "1h"))
    for tf, df in mtf_data.items():
        print(f"Timeframe {tf}: {len(df)} candles loaded. Latest Close: {df['close'].iloc[-1]}")
        assert not df.empty, f"Dataframe for {tf} should not be empty!"

    print("\n=== Step 4: Testing Confluence Strategy (Intraday & F&O with Order Flow) ===")
    strategy = ConfluenceStrategy(symbol="NIFTY", mode="FNO_INDICES")
    plan = strategy.analyze(mtf_data, live_quote=quote)

    print("Signal:", plan["signal"])
    print("Direction:", plan["direction"])
    print("Current Price:", plan["current_price"])
    print("Entry Price:", plan["entry_price"])
    print("Stop Loss:", plan["stop_loss"])
    print("Target 1:", plan["target_1"])
    print("Target 2:", plan["target_2"])
    print("Target 3:", plan["target_3"])
    print("Risk-to-Reward:", plan["risk_reward_ratio"])
    
    if plan["fno_recommendation"]:
        fno = plan["fno_recommendation"]
        print(f"F&O Recommendation: Strike {fno['strike']}, Approx Prem: {fno['approx_premium']}, SL: {fno['option_stop_loss']}, T1: {fno['option_target_1']}")
        assert "call_option" in fno, "call_option must be present in fno_recommendation!"
        assert "put_option" in fno, "put_option must be present in fno_recommendation!"
        ce_rec = fno["call_option"]
        pe_rec = fno["put_option"]
        print(f"Verified Dual Options -> CE: {ce_rec['strike']}, Prem: ₹{ce_rec['approx_premium']} | PE: {pe_rec['strike']}, Prem: ₹{pe_rec['approx_premium']}")
        assert ce_rec["atm_strike"] > 0, "CE ATM strike must be > 0"
        assert pe_rec["atm_strike"] > 0, "PE ATM strike must be > 0"
        assert ce_rec["approx_premium"] > 0, "CE Approx premium must be > 0"
        assert pe_rec["approx_premium"] > 0, "PE Approx premium must be > 0"

    print("\n=== Step 4: Testing 1-Click Order Execution (Paper Trading Isolated Test) ===")
    from pathlib import Path
    test_wallet_file = Path(__file__).resolve().parent / "data" / "test_wallet.json"
    test_trades_file = Path(__file__).resolve().parent / "data" / "test_trades.json"
    if test_wallet_file.exists():
        test_wallet_file.unlink()
    if test_trades_file.exists():
        test_trades_file.unlink()

    order_mgr = OrderManager(connector, wallet_file=test_wallet_file, trades_file=test_trades_file)
    trade_res = order_mgr.execute_trade_from_plan(plan, quantity=1, is_paper_trade=True)
    print("Trade Execution Result:", trade_res)
    assert trade_res["status"] is True, "Trade execution should succeed!"
    
    trade_id = trade_res["trade_id"]
    print("Open positions count:", len(order_mgr.get_open_positions()))
    
    # Test squaring off with valid target exit price
    opt_exit = plan["fno_recommendation"]["option_target_1"] if plan.get("fno_recommendation") else plan["target_1"]
    sq_res = order_mgr.square_off_trade(trade_id, exit_price=opt_exit)
    print(f"Square off status: {sq_res}")
    assert sq_res is True, "Trade square off should succeed!"

    # CRITICAL VERIFICATION: Test Stop Loss & Target P&L Calculations for both PE and CE options
    print("\n=== Step 4b: Verifying PE & CE Stop Loss ALWAYS produces LOSS (never profit) ===")
    # 1. PE Option with STOP LOSS HIT
    pe_trade_res = order_mgr.execute_custom_trade(
        symbol="NIFTY",
        direction="SELL",
        trade_type="Options PE",
        quantity_lots=1,
        entry_price=131.2,
        sl_price=98.4,
        target_1=178.9,
        target_2=214.7,
        custom_strike="NIFTY 25250 PE",
        underlying_entry=25257.1,
        underlying_sl=25300.0,
        underlying_t1=25200.0,
        underlying_t2=25150.0
    )
    assert pe_trade_res["status"] is True
    pe_trade_id = pe_trade_res["trade_id"]

    # Square off at Stop Loss price (98.4 vs entry 131.2)
    order_mgr.square_off_trade(pe_trade_id, exit_price=98.4, exit_reason="STOP_LOSS_HIT")
    closed = order_mgr.get_closed_trades()
    pe_closed = next(t for t in closed if t["id"] == pe_trade_id)
    print(f"PE Stop Loss Exit -> Net P&L: ₹{pe_closed['net_pnl']}, Is Profit: {pe_closed['is_profit']}")
    assert pe_closed["gross_pnl"] < 0, f"PE Stop Loss Gross P&L must be negative! Got {pe_closed['gross_pnl']}"
    assert pe_closed["net_pnl"] < 0, f"PE Stop Loss Net P&L must be negative! Got {pe_closed['net_pnl']}"
    assert pe_closed["is_profit"] is False, f"PE Stop Loss must be LOSS (is_profit=False)! Got {pe_closed['is_profit']}"

    # 2. PE Option with TARGET HIT
    pe_tgt_res = order_mgr.execute_custom_trade(
        symbol="NIFTY",
        direction="SELL",
        trade_type="Options PE",
        quantity_lots=1,
        entry_price=131.2,
        sl_price=98.4,
        target_1=178.9,
        target_2=214.7,
        custom_strike="NIFTY 25250 PE",
        underlying_entry=25257.1,
        underlying_sl=25300.0,
        underlying_t1=25200.0,
        underlying_t2=25150.0
    )
    assert pe_tgt_res["status"] is True
    pe_tgt_id = pe_tgt_res["trade_id"]
    order_mgr.square_off_trade(pe_tgt_id, exit_price=214.7, exit_reason="TARGET_2_HIT")
    pe_tgt_closed = next(t for t in order_mgr.get_closed_trades() if t["id"] == pe_tgt_id)
    print(f"PE Target Exit -> Net P&L: ₹{pe_tgt_closed['net_pnl']}, Is Profit: {pe_tgt_closed['is_profit']}")
    assert pe_tgt_closed["gross_pnl"] > 0, f"PE Target Gross P&L must be positive! Got {pe_tgt_closed['gross_pnl']}"
    assert pe_tgt_closed["net_pnl"] > 0, f"PE Target Net P&L must be positive! Got {pe_tgt_closed['net_pnl']}"
    assert pe_tgt_closed["is_profit"] is True, f"PE Target must be PROFIT (is_profit=True)!"

    # 3. Verify check_live_triggers does NOT instantly trigger false exit on normal spot tick
    ce_test_res = order_mgr.execute_custom_trade(
        symbol="NIFTY",
        direction="BUY",
        trade_type="Options CE",
        quantity_lots=1,
        entry_price=100.0,
        sl_price=75.0,
        target_1=135.0,
        target_2=160.0,
        custom_strike="NIFTY 25300 CE",
        underlying_entry=25250.0,
        underlying_sl=25200.0,
        underlying_t1=25300.0,
        underlying_t2=25350.0
    )
    ce_test_id = ce_test_res["trade_id"]
    # Pass current spot 25255 (between 25200 and 25350)
    alerts = order_mgr.check_live_triggers("NIFTY", current_ltp=25255.0)
    ce_open_check = [t for t in order_mgr.get_open_positions() if t["id"] == ce_test_id]
    print(f"Live Trigger check at spot 25255 -> Open count: {len(ce_open_check)}, Alerts: {alerts}")
    assert len(ce_open_check) == 1, "Position must NOT be closed instantly by spot tick!"

    # Clean up test files
    if test_wallet_file.exists():
        test_wallet_file.unlink()
    if test_trades_file.exists():
        test_trades_file.unlink()

    print("\n=== Step 5: Generating Plotly Chart Figure ===")
    fig = ChartPlotter.create_trade_chart(
        df=mtf_data["5m"],
        trade_plan=plan,
        timeframe="5m"
    )
    print("Chart Figure successfully created with trace count:", len(fig.data))

    # Test Bank Nifty Switching
    print("\n=== Step 6: Testing Automatic Symbol Switching to BANKNIFTY ===")
    bn_quote = connector.get_market_quote("BANKNIFTY", mode="FULL")
    print(f"Bank Nifty LTP: {bn_quote['ltp']}, Exchange: {bn_quote['exchange']}")
    assert bn_quote["ltp"] > 0, "Bank Nifty LTP must be valid!"
    bn_data = connector.get_multi_timeframe_data("BANKNIFTY", timeframes=("5m", "15m"))
    assert not bn_data["5m"].empty, "Bank Nifty 5m data must load!"
    bn_plan = ConfluenceStrategy(symbol="BANKNIFTY", mode="FNO_INDICES").analyze(bn_data, live_quote=bn_quote)
    print(f"Bank Nifty Signal: {bn_plan['signal']}, Entry: {bn_plan['entry_price']}, SL: {bn_plan['stop_loss']}")
    if bn_plan["fno_recommendation"]:
        print(f"Bank Nifty F&O Strike: {bn_plan['fno_recommendation']['strike']}, Lot Size: {bn_plan['fno_recommendation']['lot_size']}")
        assert bn_plan['fno_recommendation']['lot_size'] == 15, "Bank Nifty lot size must be 15!"

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
