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

    print("\n=== Step 4: Testing 1-Click Order Execution (Paper Trading) ===")
    order_mgr = OrderManager(connector)
    trade_res = order_mgr.execute_trade_from_plan(plan, quantity=1, is_paper_trade=True)
    print("Trade Execution Result:", trade_res)
    assert trade_res["status"] is True, "Trade execution should succeed!"
    
    trade_id = trade_res["trade_id"]
    print("Open positions count:", len(order_mgr.get_open_positions()))
    
    # Test squaring off
    sq_res = order_mgr.square_off_trade(trade_id, exit_price=plan["target_1"])
    print(f"Square off status: {sq_res}")
    assert sq_res is True, "Trade square off should succeed!"

    print("\n=== Step 5: Generating Plotly Chart Figure ===")
    fig = ChartPlotter.create_trade_chart(
        df=mtf_data["5m"],
        trade_plan=plan,
        timeframe="5m"
    )
    print("Chart Figure successfully created with trace count:", len(fig.data))

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
