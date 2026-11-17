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

        # Multi-Timeframe Scoring System (-100 to +100)
        score = 0
        reasons = []

        # 1. Macro Timeframe Analysis (35 Points)
        if df_macro is not None and len(df_macro) >= 20:
            macro_close = float(df_macro["close"].iloc[-1])
            macro_ema50 = float(df_macro["ema_50"].iloc[-1])
            macro_ema200 = float(df_macro["ema_200"].iloc[-1])
            macro_st_dir = int(df_macro["supertrend_dir"].iloc[-1])

            if macro_close > macro_ema200 and macro_close > macro_ema50:
                score += 20
                reasons.append(f"{macro_tf.upper()}: Strong Bullish Trend (Trading above 50 & 200 EMA)")
            elif macro_close < macro_ema200 and macro_close < macro_ema50:
                score -= 20
                reasons.append(f"{macro_tf.upper()}: Strong Bearish Trend (Trading below 50 & 200 EMA)")

            if macro_st_dir == 1:
                score += 15
                reasons.append(f"{macro_tf.upper()}: Supertrend is Bullish (Green)")
            else:
                score -= 15
                reasons.append(f"{macro_tf.upper()}: Supertrend is Bearish (Red)")

        # 2. Structural Timeframe Analysis (30 Points)
        if df_struct is not None and len(df_struct) >= 15:
            struct_close = float(df_struct["close"].iloc[-1])
            struct_ema9 = float(df_struct["ema_9"].iloc[-1])
            struct_ema21 = float(df_struct["ema_21"].iloc[-1])
            struct_rsi = float(df_struct["rsi"].iloc[-1])

            if struct_ema9 > struct_ema21:
                score += 15
                reasons.append(f"{struct_tf.upper()}: 9 EMA is above 21 EMA (Upward Momentum)")
            else:
                score -= 15
                reasons.append(f"{struct_tf.upper()}: 9 EMA is below 21 EMA (Downward Momentum)")

            if struct_rsi > 55:
                score += 15
                reasons.append(f"{struct_tf.upper()}: RSI at {struct_rsi:.1f} shows solid Bullish momentum")
            elif struct_rsi < 45:
                score -= 15
                reasons.append(f"{struct_tf.upper()}: RSI at {struct_rsi:.1f} shows solid Bearish pressure")

        # 3. Execution & Trigger Timeframe Analysis (35 Points)
        if df_exec is not None and len(df_exec) >= 10:
            exec_close = float(df_exec["close"].iloc[-1])
            exec_vwap = float(df_exec["vwap"].iloc[-1])
            exec_atr = float(df_exec["atr"].iloc[-1])

            if exec_close > exec_vwap:
                score += 20
                reasons.append(f"{exec_tf.upper()}: Price is holding above Intraday VWAP (Buyers in control)")
            else:
                score -= 20
                reasons.append(f"{exec_tf.upper()}: Price is below Intraday VWAP (Sellers in control)")

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
            elif upper_wick > body * 1.3:
                score -= 15
                reasons.append(f"{exec_tf.upper()}: Strong Upper Rejection Wick (Supply rejection at resistance)")

        # 4. Live Quote & Order Flow Confluence (10 Points)
        if live_quote and "order_flow_ratio" in live_quote:
            of_ratio = live_quote["order_flow_ratio"]
            if of_ratio >= 60.0:
                score += 10
                reasons.append(f"Live Order Flow: Strong Buyer Dominance ({of_ratio}% Bids vs Asks)")
            elif of_ratio <= 40.0:
                score -= 10
                reasons.append(f"Live Order Flow: Strong Seller Dominance ({100 - of_ratio:.1f}% Asks vs Bids)")

        # Determine Signal Classification
        if score >= CONFLUENCE_BUY_THRESHOLD:
            signal = "STRONG BUY"
            direction = "BUY"
        elif score >= 35:
            signal = "BUY"
            direction = "BUY"
        elif score <= CONFLUENCE_SELL_THRESHOLD:
            signal = "STRONG SELL"
            direction = "SELL"
        elif score <= -35:
            signal = "SELL"
            direction = "SELL"
        else:
            signal = "WAIT / NO TRADE"
            direction = "NEUTRAL"
            reasons.append("Conflicting timeframe signals or market consolidation. Wait for structural breakout.")

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
            
            if direction == "BUY":
                opt_type = "CE"
                recommended_strike = f"{atm_strike} CE"
                approx_prem = round(risk_points * 2.2, 1)
                delta = 0.55
                opt_sl = round(max(5.0, approx_prem - (risk_points * delta)), 1)
                opt_t1 = round(approx_prem + (reward_t1_points * delta), 1)
                opt_t2 = round(approx_prem + (reward_t2_points * delta), 1)
            elif direction == "SELL":
                opt_type = "PE"
                recommended_strike = f"{atm_strike} PE"
                approx_prem = round(risk_points * 2.2, 1)
                delta = 0.55
                opt_sl = round(max(5.0, approx_prem - (risk_points * delta)), 1)
                opt_t1 = round(approx_prem + (reward_t1_points * delta), 1)
                opt_t2 = round(approx_prem + (reward_t2_points * delta), 1)
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
                "lot_size": INDEX_TOKENS[self.symbol]["lot_size"]
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
            "analyzed_timeframes": list(analyzed_tf.keys())
        }
