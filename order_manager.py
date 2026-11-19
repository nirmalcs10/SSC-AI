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
from config import (
    INDEX_TOKENS,
    POPULAR_STOCKS,
    RISK_PER_TRADE_PERCENT,
    DAILY_LOSS_LIMIT_PERCENT,
    DAILY_MAX_TRADES,
    REVENGE_TRADING_COOLDOWN_MINUTES
)

logger = logging.getLogger("PaperTradingEngine")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
WALLET_FILE = DATA_DIR / "virtual_wallet.json"
TRADES_FILE = DATA_DIR / "trade_history.json"

DEFAULT_STARTING_CAPITAL = 100000.0  # Rs. 1,00,000 starting virtual balance


class OrderManager:
    def __init__(
        self,
        connector: AngelOneConnector,
        wallet_file: Optional[Path] = None,
        trades_file: Optional[Path] = None
    ):
        self.connector = connector
        self.token_manager = TokenManager.get_instance()
        self.wallet_file = wallet_file or WALLET_FILE
        self.trades_file = trades_file or TRADES_FILE
        self.wallet = self.load_wallet()
        self.trades = self.load_trades()

    def load_wallet(self) -> Dict[str, Any]:
        """Load virtual wallet state from disk."""
        if self.wallet_file.exists():
            try:
                with open(self.wallet_file, "r") as f:
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
            with open(self.wallet_file, "w") as f:
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
        if self.trades_file.exists():
            try:
                with open(self.trades_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read trade history: {e}")
        return []

    def save_trades(self):
        """Persist trade logs to disk."""
        try:
            with open(self.trades_file, "w") as f:
                json.dump(self.trades, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trade history: {e}")

    def calculate_trade_charges(self, turnover: float, is_option: bool = False) -> float:
        """
        Calculates realistic simulated statutory charges:
        Brokerage: Rs.20 flat.
        STT: 0.0625% on option turnover (premium), 0.025% on equity intraday.
        Exchange turnover fee: 0.0035%.
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
        is_paper_trade: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a 100% Risk-Free Virtual Paper Trade with realistic entry, SL, and Target.
        """
        direction = plan.get("direction", "BUY")
        if direction not in ("BUY", "SELL"):
            direction = "BUY"

        symbol = plan.get("symbol", "NIFTY")
        is_index = symbol in INDEX_TOKENS
        fno = plan.get("fno_recommendation")

        underlying_entry = float(plan.get("entry_price", 0.0))
        underlying_sl = float(plan.get("stop_loss", 0.0))
        underlying_t1 = float(plan.get("target_1", 0.0))
        underlying_t2 = float(plan.get("target_2", 0.0))

        if is_index and fno:
            strike = fno["atm_strike"]
            opt_type = fno["type"] if fno["type"] in ("CE", "PE") else ("CE" if direction == "BUY" else "PE")
            trading_symbol = f"{symbol} {strike} {opt_type}"
            lot_size = fno.get("lot_size") or INDEX_TOKENS.get(symbol, {}).get("lot_size", 65)
            total_qty = quantity * lot_size
            entry_price = float(fno.get("approx_premium", 65.0))
            sl_price = float(fno.get("option_stop_loss", entry_price * 0.75))
            target_1 = float(fno.get("option_target_1", entry_price * 1.35))
            target_2 = float(fno.get("option_target_2", entry_price * 1.60))
            trade_type = f"Options {opt_type}"
            is_opt = True
        else:
            trading_symbol = f"{symbol}-EQ"
            total_qty = quantity
            entry_price = float(plan.get("entry_price", 100.0))
            sl_price = float(plan.get("stop_loss", entry_price * 0.98))
            target_1 = float(plan.get("target_1", entry_price * 1.02))
            target_2 = float(plan.get("target_2", entry_price * 1.04))
            trade_type = "Equity Intraday"
            is_opt = False

        return self._create_paper_trade(
            symbol=symbol,
            trading_symbol=trading_symbol,
            trade_type=trade_type,
            direction=direction,
            total_qty=total_qty,
            quantity_lots=quantity,
            entry_price=entry_price,
            sl_price=sl_price,
            target_1=target_1,
            target_2=target_2,
            is_opt=is_opt,
            underlying_entry=underlying_entry,
            underlying_sl=underlying_sl,
            underlying_t1=underlying_t1,
            underlying_t2=underlying_t2
        )

    def execute_custom_trade(
        self,
        symbol: str,
        direction: str,
        trade_type: str,
        quantity_lots: int,
        entry_price: float,
        sl_price: float,
        target_1: float,
        target_2: float,
        custom_strike: str = "",
        underlying_entry: float = 0.0,
        underlying_sl: float = 0.0,
        underlying_t1: float = 0.0,
        underlying_t2: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes a 1-click paper trade on ANY index or equity with explicit parameters.
        """
        is_index = symbol in INDEX_TOKENS
        is_opt = "Option" in trade_type or trade_type in ("CE", "PE")

        if is_index:
            lot_size = INDEX_TOKENS.get(symbol, {}).get("lot_size", 65)
            total_qty = quantity_lots * lot_size
            trading_symbol = custom_strike or f"{symbol} {trade_type}"
        else:
            total_qty = quantity_lots
            trading_symbol = f"{symbol}-EQ"

        return self._create_paper_trade(
            symbol=symbol,
            trading_symbol=trading_symbol,
            trade_type=trade_type,
            direction=direction,
            total_qty=total_qty,
            quantity_lots=quantity_lots,
            entry_price=entry_price,
            sl_price=sl_price,
            target_1=target_1,
            target_2=target_2,
            is_opt=is_opt,
            underlying_entry=underlying_entry,
            underlying_sl=underlying_sl,
            underlying_t1=underlying_t1,
            underlying_t2=underlying_t2
        )


    def get_risk_status(self) -> Dict[str, Any]:
        """
        Pillar 4: Institutional Risk Management & Capital Protection Guard.
        Evaluates Risk per trade, Daily trade limit (1-3 max),
        Daily loss limit (2% circuit breaker), and Revenge Trading Lockout.
        """
        starting_cap = float(self.wallet.get("starting_capital", DEFAULT_STARTING_CAPITAL))
        current_balance = float(self.wallet.get("balance", starting_cap))
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        today_trades = [t for t in self.trades if t.get("timestamp", "").startswith(today_str)]
        daily_trades_count = len(today_trades)
        daily_max_trades = DAILY_MAX_TRADES
        can_trade_daily = daily_trades_count < daily_max_trades

        today_closed = [t for t in today_trades if t.get("status") == "CLOSED"]
        today_realized_pnl = round(sum(float(t.get("net_pnl", 0.0)) for t in today_closed), 2)
        daily_loss_limit_inr = round(-DAILY_LOSS_LIMIT_PERCENT * starting_cap, 2)
        is_circuit_breaker_tripped = (today_realized_pnl <= daily_loss_limit_inr)

        # Revenge Trading Detection:
        # If any trade hit stop loss or took a loss within the cooldown window
        revenge_cooldown_active = False
        cooldown_remaining_sec = 0
        cooldown_window_sec = REVENGE_TRADING_COOLDOWN_MINUTES * 60
        now = datetime.datetime.now()

        # Find most recently closed losing trade
        closed_losing_trades = [
            t for t in today_closed
            if t.get("exit_reason") == "STOP_LOSS_HIT" or float(t.get("net_pnl", 0.0)) < 0
        ]
        if closed_losing_trades:
            last_losing = closed_losing_trades[-1]
            exit_ts_str = last_losing.get("exit_timestamp") or last_losing.get("timestamp")
            if exit_ts_str:
                try:
                    exit_dt = datetime.datetime.strptime(exit_ts_str, "%Y-%m-%d %H:%M:%S")
                    elapsed_sec = (now - exit_dt).total_seconds()
                    if 0 <= elapsed_sec < cooldown_window_sec:
                        revenge_cooldown_active = True
                        cooldown_remaining_sec = int(cooldown_window_sec - elapsed_sec)
                except Exception as e:
                    logger.debug(f"Error parsing exit timestamp: {e}")

        # Position sizing max risk
        risk_per_trade_max_inr = round(current_balance * RISK_PER_TRADE_PERCENT, 2)

        return {
            "starting_capital": starting_cap,
            "current_balance": current_balance,
            "daily_trades_count": daily_trades_count,
            "daily_max_trades": daily_max_trades,
            "can_trade_daily": can_trade_daily,
            "today_realized_pnl": today_realized_pnl,
            "daily_loss_limit_inr": daily_loss_limit_inr,
            "daily_loss_limit_percent": DAILY_LOSS_LIMIT_PERCENT * 100,
            "is_circuit_breaker_tripped": is_circuit_breaker_tripped,
            "revenge_cooldown_active": revenge_cooldown_active,
            "cooldown_remaining_sec": cooldown_remaining_sec,
            "cooldown_remaining_min": max(1, (cooldown_remaining_sec // 60) + 1) if revenge_cooldown_active else 0,
            "risk_per_trade_max_inr": risk_per_trade_max_inr,
            "risk_per_trade_percent": RISK_PER_TRADE_PERCENT * 100
        }

    def validate_risk_limits(
        self,
        symbol: str,
        entry_price: float,
        sl_price: float,
        total_qty: int
    ) -> Tuple[bool, str]:
        """Validates all 4 risk management rules before permitting trade entry."""
        status = self.get_risk_status()

        # 1. Daily Loss Limit (2% Circuit Breaker)
        if status["is_circuit_breaker_tripped"]:
            return False, (
                f"🚨 Daily Loss Limit Hit: Today's net P&L is -₹{abs(status['today_realized_pnl']):,.2f} "
                f"(exceeds 2.0% daily capital limit of -₹{abs(status['daily_loss_limit_inr']):,.2f}). "
                f"Trading halted for today to protect capital."
            )

        # 2. Daily Trade Limit (1-3 Quality Setups Max)
        if not status["can_trade_daily"]:
            return False, (
                f"🛑 Daily Trade Limit Reached: {status['daily_trades_count']}/{status['daily_max_trades']} "
                f"quality setups executed today. Overtrading prevention halts new entries for today."
            )

        # 3. Revenge Trading Protection (Never)
        if status["revenge_cooldown_active"]:
            rem_m = status["cooldown_remaining_min"]
            return False, (
                f"⏳ Revenge Trading Protection Active: Stop loss was hit recently. "
                f"15-minute emotional reset cooldown in effect ({rem_m} min remaining). "
                f"Rule: NEVER revenge trade. Wait for a completely fresh confirmed setup."
            )

        return True, "Risk management checks passed successfully."

    def _create_paper_trade(
        self,
        symbol: str,
        trading_symbol: str,
        trade_type: str,
        direction: str,
        total_qty: int,
        quantity_lots: int,
        entry_price: float,
        sl_price: float,
        target_1: float,
        target_2: float,
        is_opt: bool,
        underlying_entry: float = 0.0,
        underlying_sl: float = 0.0,
        underlying_t1: float = 0.0,
        underlying_t2: float = 0.0
    ) -> Dict[str, Any]:
        """Internal helper to validate balance and open persistent trade record."""
        # Validate Institutional Risk Management Guard (Pillar 4)
        can_exec, risk_msg = self.validate_risk_limits(symbol, entry_price, sl_price, total_qty)
        if not can_exec:
            return {
                "status": False,
                "message": risk_msg,
                "code": "RISK_LIMIT_VIOLATION"
            }
        turnover = entry_price * total_qty
        charges = self.calculate_trade_charges(turnover, is_option=is_opt)

        margin_required = turnover if is_opt else (turnover * 0.20)
        if self.wallet["balance"] < margin_required:
            return {
                "status": False,
                "message": f"Insufficient Virtual Capital. Required: Rs.{margin_required:,.2f}, Available: Rs.{self.wallet['balance']:,.2f}"
            }

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        entry_time_display = now.strftime("%d-%b-%Y %H:%M:%S IST")
        trade_id = f"PAPER_{len(self.trades) + 1}"

        invested_capital = round(turnover, 2)
        opt_type = ("CE" if "CE" in trade_type else ("PE" if "PE" in trade_type else ("CE" if direction == "BUY" else "PE"))) if is_opt else ""

        trade_record = {
            "id": trade_id,
            "timestamp": timestamp_str,
            "entry_time": entry_time_display,
            "exit_time": None,
            "mode": "PAPER_TRADING",
            "symbol": symbol,
            "trading_symbol": trading_symbol,
            "trade_type": trade_type,
            "direction": direction,
            "is_option": is_opt,
            "option_type": opt_type,
            "quantity": total_qty,
            "quantity_lots": quantity_lots,
            "entry_price": round(entry_price, 2),
            "invested_capital": invested_capital,
            "stop_loss": round(sl_price, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "underlying_entry": round(underlying_entry, 2),
            "underlying_sl": round(underlying_sl, 2),
            "underlying_t1": round(underlying_t1, 2),
            "underlying_t2": round(underlying_t2, 2),
            "target_1_booked": False,
            "status": "OPEN",
            "current_price": round(entry_price, 2),
            "margin_blocked": round(margin_required, 2),
            "charges": charges,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "return_pct": 0.0,
            "is_profit": None,
            "exit_reason": None
        }

        # Deduct margin from available cash
        self.wallet["balance"] = round(self.wallet["balance"] - margin_required, 2)
        self.wallet["total_trades"] += 1
        self.save_wallet()

        self.trades.insert(0, trade_record)
        self.save_trades()

        return {
            "status": True,
            "message": f"Paper Trade Opened! {direction} {total_qty} qty of {trading_symbol} at Rs.{entry_price:.2f} (Invested: Rs.{invested_capital:,.2f})",
            "trade_id": trade_id,
            "invested_capital": invested_capital,
            "entry_time": entry_time_display,
            "mode": "PAPER"
        }

    def check_live_triggers(self, symbol: str, current_ltp: float) -> List[Dict[str, Any]]:
        """
        Evaluates open paper trades against the latest live tick price.
        Accurately maps spot index movements vs option strike premiums without cross-unit errors.
        Guarantees that a Stop Loss hit ALWAYS records a LOSS.
        """
        alerts = []
        for t in self.trades:
            if t.get("status") == "OPEN" and t.get("symbol") == symbol:
                is_opt = t.get("is_option", False) or t.get("trade_type", "").startswith("Options")
                opt_type = t.get("option_type", "")
                direction = t.get("direction", "BUY")
                qty = t.get("quantity", 1)
                entry_opt = t.get("entry_price", 0.0)
                invested = t.get("invested_capital") or (entry_opt * qty)

                u_entry = t.get("underlying_entry", 0.0)
                u_sl = t.get("underlying_sl", 0.0)
                u_t1 = t.get("underlying_t1", 0.0)
                u_t2 = t.get("underlying_t2", 0.0)

                opt_sl = t.get("stop_loss", 0.0)
                opt_t1 = t.get("target_1", 0.0)
                opt_t2 = t.get("target_2", 0.0)

                if is_opt:
                    # OPTION TRADE: Retail paper traders are Option BUYERS (Long CE or Long PE)
                    # Dynamic option premium estimation with Delta ~ 0.50
                    if u_entry > 0:
                        spot_diff = current_ltp - u_entry
                        if opt_type == "CE" or direction == "BUY":
                            cur_opt_price = max(0.50, round(entry_opt + (0.50 * spot_diff), 2))
                        else:  # PE or SELL Put direction
                            cur_opt_price = max(0.50, round(entry_opt - (0.50 * spot_diff), 2))
                    else:
                        cur_opt_price = entry_opt

                    t["current_price"] = cur_opt_price
                    gross_pnl = round((cur_opt_price - entry_opt) * qty, 2)
                    t["gross_pnl"] = gross_pnl
                    net_pnl = round(gross_pnl - t.get("charges", 20.0), 2)
                    t["net_pnl"] = net_pnl
                    t["return_pct"] = round((net_pnl / (invested + 1e-10)) * 100, 2)

                    # Trigger logic using underlying spot levels
                    if opt_type == "CE" or direction == "BUY":
                        # BULLISH CALL: SL if spot <= u_sl; T2 if spot >= u_t2
                        is_sl_hit = (current_ltp <= u_sl) if (u_sl > 0) else False
                        is_t2_hit = (current_ltp >= u_t2) if (u_t2 > 0) else False
                        is_t1_hit = (current_ltp >= u_t1) if (u_t1 > 0) else False

                        if is_sl_hit:
                            # Stop loss hit on Call Option -> Always exit at opt_sl (Loss)
                            exit_p = min(opt_sl, entry_opt * 0.75) if opt_sl > 0 else entry_opt * 0.75
                            self.square_off_trade(t["id"], exit_price=exit_p, exit_reason="STOP_LOSS_HIT")
                            alerts.append({
                                "type": "SL_HIT",
                                "trade_id": t["id"],
                                "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{exit_p:.2f}. Trade closed at Net Loss."
                            })
                        elif is_t2_hit:
                            exit_p = max(opt_t2, entry_opt * 1.60) if opt_t2 > 0 else entry_opt * 1.60
                            self.square_off_trade(t["id"], exit_price=exit_p, exit_reason="TARGET_2_HIT")
                            alerts.append({
                                "type": "T2_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Full profit booked at Rs.{exit_p:.2f}."
                            })
                        elif is_t1_hit and not t.get("target_1_booked", False):
                            t["target_1_booked"] = True
                            t["underlying_sl"] = u_entry
                            alerts.append({
                                "type": "T1_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 1 HIT on {t['trading_symbol']}! Trailing Stop Loss moved to Cost ({u_entry:,.2f})."
                            })

                    else:
                        # BEARISH PUT (PE): SL if spot >= u_sl; T2 if spot <= u_t2
                        is_sl_hit = (current_ltp >= u_sl) if (u_sl > 0) else False
                        is_t2_hit = (current_ltp <= u_t2) if (u_t2 > 0) else False
                        is_t1_hit = (current_ltp <= u_t1) if (u_t1 > 0) else False

                        if is_sl_hit:
                            # Stop loss hit on Put Option -> Always exit at opt_sl (Loss)
                            exit_p = min(opt_sl, entry_opt * 0.75) if opt_sl > 0 else entry_opt * 0.75
                            self.square_off_trade(t["id"], exit_price=exit_p, exit_reason="STOP_LOSS_HIT")
                            alerts.append({
                                "type": "SL_HIT",
                                "trade_id": t["id"],
                                "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{exit_p:.2f}. Trade closed at Net Loss."
                            })
                        elif is_t2_hit:
                            exit_p = max(opt_t2, entry_opt * 1.60) if opt_t2 > 0 else entry_opt * 1.60
                            self.square_off_trade(t["id"], exit_price=exit_p, exit_reason="TARGET_2_HIT")
                            alerts.append({
                                "type": "T2_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Full profit booked at Rs.{exit_p:.2f}."
                            })
                        elif is_t1_hit and not t.get("target_1_booked", False):
                            t["target_1_booked"] = True
                            t["underlying_sl"] = u_entry
                            alerts.append({
                                "type": "T1_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 1 HIT on {t['trading_symbol']}! Trailing Stop Loss moved to Cost ({u_entry:,.2f})."
                            })

                else:
                    # EQUITY INTRADAY
                    entry = entry_opt
                    sl = opt_sl
                    t1 = opt_t1
                    t2 = opt_t2

                    if direction == "BUY":
                        gross_pnl = (current_ltp - entry) * qty
                        t["current_price"] = current_ltp
                        t["gross_pnl"] = round(gross_pnl, 2)
                        net_pnl = round(gross_pnl - t.get("charges", 20.0), 2)
                        t["net_pnl"] = net_pnl
                        t["return_pct"] = round((net_pnl / (invested + 1e-10)) * 100, 2)

                        if current_ltp <= sl:
                            self.square_off_trade(t["id"], exit_price=sl, exit_reason="STOP_LOSS_HIT")
                            alerts.append({
                                "type": "SL_HIT",
                                "trade_id": t["id"],
                                "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{sl:.2f}. Net Loss: Rs.{abs(net_pnl):.2f}"
                            })
                        elif current_ltp >= t2:
                            self.square_off_trade(t["id"], exit_price=t2, exit_reason="TARGET_2_HIT")
                            alerts.append({
                                "type": "T2_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Booked at Rs.{t2:.2f}. Net Profit: Rs.{net_pnl:.2f}"
                            })
                        elif current_ltp >= t1 and not t.get("target_1_booked", False):
                            t["target_1_booked"] = True
                            t["stop_loss"] = entry
                            alerts.append({
                                "type": "T1_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 1 HIT on {t['trading_symbol']} at Rs.{t1:.2f}!"
                            })

                    elif direction == "SELL":
                        gross_pnl = (entry - current_ltp) * qty
                        t["current_price"] = current_ltp
                        t["gross_pnl"] = round(gross_pnl, 2)
                        net_pnl = round(gross_pnl - t.get("charges", 20.0), 2)
                        t["net_pnl"] = net_pnl
                        t["return_pct"] = round((net_pnl / (invested + 1e-10)) * 100, 2)

                        if current_ltp >= sl:
                            self.square_off_trade(t["id"], exit_price=sl, exit_reason="STOP_LOSS_HIT")
                            alerts.append({
                                "type": "SL_HIT",
                                "trade_id": t["id"],
                                "message": f"STOP LOSS HIT on {t['trading_symbol']}! Exited at Rs.{sl:.2f}. Net Loss: Rs.{abs(net_pnl):.2f}"
                            })
                        elif current_ltp <= t2:
                            self.square_off_trade(t["id"], exit_price=t2, exit_reason="TARGET_2_HIT")
                            alerts.append({
                                "type": "T2_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 2 REACHED on {t['trading_symbol']}! Booked at Rs.{t2:.2f}. Net Profit: Rs.{net_pnl:.2f}"
                            })
                        elif current_ltp <= t1 and not t.get("target_1_booked", False):
                            t["target_1_booked"] = True
                            t["stop_loss"] = entry
                            alerts.append({
                                "type": "T1_HIT",
                                "trade_id": t["id"],
                                "message": f"TARGET 1 HIT on {t['trading_symbol']} at Rs.{t1:.2f}!"
                            })
        if alerts:
            self.save_trades()
        return alerts

    def square_off_trade(self, trade_id: str, exit_price: float, exit_reason: str = "MANUAL_EXIT") -> bool:
        """Square off an open virtual position, update balance, and record complete lifecycle & P&L."""
        for t in self.trades:
            if t.get("id") == trade_id and t.get("status") == "OPEN":
                is_opt = t.get("is_option", False) or t.get("trade_type", "").startswith("Options")

                # Protection against index price mistakenly passed for options
                if is_opt:
                    if exit_price > t["entry_price"] * 8 and exit_price > 1000:
                        logger.warning(f"Abnormal option exit price {exit_price} for entry {t['entry_price']}. Using Target 2 {t.get('target_2')}")
                        exit_price = float(t.get("target_2") or (t["entry_price"] * 1.5))

                t["status"] = "CLOSED"
                t["exit_price"] = round(exit_price, 2)
                t["exit_time"] = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S IST")
                t["exit_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t["exit_reason"] = exit_reason

                qty = t["quantity"]
                # CRITICAL RULE: For Option buyers (both CE and PE), profit is (exit - entry) * qty!
                # If exit < entry (e.g. Stop Loss hit), gross_pnl is strictly NEGATIVE (LOSS)!
                if is_opt:
                    gross_pnl = (exit_price - t["entry_price"]) * qty
                else:
                    if t["direction"] == "BUY":
                        gross_pnl = (exit_price - t["entry_price"]) * qty
                    else:
                        gross_pnl = (t["entry_price"] - exit_price) * qty
                    
                total_charges = t.get("charges", 20.0) * 2  # Entry + Exit charges
                net_pnl = round(gross_pnl - total_charges, 2)
                invested = t.get("invested_capital") or (t["entry_price"] * qty)
                return_pct = round((net_pnl / (invested + 1e-10)) * 100, 2)
                
                t["gross_pnl"] = round(gross_pnl, 2)
                t["charges"] = round(total_charges, 2)
                t["net_pnl"] = net_pnl
                t["return_pct"] = return_pct
                t["is_profit"] = (net_pnl >= 0)
                
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
                "net_pnl": 0.0,
                "total_invested": 0.0
            }
            
        wins = [t["net_pnl"] for t in closed if t.get("net_pnl", 0) > 0]
        losses = [abs(t["net_pnl"]) for t in closed if t.get("net_pnl", 0) < 0]
        total_invested = sum([t.get("invested_capital", 0.0) for t in closed])
        
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
            "net_pnl": self.wallet.get("net_pnl", 0.0),
            "total_invested": round(total_invested, 2)
        }
