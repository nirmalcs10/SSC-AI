"""
Multi-Timeframe Confluence Strategy Engine.
Analyzes 1m, 5m, 15m, 1h (and 1D) to output exact Direction,
Take Trade Price (Entry), Stop Loss, and Targets (T1, T2, T3) with F&O Strike Recommendations.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from config import (
    INDEX_TOKENS,
    ATR_MULTIPLIER_SL,
    RR_RATIO_TARGET_1,
    RR_RATIO_TARGET_2,
    CONFLUENCE_BUY_THRESHOLD,
    CONFLUENCE_SELL_THRESHOLD
)
from indicator_engine import IndicatorEngine
from level_detector import LevelDetector


class ConfluenceStrategy:
    def __init__(self, symbol: str = "NIFTY", mode: str = "INTRADAY"):
        self.symbol = symbol.upper().strip()
        self.mode = mode.upper().strip()
        self.is_index = self.symbol in INDEX_TOKENS

    def analyze(self, mtf_data: Dict[str, pd.DataFrame], live_quote: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Full Top-Down Analysis across multiple timeframes.
        Returns trade recommendation with Entry, Stop Loss, Targets, and Rationale.
        """
        # Ensure indicators and levels are computed
        analyzed_tf = {}
        for tf, df in mtf_data.items():
            if df is not None and not df.empty:
                analyzed_tf[tf] = IndicatorEngine.apply_all(df)

        if not analyzed_tf:
            return {
                "signal": "NO DATA",
                "symbol": self.symbol,
                "message": "No candle data available for analysis"
            }

        # Select Primary & Secondary timeframes based on mode
        if self.mode == "SWING":
            macro_tf = "1D" if "1D" in analyzed_tf else "1h"
            struct_tf = "1h" if "1h" in analyzed_tf else "15m"
            exec_tf = "15m" if "15m" in analyzed_tf else "5m"
        else:  # INTRADAY / FNO_INDICES
            macro_tf = "1h" if "1h" in analyzed_tf else "15m"
            struct_tf = "15m" if "15m" in analyzed_tf else "5m"
            exec_tf = "5m" if "5m" in analyzed_tf else "1m"

        df_macro = analyzed_tf.get(macro_tf)
        df_struct = analyzed_tf.get(struct_tf)
        df_exec = analyzed_tf.get(exec_tf)
        df_1m = analyzed_tf.get("1m")

        # Current Price from lowest available TF
        ref_df = df_1m if (df_1m is not None and not df_1m.empty) else df_exec
        current_candle = ref_df.iloc[-1]
        current_price = float(current_candle["close"])

        # Detect S/R, CPR, and Key levels
        daily_ref = analyzed_tf.get("1D")
        if daily_ref is None or daily_ref.empty:
            daily_ref = df_macro

        struct_ref = df_struct if (df_struct is not None and not df_struct.empty) else df_macro
        exec_ref = df_exec if (df_exec is not None and not df_exec.empty) else df_struct

        cpr_data = LevelDetector.calculate_cpr_and_pivots(daily_ref)
        pdh_pdl = LevelDetector.get_pdh_pdl_open(struct_ref)
        sr_zones = LevelDetector.detect_support_resistance_zones(struct_ref)
        fvgs = LevelDetector.detect_fair_value_gaps(exec_ref)
        obs = LevelDetector.detect_order_blocks(exec_ref)

        # Multi-Timeframe Scoring System (-100 to +100) & Structured Rationale
        score = 0
        reasons = []
        detailed_rationale = {
            "macro": [],
            "structure": [],
            "execution": [],
            "order_flow": [],
            "levels": []
        }

        # 1. Macro Timeframe Analysis (35 Points)
        if df_macro is not None and len(df_macro) >= 20:
            macro_close = float(df_macro["close"].iloc[-1])
            macro_ema50 = float(df_macro["ema_50"].iloc[-1])
            macro_ema200 = float(df_macro["ema_200"].iloc[-1])
            macro_st_dir = int(df_macro["supertrend_dir"].iloc[-1])

            if macro_close > macro_ema200 and macro_close > macro_ema50:
                score += 20
                reasons.append(f"{macro_tf.upper()}: Strong Bullish Trend (Trading above 50 & 200 EMA)")
                detailed_rationale["macro"].append({
                    "factor": f"{macro_tf.upper()} 50 & 200 EMA",
                    "status": "BULLISH",
                    "detail": f"Price ₹{macro_close:,.2f} is above 50 EMA (₹{macro_ema50:,.2f}) & 200 EMA (₹{macro_ema200:,.2f})",
                    "points": 20
                })
            elif macro_close < macro_ema200 and macro_close < macro_ema50:
                score -= 20
                reasons.append(f"{macro_tf.upper()}: Strong Bearish Trend (Trading below 50 & 200 EMA)")
                detailed_rationale["macro"].append({
                    "factor": f"{macro_tf.upper()} 50 & 200 EMA",
                    "status": "BEARISH",
                    "detail": f"Price ₹{macro_close:,.2f} is below 50 EMA (₹{macro_ema50:,.2f}) & 200 EMA (₹{macro_ema200:,.2f})",
                    "points": -20
                })
            else:
                detailed_rationale["macro"].append({
                    "factor": f"{macro_tf.upper()} 50 & 200 EMA",
                    "status": "NEUTRAL",
                    "detail": f"Price ₹{macro_close:,.2f} is sandwiched between 50 EMA (₹{macro_ema50:,.2f}) & 200 EMA (₹{macro_ema200:,.2f})",
                    "points": 0
                })

            if macro_st_dir == 1:
                score += 15
                reasons.append(f"{macro_tf.upper()}: Supertrend is Bullish (Green)")
                detailed_rationale["macro"].append({
                    "factor": f"{macro_tf.upper()} Supertrend",
                    "status": "BULLISH",
                    "detail": "Supertrend is Green providing dynamic ascending support",
                    "points": 15
                })
            else:
                score -= 15
                reasons.append(f"{macro_tf.upper()}: Supertrend is Bearish (Red)")
                detailed_rationale["macro"].append({
                    "factor": f"{macro_tf.upper()} Supertrend",
                    "status": "BEARISH",
                    "detail": "Supertrend is Red acting as dynamic overhead resistance",
                    "points": -15
                })

        # 2. Structural Timeframe Analysis (30 Points)
        struct_rsi = 50.0
        if df_struct is not None and len(df_struct) >= 15:
            struct_close = float(df_struct["close"].iloc[-1])
            struct_ema9 = float(df_struct["ema_9"].iloc[-1])
            struct_ema21 = float(df_struct["ema_21"].iloc[-1])
            struct_rsi = float(df_struct["rsi"].iloc[-1])

            if struct_ema9 > struct_ema21:
                score += 15
                reasons.append(f"{struct_tf.upper()}: 9 EMA is above 21 EMA (Upward Momentum)")
                detailed_rationale["structure"].append({
                    "factor": f"{struct_tf.upper()} 9/21 EMA Alignment",
                    "status": "BULLISH",
                    "detail": f"Fast 9 EMA (₹{struct_ema9:,.2f}) is above Slow 21 EMA (₹{struct_ema21:,.2f})",
                    "points": 15
                })
            else:
                score -= 15
                reasons.append(f"{struct_tf.upper()}: 9 EMA is below 21 EMA (Downward Momentum)")
                detailed_rationale["structure"].append({
                    "factor": f"{struct_tf.upper()} 9/21 EMA Alignment",
                    "status": "BEARISH",
                    "detail": f"Fast 9 EMA (₹{struct_ema9:,.2f}) is below Slow 21 EMA (₹{struct_ema21:,.2f})",
                    "points": -15
                })

            if struct_rsi > 55:
                score += 15
                reasons.append(f"{struct_tf.upper()}: RSI at {struct_rsi:.1f} shows solid Bullish momentum")
                detailed_rationale["structure"].append({
                    "factor": f"{struct_tf.upper()} RSI Momentum",
                    "status": "BULLISH",
                    "detail": f"RSI is at {struct_rsi:.1f} (>55) indicating solid bullish buying velocity",
                    "points": 15
                })
            elif struct_rsi < 45:
                score -= 15
                reasons.append(f"{struct_tf.upper()}: RSI at {struct_rsi:.1f} shows solid Bearish pressure")
                detailed_rationale["structure"].append({
                    "factor": f"{struct_tf.upper()} RSI Momentum",
                    "status": "BEARISH",
                    "detail": f"RSI is at {struct_rsi:.1f} (<45) indicating active selling pressure",
                    "points": -15
                })
            else:
                detailed_rationale["structure"].append({
                    "factor": f"{struct_tf.upper()} RSI Momentum",
                    "status": "NEUTRAL",
                    "detail": f"RSI is at {struct_rsi:.1f} (in neutral 45-55 chop range)",
                    "points": 0
                })

        # 3. Execution & Trigger Timeframe Analysis (35 Points)
        if df_exec is not None and len(df_exec) >= 10:
            exec_close = float(df_exec["close"].iloc[-1])
            exec_vwap = float(df_exec["vwap"].iloc[-1])
            exec_atr = float(df_exec["atr"].iloc[-1])

            if exec_close > exec_vwap:
                score += 20
                reasons.append(f"{exec_tf.upper()}: Price is holding above Intraday VWAP (Buyers in control)")
                detailed_rationale["execution"].append({
                    "factor": f"{exec_tf.upper()} Intraday VWAP",
                    "status": "BULLISH",
                    "detail": f"Price ₹{exec_close:,.2f} is holding above institutional VWAP ₹{exec_vwap:,.2f}",
                    "points": 20
                })
            else:
                score -= 20
                reasons.append(f"{exec_tf.upper()}: Price is below Intraday VWAP (Sellers in control)")
                detailed_rationale["execution"].append({
                    "factor": f"{exec_tf.upper()} Intraday VWAP",
                    "status": "BEARISH",
                    "detail": f"Price ₹{exec_close:,.2f} is below institutional VWAP ₹{exec_vwap:,.2f}",
                    "points": -20
                })

            # Check candle trigger (rejection wick or engulfing)
            last_c = df_exec.iloc[-1]
            c_open = float(last_c["open"])
            c_high = float(last_c["high"])
            c_low = float(last_c["low"])
            c_close = float(last_c["close"])
            body = abs(c_close - c_open)
            lower_wick = min(c_open, c_close) - c_low
            upper_wick = c_high - max(c_open, c_close)

            if lower_wick > body * 1.3:
                score += 15
                reasons.append(f"{exec_tf.upper()}: Strong Lower Rejection Wick (Demand buying support)")
                detailed_rationale["execution"].append({
                    "factor": "Candle Wick Action",
                    "status": "BULLISH",
                    "detail": "Long lower shadow demonstrates aggressive dip-buying absorption",
                    "points": 15
                })
            elif upper_wick > body * 1.3:
                score -= 15
                reasons.append(f"{exec_tf.upper()}: Strong Upper Rejection Wick (Supply rejection at resistance)")
                detailed_rationale["execution"].append({
                    "factor": "Candle Wick Action",
                    "status": "BEARISH",
                    "detail": "Long upper shadow demonstrates supply rejection capping higher prices",
                    "points": -15
                })
            else:
                detailed_rationale["execution"].append({
                    "factor": "Candle Wick Action",
                    "status": "NEUTRAL",
                    "detail": "Standard candle body without extreme wick rejection",
                    "points": 0
                })

        # 4. Live Quote & Order Flow Confluence (10 Points)
        of_ratio = 50.0
        if live_quote and "order_flow_ratio" in live_quote:
            of_ratio = float(live_quote["order_flow_ratio"])
            if of_ratio >= 60.0:
                score += 10
                reasons.append(f"Live Order Flow: Strong Buyer Dominance ({of_ratio}% Bids vs Asks)")
                detailed_rationale["order_flow"].append({
                    "factor": "Live Order Flow Depth",
                    "status": "BULLISH",
                    "detail": f"Buyer dominance with {of_ratio:.1f}% bids vs {100 - of_ratio:.1f}% asks",
                    "points": 10
                })
            elif of_ratio <= 40.0:
                score -= 10
                reasons.append(f"Live Order Flow: Strong Seller Dominance ({100 - of_ratio:.1f}% Asks vs Bids)")
                detailed_rationale["order_flow"].append({
                    "factor": "Live Order Flow Depth",
                    "status": "BEARISH",
                    "detail": f"Seller dominance with {100 - of_ratio:.1f}% asks vs {of_ratio:.1f}% bids",
                    "points": -10
                })
            else:
                detailed_rationale["order_flow"].append({
                    "factor": "Live Order Flow Depth",
                    "status": "NEUTRAL",
                    "detail": f"Balanced exchange order flow with {of_ratio:.1f}% bids vs {100 - of_ratio:.1f}% asks",
                    "points": 0
                })

        # 5. Key Levels (CPR & S/R Zones)
        cpr_tc = float(cpr_data.get("tc", 0.0))
        cpr_bc = float(cpr_data.get("bc", 0.0))
        if current_price > cpr_tc and cpr_tc > 0:
            detailed_rationale["levels"].append({
                "factor": "Central Pivot Range (CPR)",
                "status": "BULLISH",
                "detail": f"Price (₹{current_price:,.2f}) is trading above Top Central Pivot (₹{cpr_tc:,.2f})",
                "points": 0
            })
        elif current_price < cpr_bc and cpr_bc > 0:
            detailed_rationale["levels"].append({
                "factor": "Central Pivot Range (CPR)",
                "status": "BEARISH",
                "detail": f"Price (₹{current_price:,.2f}) is trading below Bottom Central Pivot (₹{cpr_bc:,.2f})",
                "points": 0
            })
        else:
            detailed_rationale["levels"].append({
                "factor": "Central Pivot Range (CPR)",
                "status": "NEUTRAL",
                "detail": f"Price is trading inside CPR consolidation band (₹{cpr_bc:,.2f} - ₹{cpr_tc:,.2f})",
                "points": 0
            })

        closest_supp = sr_zones["supports"][0]["level"] if sr_zones["supports"] else None
        closest_res = sr_zones["resistances"][0]["level"] if sr_zones["resistances"] else None
        detailed_rationale["levels"].append({
            "factor": "Support / Resistance",
            "status": "NEUTRAL",
            "detail": f"Nearest Support: ₹{closest_supp or 'N/A'} | Nearest Resistance: ₹{closest_res or 'N/A'}",
            "points": 0
        })

        # Determine Signal Classification & Natural Language Explanation
        if score >= CONFLUENCE_BUY_THRESHOLD:
            signal = "STRONG BUY"
            direction = "BUY"
            decision_summary = (
                f"🟢 STRONG BUY DECISION (Score: {score}/100): "
                f"High-probability bullish trend confluence verified across macro and intraday timeframes. "
                f"Price is trading above 50/200 EMAs and Intraday VWAP, with 15m 9 EMA above 21 EMA (RSI: {struct_rsi:.1f}). "
                f"Buyers hold market dominance ({of_ratio:.1f}% bids). Look for long/CE entries on pullbacks with SL below support."
            )
        elif score >= 35:
            signal = "BUY"
            direction = "BUY"
            decision_summary = (
                f"🟢 BUY DECISION (Score: {score}/100): "
                f"Bullish momentum setup active. The primary trend and intraday moving averages are aligned upward. "
                f"Price is holding above VWAP with positive RSI ({struct_rsi:.1f}). Maintain strict SL below trigger low."
            )
        elif score <= CONFLUENCE_SELL_THRESHOLD:
            signal = "STRONG SELL"
            direction = "SELL"
            decision_summary = (
                f"🔴 STRONG SELL DECISION (Score: {score}/100): "
                f"High-probability bearish breakdown verified. Price has broken below key 50/200 EMAs and Intraday VWAP, "
                f"accompanied by downward 9/21 EMA cross and weak RSI ({struct_rsi:.1f}). Sellers dominate order flow. Look for short/PE entries."
            )
        elif score <= -35:
            signal = "SELL"
            direction = "SELL"
            decision_summary = (
                f"🔴 SELL DECISION (Score: {score}/100): "
                f"Bearish momentum setup active. Intraday price is trading below VWAP with downward moving average pressure. "
                f"Maintain strict SL above trigger high."
            )
        else:
            signal = "WAIT / NO TRADE"
            direction = "NEUTRAL"
            reasons.append("Conflicting timeframe signals or market consolidation. Wait for structural breakout.")
            decision_summary = (
                f"⏳ WAIT / NO TRADE DECISION (Score: {score}/100): "
                f"The algorithm detected conflicting timeframe signals or sideways equilibrium (Confluence score is between -35 and +35). "
                f"Higher timeframe trend is not cleanly supported by intraday order flow, or price is trapped in CPR chop. "
                f"Patience pays in trading: Wait for a decisive breakout above resistance or below support before committing capital."
            )

        # Calculate Entry, Stop Loss, and Targets
        atr_val = float(df_exec["atr"].iloc[-1]) if df_exec is not None else (current_price * 0.003)
        recent_low = float(df_exec["low"].iloc[-5:].min()) if df_exec is not None else current_price - atr_val
        recent_high = float(df_exec["high"].iloc[-5:].max()) if df_exec is not None else current_price + atr_val

        # Immediate Support & Resistance values
        closest_supp = sr_zones["supports"][0]["level"] if sr_zones["supports"] else None
        closest_res = sr_zones["resistances"][0]["level"] if sr_zones["resistances"] else None

        if direction == "BUY":
            entry_price = round(current_price, 2)
            # SL: below recent swing low or ATR buffer or nearest support
            sl_candidate_1 = recent_low - (0.3 * atr_val)
            sl_candidate_2 = entry_price - (ATR_MULTIPLIER_SL * atr_val)
            stop_loss = round(min(sl_candidate_1, sl_candidate_2), 2)
            
            risk = max(entry_price - stop_loss, atr_val * 0.8)
            target_1 = round(entry_price + (risk * RR_RATIO_TARGET_1), 2)
            target_2 = round(entry_price + (risk * RR_RATIO_TARGET_2), 2)
            
            # Target 3 is either next major resistance or 3.5x risk
            if closest_res and closest_res > target_2:
                target_3 = round(closest_res, 2)
            else:
                target_3 = round(entry_price + (risk * 3.5), 2)
                
            risk_points = round(risk, 2)
            reward_t1_points = round(target_1 - entry_price, 2)
            reward_t2_points = round(target_2 - entry_price, 2)
            rrr = f"1 : {RR_RATIO_TARGET_2:.1f}"

        elif direction == "SELL":
            entry_price = round(current_price, 2)
            # SL: above recent swing high or ATR buffer or nearest resistance
            sl_candidate_1 = recent_high + (0.3 * atr_val)
            sl_candidate_2 = entry_price + (ATR_MULTIPLIER_SL * atr_val)
            stop_loss = round(max(sl_candidate_1, sl_candidate_2), 2)
            
            risk = max(stop_loss - entry_price, atr_val * 0.8)
            target_1 = round(entry_price - (risk * RR_RATIO_TARGET_1), 2)
            target_2 = round(entry_price - (risk * RR_RATIO_TARGET_2), 2)
            
            if closest_supp and closest_supp < target_2:
                target_3 = round(closest_supp, 2)
            else:
                target_3 = round(entry_price - (risk * 3.5), 2)
                
            risk_points = round(risk, 2)
            reward_t1_points = round(entry_price - target_1, 2)
            reward_t2_points = round(entry_price - target_2, 2)
            rrr = f"1 : {RR_RATIO_TARGET_2:.1f}"

        else:  # NEUTRAL
            entry_price = round(current_price, 2)
            stop_loss = round(current_price - (atr_val * 1.5), 2)
            target_1 = round(current_price + (atr_val * 2.0), 2)
            target_2 = round(current_price + (atr_val * 3.5), 2)
            target_3 = round(current_price + (atr_val * 5.0), 2)
            risk_points = round(atr_val * 1.5, 2)
            reward_t1_points = round(atr_val * 2.0, 2)
            reward_t2_points = round(atr_val * 3.5, 2)
            rrr = "N/A (Wait)"

        # F&O Options Strike Recommendation (for Indices F&O)
        fno_rec = None
        if self.is_index:
            strike_step = INDEX_TOKENS[self.symbol]["strike_step"]
            atm_strike = int(round(current_price / strike_step) * strike_step)
            lot_size = INDEX_TOKENS[self.symbol]["lot_size"]

            delta = 0.55
            base_prem = round(max(35.0, risk_points * 2.2), 1) if risk_points > 0 else 100.0

            # CE (Call Option) calculations
            ce_strike = f"{atm_strike} CE"
            ce_prem = base_prem
            ce_sl = round(max(5.0, ce_prem - (risk_points * delta)), 1)
            ce_t1 = round(ce_prem + (reward_t1_points * delta), 1)
            ce_t2 = round(ce_prem + (reward_t2_points * delta), 1)

            # PE (Put Option) calculations
            pe_strike = f"{atm_strike} PE"
            pe_prem = base_prem
            pe_sl = round(max(5.0, pe_prem - (risk_points * delta)), 1)
            pe_t1 = round(pe_prem + (reward_t1_points * delta), 1)
            pe_t2 = round(pe_prem + (reward_t2_points * delta), 1)

            if direction == "BUY":
                opt_type = "CE"
                recommended_strike = ce_strike
                approx_prem = ce_prem
                opt_sl = ce_sl
                opt_t1 = ce_t1
                opt_t2 = ce_t2
            elif direction == "SELL":
                opt_type = "PE"
                recommended_strike = pe_strike
                approx_prem = pe_prem
                opt_sl = pe_sl
                opt_t1 = pe_t1
                opt_t2 = pe_t2
            else:
                opt_type = "CE / PE"
                recommended_strike = f"{atm_strike} CE/PE"
                approx_prem = 100.0
                opt_sl = 70.0
                opt_t1 = 140.0
                opt_t2 = 180.0

            fno_rec = {
                "strike": recommended_strike,
                "type": opt_type,
                "atm_strike": atm_strike,
                "approx_premium": approx_prem,
                "option_stop_loss": opt_sl,
                "option_target_1": opt_t1,
                "option_target_2": opt_t2,
                "lot_size": lot_size,
                "call_option": {
                    "strike": ce_strike,
                    "type": "CE",
                    "atm_strike": atm_strike,
                    "approx_premium": ce_prem,
                    "option_stop_loss": ce_sl,
                    "option_target_1": ce_t1,
                    "option_target_2": ce_t2,
                    "lot_size": lot_size,
                    "is_recommended": direction == "BUY"
                },
                "put_option": {
                    "strike": pe_strike,
                    "type": "PE",
                    "atm_strike": atm_strike,
                    "approx_premium": pe_prem,
                    "option_stop_loss": pe_sl,
                    "option_target_1": pe_t1,
                    "option_target_2": pe_t2,
                    "lot_size": lot_size,
                    "is_recommended": direction == "SELL"
                }
            }

        return {
            "symbol": self.symbol,
            "mode": self.mode,
            "signal": signal,
            "direction": direction,
            "confluence_score": score,
            "current_price": round(current_price, 2),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "target_3": target_3,
            "risk_points": risk_points,
            "reward_points": reward_t2_points,
            "risk_reward_ratio": rrr,
            "cpr": cpr_data,
            "pdh_pdl": pdh_pdl,
            "sr_zones": sr_zones,
            "fvgs": fvgs,
            "obs": obs,
            "fno_recommendation": fno_rec,
            "reasons": reasons,
            "detailed_rationale": detailed_rationale,
            "decision_summary": decision_summary,
            "analyzed_timeframes": list(analyzed_tf.keys())
        }
