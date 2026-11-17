"""
100% Risk-Free Virtual Paper Trading Engine.
Simulates realistic Indian market order execution with slippage,
brokerage (Rs.20/order), STT/GST charges, automated SL/Target exits, and wallet tracking.
ZERO real money is ever placed.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from angel_connector import AngelOneConnector
from token_manager import TokenManager
from config import INDEX_TOKENS, POPULAR_STOCKS

logger = logging.getLogger("PaperTradingEngine")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
WALLET_FILE = DATA_DIR / "virtual_wallet.json"
TRADES_FILE = DATA_DIR / "trade_history.json"

DEFAULT_STARTING_CAPITAL = 100000.0  # Rs. 1,00,000 starting virtual balance


class OrderManager:
    def __init__(self, connector: AngelOneConnector):
        self.connector = connector
        self.token_manager = TokenManager.get_instance()
        self.wallet = self.load_wallet()
        self.trades = self.load_trades()

    def load_wallet(self) -> Dict[str, Any]:
        """Load virtual wallet state from disk."""
        if WALLET_FILE.exists():
            try:
                with open(WALLET_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load wallet file: {e}")
        return {
            "starting_capital": DEFAULT_STARTING_CAPITAL,
            "balance": DEFAULT_STARTING_CAPITAL,
            "realized_pnl": 0.0,
            "total_charges": 0.0,
            "net_pnl": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }

    def save_wallet(self):
        """Save virtual wallet state to disk."""
        try:
            with open(WALLET_FILE, "w") as f:
                json.dump(self.wallet, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save wallet: {e}")

    def reset_wallet(self, starting_capital: float = DEFAULT_STARTING_CAPITAL):
        """Reset virtual wallet to starting capital and clear trade history."""
        self.wallet = {
            "starting_capital": starting_capital,
            "balance": starting_capital,
            "realized_pnl": 0.0,
            "total_charges": 0.0,
            "net_pnl": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }
        self.trades = []
        self.save_wallet()
        self.save_trades()

    def load_trades(self) -> List[Dict[str, Any]]:
        """Load persistent trade logs."""
        if TRADES_FILE.exists():
            try:
                with open(TRADES_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read trade history: {e}")
        return []

    def save_trades(self):
        """Save trade logs to disk."""
        try:
            with open(TRADES_FILE, "w") as f:
                json.dump(self.trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save trades: {e}")

    def calculate_trade_charges(self, turnover: float, is_option: bool = True) -> float:
        """
        Estimate realistic Indian trading charges (Brokerage + STT + GST + Exchange fees).
        Brokerage: Rs. 20 flat.
        STT: ~0.0625% on sell side (options) or 0.025% (intraday equity).
        GST: 18% on brokerage.
        """
        brokerage = 20.0
        gst = brokerage * 0.18
        stt = turnover * (0.000625 if is_option else 0.00025)
        exchange_turnover_fee = turnover * 0.000035
        sebi_charges = turnover * 0.000001
        return round(brokerage + gst + stt + exchange_turnover_fee + sebi_charges, 2)

    def execute_trade_from_plan(
        self,
        plan: Dict[str, Any],
        quantity: int = 1,
        is_paper_trade: bool = True  # Always True (Hardcoded for Safety)
    ) -> Dict[str, Any]:
        """
        Executes a 100% Risk-Free Virtual Paper Trade with realistic entry, SL, and Target.
        Real money is never touched.
        """
        direction = plan.get("direction")
        if direction not in ("BUY", "SELL"):
            return {"status": False, "message": "Cannot execute on NEUTRAL / WAIT signal."}

        symbol = plan.get("symbol", "NIFTY")
        is_index = symbol in INDEX_TOKENS
        fno = plan.get("fno_recommendation")
        
        # Determine Trading Symbol & Pricing
        if is_index and fno:
            strike = fno["atm_strike"]
            opt_type = fno["type"]
            trading_symbol = f"{symbol} {strike} {opt_type}"
            lot_size = fno.get("lot_size") or INDEX_TOKENS.get(symbol, {}).get("lot_size", 65)
            total_qty = quantity * lot_size
            entry_price = float(fno["approx_premium"])
            sl_price = float(fno["option_stop_loss"])
            target_1 = float(fno["option_target_1"])
            target_2 = float(fno["option_target_2"])
            trade_type = f"Options {opt_type}"
            is_opt = True
        else:
            trading_symbol = f"{symbol}-EQ"
            total_qty = quantity
            entry_price = float(plan["entry_price"])
            sl_price = float(plan["stop_loss"])
            target_1 = float(plan["target_1"])
            target_2 = float(plan["target_2"])
            trade_type = "Equity Intraday"
            is_opt = False

        turnover = entry_price * total_qty
        charges = self.calculate_trade_charges(turnover, is_option=is_opt)

        # Check virtual balance
        margin_required = turnover if is_opt else (turnover * 0.20)  # 5x intraday margin for equity
        if self.wallet["balance"] < margin_required:
            return {
                "status": False,
                "message": f"Insufficient Virtual Capital. Required: Rs.{margin_required:,.2f}, Available: Rs.{self.wallet['balance']:,.2f}"
            }

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade_id = f"PAPER_{len(self.trades) + 1}"

        trade_record = {
            "id": trade_id,
            "timestamp": timestamp,
            "mode": "PAPER_TRADING",
            "symbol": symbol,
            "trading_symbol": trading_symbol,
            "trade_type": trade_type,
            "direction": direction,
            "quantity": total_qty,
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "target_1": target_1,
            "target_2": target_2,
            "target_1_booked": False,
            "status": "OPEN",
            "current_price": entry_price,
            "margin_blocked": round(margin_required, 2),
            "charges": charges,
            "gross_pnl": 0.0,
            "net_pnl": 0.0
        }

        # Deduct margin from available balance
        self.wallet["balance"] = round(self.wallet["balance"] - margin_required, 2)
        self.wallet["total_trades"] += 1
        self.save_wallet()

        self.trades.insert(0, trade_record)
        self.save_trades()

        return {
            "status": True,
            "message": f"Paper Trade Opened! {direction} {total_qty} qty of {trading_symbol} at Rs.{entry_price:.2f} (SL: Rs.{sl_price:.2f}, Target: Rs.{target_2:.2f})",
            "trade_id": trade_id,
            "mode": "PAPER"
        }

    def check_live_triggers(self, symbol: str, current_ltp: float) -> List[Dict[str, Any]]:
        """
        Evaluates open paper trades against the latest live tick price.
        Automatically executes exits when Target or Stop Loss is reached!
        """
        alerts = []
        for t in self.trades:
            if t.get("status") == "OPEN" and t.get("symbol") == symbol:
                direction = t.get("direction")
                sl = t.get("stop_loss", 0.0)
                t1 = t.get("target_1", 0.0)
                t2 = t.get("target_2", 0.0)
                entry = t.get("entry_price", 0.0)
                qty = t.get("quantity", 1)

                # Update live price and unrealized P&L
                if direction == "BUY":
                    gross_pnl = (current_ltp - entry) * qty
                    t["current_price"] = current_ltp
                    t["gross_pnl"] = round(gross_pnl, 2)
                    t["net_pnl"] = round(gross_pnl - t.get("charges", 20.0), 2)
                    
                    # Stop Loss Trigger
                    if current_ltp <= sl:
                        self.square_off_trade(t["id"], exit_price=sl, exit_reason="STOP_LOSS_HIT")
                        alerts.append({
                            "type": "SL_HIT",
                            "trade_id": t["id"],
                            "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{sl}. Net P&L: Rs.{t['net_pnl']}"
                        })
                    # Target 2 (Full Profit) Trigger
                    elif current_ltp >= t2:
                        self.square_off_trade(t["id"], exit_price=t2, exit_reason="TARGET_2_HIT")
                        alerts.append({
                            "type": "T2_HIT",
                            "trade_id": t["id"],
                            "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Full profit booked at Rs.{t2}. Net P&L: Rs.{t['net_pnl']}"
                        })
                    # Target 1 (Partial Profit / Trailing SL) Trigger
                    elif current_ltp >= t1 and not t.get("target_1_booked", False):
                        t["target_1_booked"] = True
                        t["stop_loss"] = entry  # Move SL to Cost (Break-even)
                        alerts.append({
                            "type": "T1_HIT",
                            "trade_id": t["id"],
                            "message": f"TARGET 1 HIT on {t['trading_symbol']} at Rs.{t1}! Trailing SL moved to Cost (Rs.{entry}). Risk eliminated!"
                        })

                elif direction == "SELL":
                    gross_pnl = (entry - current_ltp) * qty
                    t["current_price"] = current_ltp
                    t["gross_pnl"] = round(gross_pnl, 2)
                    t["net_pnl"] = round(gross_pnl - t.get("charges", 20.0), 2)
                    
                    # Stop Loss Trigger
                    if current_ltp >= sl:
                        self.square_off_trade(t["id"], exit_price=sl, exit_reason="STOP_LOSS_HIT")
                        alerts.append({
                            "type": "SL_HIT",
                            "trade_id": t["id"],
                            "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{sl}. Net P&L: Rs.{t['net_pnl']}"
                        })
                    # Target 2 Trigger
                    elif current_ltp <= t2:
                        self.square_off_trade(t["id"], exit_price=t2, exit_reason="TARGET_2_HIT")
                        alerts.append({
                            "type": "T2_HIT",
                            "trade_id": t["id"],
                            "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Full profit booked at Rs.{t2}. Net P&L: Rs.{t['net_pnl']}"
                        })
                    # Target 1 Trigger
                    elif current_ltp <= t1 and not t.get("target_1_booked", False):
                        t["target_1_booked"] = True
                        t["stop_loss"] = entry
                        alerts.append({
                            "type": "T1_HIT",
                            "trade_id": t["id"],
                            "message": f"TARGET 1 HIT on {t['trading_symbol']} at Rs.{t1}! Trailing SL moved to Cost (Rs.{entry})."
                        })
        if alerts:
            self.save_trades()
        return alerts

    def square_off_trade(self, trade_id: str, exit_price: float, exit_reason: str = "MANUAL_EXIT") -> bool:
        """Square off an open virtual position, update balance, and record realized P&L."""
        for t in self.trades:
            if t.get("id") == trade_id and t.get("status") == "OPEN":
                t["status"] = "CLOSED"
                t["exit_price"] = round(exit_price, 2)
                t["exit_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t["exit_reason"] = exit_reason
                
                qty = t["quantity"]
                if t["direction"] == "BUY":
                    gross_pnl = (exit_price - t["entry_price"]) * qty
                else:
                    gross_pnl = (t["entry_price"] - exit_price) * qty
                    
                total_charges = t.get("charges", 20.0) * 2  # Entry + Exit charges
                net_pnl = round(gross_pnl - total_charges, 2)
                
                t["gross_pnl"] = round(gross_pnl, 2)
                t["charges"] = round(total_charges, 2)
                t["net_pnl"] = net_pnl
                
                # Restore margin + Net P&L to virtual wallet
                margin = t.get("margin_blocked", 0.0)
                self.wallet["balance"] = round(self.wallet["balance"] + margin + net_pnl, 2)
                self.wallet["realized_pnl"] = round(self.wallet["realized_pnl"] + net_pnl, 2)
                self.wallet["total_charges"] = round(self.wallet["total_charges"] + total_charges, 2)
                self.wallet["net_pnl"] = round(self.wallet["realized_pnl"], 2)
                
                if net_pnl > 0:
                    self.wallet["winning_trades"] += 1
                else:
                    self.wallet["losing_trades"] += 1
                    
                self.save_wallet()
                self.save_trades()
                return True
        return False

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return list of active virtual trades."""
        return [t for t in self.trades if t.get("status") == "OPEN"]

    def get_closed_trades(self) -> List[Dict[str, Any]]:
        """Return list of completed virtual trades."""
        return [t for t in self.trades if t.get("status") == "CLOSED"]

    def get_analytics(self) -> Dict[str, Any]:
        """Compute performance analytics: Win Rate, Profit Factor, Net P&L."""
        closed = self.get_closed_trades()
        total_closed = len(closed)
        if total_closed == 0:
            return {
                "total_closed": 0,
                "win_rate": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": 0.0,
                "net_pnl": 0.0
            }
            
        wins = [t["net_pnl"] for t in closed if t["net_pnl"] > 0]
        losses = [abs(t["net_pnl"]) for t in closed if t["net_pnl"] < 0]
        
        gross_profit = sum(wins)
        gross_loss = sum(losses)
        win_rate = round((len(wins) / total_closed) * 100, 1)
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        
        return {
            "total_closed": total_closed,
            "win_rate": win_rate,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": profit_factor,
            "net_pnl": self.wallet.get("net_pnl", 0.0)
        }
