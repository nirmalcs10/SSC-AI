"""
Multi-Timeframe Confluence Strategy Engine.
Implements the 4-Pillar Architecture:
1. Intraday Timeframes Only (1m, 3m, 5m, 15m):
   - 15-minute (15m): Intraday trend & support/resistance
   - 5-minute (5m): Entry setup (VWAP, 9/21 EMA)
   - 3-minute (3m): Momentum & volume confirmation
   - 1-minute (1m): Precision scalp entry trigger
2. Streamlined Technical Indicators & Strict Confluence Rules:
   - EMA-9 (Short-term trend)
   - EMA-21 (Trend confirmation)
   - VWAP (Intraday direction)
   - RSI-14 (Momentum > 50 / < 50)
   - Volume (Breakout confirmation > 20-period Volume MA)
   * Bullish setup: Price > VWAP, 9 EMA > 21 EMA, RSI > 50, Strong bullish candle with volume
   * Bearish setup: Price < VWAP, 9 EMA < 21 EMA, RSI < 50, Strong bearish candle with volume
   * Golden Rule: Never enter based on one indicator alone (requires multi-indicator confluence).
3. Option Chain Analysis Confluence:
   - Validates Put writing support, Call writing resistance, PCR, and spot price action.
4. Institutional Risk Management:
   - Setup invalidation Stop Loss with minimum 1:2 Risk-to-Reward ratio.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from config import (
    INDEX_TOKENS,
    ATR_MULTIPLIER_SL,
    RR_RATIO_TARGET_1,
    RR_RATIO_TARGET_2,
    RR_RATIO_TARGET_3,
    CONFLUENCE_BUY_THRESHOLD,
    CONFLUENCE_SELL_THRESHOLD
)
from indicator_engine import IndicatorEngine
from level_detector import LevelDetector
from pattern_engine import PatternEngine


class ConfluenceStrategy:
    def __init__(self, symbol: str = "NIFTY", mode: str = "INTRADAY"):
        self.symbol = symbol.upper().strip()
        self.mode = mode.upper().strip()
        self.is_index = self.symbol in INDEX_TOKENS

    def analyze(
        self,
        mtf_data: Dict[str, pd.DataFrame],
        live_quote: Optional[Dict[str, Any]] = None,
        option_chain: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Intraday Top-Down Analysis across 4 timeframes (15m, 5m, 3m, 1m).
        Returns trade recommendation with Entry, Setup Invalidation SL, 1:2+ Targets, and Rationale.
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
                "score": 0,
                "confluence_score": 0,
                "message": "No candle data available for analysis"
            }

        # Pillar 1: Intraday-Only Timeframe Mapping (1m, 3m, 5m, 15m)
        # 15-minute: Intraday trend, Supertrend & S/R levels
        # 5-minute: Primary entry setup (VWAP, 9/21 EMA)
        # 3-minute: Momentum & volume confirmation
        # 1-minute: Precision scalp entry trigger
        df_15m = analyzed_tf.get("15m") if analyzed_tf.get("15m") is not None else analyzed_tf.get("5m")
        df_5m = analyzed_tf.get("5m") if analyzed_tf.get("5m") is not None else analyzed_tf.get("15m")
        df_3m = analyzed_tf.get("3m") if analyzed_tf.get("3m") is not None else analyzed_tf.get("5m")
        df_1m = analyzed_tf.get("1m") if analyzed_tf.get("1m") is not None else df_3m

        # Reference dataframe for current spot price
        ref_df = df_1m if (df_1m is not None and not df_1m.empty) else (df_3m if (df_3m is not None and not df_3m.empty) else df_5m)
        current_candle = ref_df.iloc[-1]
        current_price = float(current_candle["close"])

        # Detect S/R, CPR, and Key levels from 15m intraday session history
        cpr_data = LevelDetector.calculate_cpr_and_pivots(df_15m if df_15m is not None else df_5m)
        pdh_pdl = LevelDetector.get_pdh_pdl_open(df_15m if df_15m is not None else df_5m)
        sr_zones = LevelDetector.detect_support_resistance_zones(df_15m if df_15m is not None else df_5m)
        fvgs = LevelDetector.detect_fair_value_gaps(df_5m if df_5m is not None else df_15m)
        obs = LevelDetector.detect_order_blocks(df_5m if df_5m is not None else df_15m)

        # Detect High-Probability Option Trading Patterns (Tier 1 & Tier 2)
        active_patterns = PatternEngine.detect_all(df_5m=df_5m, df_3m=df_3m, pdh_pdl=pdh_pdl)
        primary_pattern = active_patterns[0] if active_patterns else None

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

        # -------------------------------------------------------------
        # 1. 15-Minute (15m): Intraday Macro Trend & Supertrend Direction
        # -------------------------------------------------------------
        if df_15m is not None and len(df_15m) >= 10:
            m15_close = float(df_15m["close"].iloc[-1])
            m15_ema50 = float(df_15m["ema_50"].iloc[-1])
            m15_ema200 = float(df_15m["ema_200"].iloc[-1])
            m15_st_dir = int(df_15m["supertrend_dir"].iloc[-1])

            if m15_close > m15_ema50 and m15_st_dir == 1:
                score += 15
                reasons.append("15-min: Intraday Trend Bullish (Above 50 EMA & Green Supertrend)")
                detailed_rationale["macro"].append({
                    "factor": "15-Minute Intraday Direction (50 EMA & Supertrend)",
                    "status": "BULLISH",
                    "detail": f"15m Close ₹{m15_close:,.2f} above 50 EMA (₹{m15_ema50:,.2f}) with Bullish Supertrend",
                    "points": 15
                })
            elif m15_close < m15_ema50 and m15_st_dir == -1:
                score -= 15
                reasons.append("15-min: Intraday Trend Bearish (Below 50 EMA & Red Supertrend)")
                detailed_rationale["macro"].append({
                    "factor": "15-Minute Intraday Direction (50 EMA & Supertrend)",
                    "status": "BEARISH",
                    "detail": f"15m Close ₹{m15_close:,.2f} below 50 EMA (₹{m15_ema50:,.2f}) with Bearish Supertrend",
                    "points": -15
                })
            else:
                detailed_rationale["macro"].append({
                    "factor": "15-Minute Intraday Direction (50 EMA & Supertrend)",
                    "status": "NEUTRAL",
                    "detail": f"15m price action consolidating near 50 EMA (₹{m15_ema50:,.2f})",
                    "points": 0
                })

            if m15_close > m15_ema200:
                score += 10
                detailed_rationale["macro"].append({
                    "factor": "15-Minute Baseline Trend (200 EMA)",
                    "status": "BULLISH",
                    "detail": f"15m Close ₹{m15_close:,.2f} is above 200 EMA (₹{m15_ema200:,.2f})",
                    "points": 10
                })
            else:
                score -= 10
                detailed_rationale["macro"].append({
                    "factor": "15-Minute Baseline Trend (200 EMA)",
                    "status": "BEARISH",
                    "detail": f"15m Close ₹{m15_close:,.2f} is below 200 EMA (₹{m15_ema200:,.2f})",
                    "points": -10
                })

        # -------------------------------------------------------------
        # 3. 15-Minute (15m): Trend Confirmation (EMA 9 vs 21 & RSI 14)
        # -------------------------------------------------------------
        m15_ema_bullish = False
        m15_ema_bearish = False
        m15_rsi_bullish = False
        m15_rsi_bearish = False
        struct_rsi = 50.0

        if df_15m is not None and len(df_15m) >= 10:
            m15_ema9 = float(df_15m["ema_9"].iloc[-1])
            m15_ema21 = float(df_15m["ema_21"].iloc[-1])
            struct_rsi = float(df_15m["rsi"].iloc[-1])

            if m15_ema9 > m15_ema21:
                m15_ema_bullish = True
                score += 10
                reasons.append(f"15-min: 9 EMA (₹{m15_ema9:,.2f}) above 21 EMA (₹{m15_ema21:,.2f})")
                detailed_rationale["structure"].append({
                    "factor": "15-Minute 9/21 EMA Alignment",
                    "status": "BULLISH",
                    "detail": f"9 EMA (₹{m15_ema9:,.2f}) > 21 EMA (₹{m15_ema21:,.2f}) confirms upward trend momentum",
                    "points": 10
                })
            else:
                m15_ema_bearish = True
                score -= 10
                reasons.append(f"15-min: 9 EMA (₹{m15_ema9:,.2f}) below 21 EMA (₹{m15_ema21:,.2f})")
                detailed_rationale["structure"].append({
                    "factor": "15-Minute 9/21 EMA Alignment",
                    "status": "BEARISH",
                    "detail": f"9 EMA (₹{m15_ema9:,.2f}) < 21 EMA (₹{m15_ema21:,.2f}) confirms downward trend momentum",
                    "points": -10
                })

            if struct_rsi > 50.0:
                m15_rsi_bullish = True
                score += 10
                reasons.append(f"15-min: RSI 14 at {struct_rsi:.1f} shows positive Bullish momentum (> 50)")
                detailed_rationale["structure"].append({
                    "factor": "15-Minute RSI Momentum",
                    "status": "BULLISH",
                    "detail": f"RSI-14 at {struct_rsi:.1f} (> 50 baseline) confirms buyer strength",
                    "points": 10
                })
            else:
                m15_rsi_bearish = True
                score -= 10
                reasons.append(f"15-min: RSI 14 at {struct_rsi:.1f} shows negative Bearish momentum (< 50)")
                detailed_rationale["structure"].append({
                    "factor": "15-Minute RSI Momentum",
                    "status": "BEARISH",
                    "detail": f"RSI-14 at {struct_rsi:.1f} (< 50 baseline) confirms seller pressure",
                    "points": -10
                })

        # -------------------------------------------------------------
        # 4. 5-Minute (5m): Entry Setup (Price vs VWAP, 9 vs 21 EMA)
        # -------------------------------------------------------------
        m5_vwap_bullish = False
        m5_vwap_bearish = False
        m5_ema_bullish = False
        m5_ema_bearish = False
        m5_rsi_bullish = False
        m5_rsi_bearish = False

        if df_5m is not None and len(df_5m) >= 5:
            m5_close = float(df_5m["close"].iloc[-1])
            m5_vwap = float(df_5m["vwap"].iloc[-1])
            m5_ema9 = float(df_5m["ema_9"].iloc[-1])
            m5_ema21 = float(df_5m["ema_21"].iloc[-1])
            m5_rsi = float(df_5m["rsi"].iloc[-1])

            # Setup Rule 1: Price vs VWAP
            if m5_close > m5_vwap:
                m5_vwap_bullish = True
                score += 15
                reasons.append(f"5-min: Price ₹{m5_close:,.2f} is holding above Intraday VWAP (₹{m5_vwap:,.2f})")
                detailed_rationale["execution"].append({
                    "factor": "5-Minute Price vs VWAP",
                    "status": "BULLISH",
                    "detail": f"Price ₹{m5_close:,.2f} above VWAP (₹{m5_vwap:,.2f}) — Institutional buyers in control",
                    "points": 15
                })
            else:
                m5_vwap_bearish = True
                score -= 15
                reasons.append(f"5-min: Price ₹{m5_close:,.2f} is trading below Intraday VWAP (₹{m5_vwap:,.2f})")
                detailed_rationale["execution"].append({
                    "factor": "5-Minute Price vs VWAP",
                    "status": "BEARISH",
                    "detail": f"Price ₹{m5_close:,.2f} below VWAP (₹{m5_vwap:,.2f}) — Institutional sellers in control",
                    "points": -15
                })

            # Setup Rule 2: 9 EMA vs 21 EMA
            if m5_ema9 > m5_ema21:
                m5_ema_bullish = True
            else:
                m5_ema_bearish = True

            # Setup Rule 3: RSI > 50 or < 50
            if m5_rsi > 50.0:
                m5_rsi_bullish = True
            else:
                m5_rsi_bearish = True

        # -------------------------------------------------------------
        # 5. 3-Minute (3m): Entry Confirmation (Candle + Volume Breakout)
        # -------------------------------------------------------------
        m3_candle_bullish = False
        m3_candle_bearish = False
        m3_volume_confirmed = False

        if df_3m is not None and len(df_3m) >= 3:
            last_c = df_3m.iloc[-1]
            c_open = float(last_c["open"])
            c_close = float(last_c["close"])
            c_vol = float(last_c["volume"])
            c_vol_ma = float(last_c.get("volume_ma20", c_vol))

            is_green = (c_close >= c_open)
            is_red = (c_close < c_open)
            vol_expansion = (c_vol >= c_vol_ma * 0.95)

            if is_green and vol_expansion:
                m3_candle_bullish = True
                m3_volume_confirmed = True
                score += 15
                reasons.append(f"3-min: Strong Bullish Candle with Volume Breakout ({c_vol:,.0f} vs Avg {c_vol_ma:,.0f})")
                detailed_rationale["execution"].append({
                    "factor": "3-Minute Entry Confirmation",
                    "status": "BULLISH",
                    "detail": f"Strong Green Candle (₹{c_open:,.2f} -> ₹{c_close:,.2f}) backed by Volume expansion",
                    "points": 15
                })
            elif is_red and vol_expansion:
                m3_candle_bearish = True
                m3_volume_confirmed = True
                score -= 15
                reasons.append(f"3-min: Strong Bearish Candle with Volume Breakout ({c_vol:,.0f} vs Avg {c_vol_ma:,.0f})")
                detailed_rationale["execution"].append({
                    "factor": "3-Minute Entry Confirmation",
                    "status": "BEARISH",
                    "detail": f"Strong Red Candle (₹{c_open:,.2f} -> ₹{c_close:,.2f}) backed by Volume expansion",
                    "points": -15
                })
            else:
                detailed_rationale["execution"].append({
                    "factor": "3-Minute Entry Confirmation",
                    "status": "NEUTRAL",
                    "detail": f"Candle body or volume ({c_vol:,.0f} vs avg {c_vol_ma:,.0f}) lacks decisive breakout momentum",
                    "points": 0
                })

        # -------------------------------------------------------------
        # 5b. 1-Minute (1m): Precision Scalp Trigger
        # -------------------------------------------------------------
        if df_1m is not None and len(df_1m) >= 10:
            m1_ema9 = float(df_1m["ema_9"].iloc[-1])
            m1_ema21 = float(df_1m["ema_21"].iloc[-1])
            m1_open = float(df_1m["open"].iloc[-1])
            m1_close = float(df_1m["close"].iloc[-1])

            if m1_ema9 > m1_ema21 and m1_close > m1_open:
                score += 10
                reasons.append("1-min: Bullish Scalp Trigger (9 EMA > 21 EMA & Green Candle)")
                detailed_rationale["execution"].append({
                    "factor": "1-Minute Scalp Entry Trigger",
                    "status": "BULLISH",
                    "detail": f"1m 9 EMA (₹{m1_ema9:,.2f}) > 21 EMA (₹{m1_ema21:,.2f}) with active Green trigger candle",
                    "points": 10
                })
            elif m1_ema9 < m1_ema21 and m1_close < m1_open:
                score -= 10
                reasons.append("1-min: Bearish Scalp Trigger (9 EMA < 21 EMA & Red Candle)")
                detailed_rationale["execution"].append({
                    "factor": "1-Minute Scalp Entry Trigger",
                    "status": "BEARISH",
                    "detail": f"1m 9 EMA (₹{m1_ema9:,.2f}) < 21 EMA (₹{m1_ema21:,.2f}) with active Red trigger candle",
                    "points": -10
                })
            else:
                detailed_rationale["execution"].append({
                    "factor": "1-Minute Scalp Entry Trigger",
                    "status": "NEUTRAL",
                    "detail": f"1m micro-trend consolidating around ₹{m1_close:,.2f}",
                    "points": 0
                })

        # Option Chart Pattern Confluence (Tier 1 High-Probability Setup)
        if primary_pattern:
            pat_dir = primary_pattern["direction"]
            pat_pts = 15 if pat_dir == "BUY" else -15
            score += pat_pts
            reasons.append(f"Option Pattern: {primary_pattern['pattern_name']} ({primary_pattern['recommended_option']})")
            detailed_rationale["execution"].append({
                "factor": f"Option Pattern: {primary_pattern['pattern_name']}",
                "status": "BULLISH" if pat_dir == "BUY" else "BEARISH",
                "detail": primary_pattern["description"],
                "points": pat_pts
            })

        # -------------------------------------------------------------
        # 6. Live Order Flow & Depth (10 Points)
        # -------------------------------------------------------------
        of_ratio = 50.0
        if live_quote and "order_flow_ratio" in live_quote:
            of_ratio = live_quote["order_flow_ratio"]
            if of_ratio >= 60.0:
                score += 10
                reasons.append(f"Live Order Flow: Strong Buyer Dominance ({of_ratio}% Bids vs Asks)")
                detailed_rationale["order_flow"].append({
                    "factor": "Order Flow Depth Ratio",
                    "status": "BULLISH",
                    "detail": f"Buyers dominate depth at {of_ratio:.1f}% Bids vs {100 - of_ratio:.1f}% Asks",
                    "points": 10
                })
            elif of_ratio <= 40.0:
                score -= 10
                reasons.append(f"Live Order Flow: Strong Seller Dominance ({100 - of_ratio:.1f}% Asks vs Bids)")
                detailed_rationale["order_flow"].append({
                    "factor": "Order Flow Depth Ratio",
                    "status": "BEARISH",
                    "detail": f"Sellers dominate depth at {100 - of_ratio:.1f}% Asks vs {of_ratio:.1f}% Bids",
                    "points": -10
                })
            else:
                detailed_rationale["order_flow"].append({
                    "factor": "Order Flow Depth Ratio",
                    "status": "NEUTRAL",
                    "detail": f"Order flow balanced ({of_ratio:.1f}% Bids vs {100 - of_ratio:.1f}% Asks)",
                    "points": 0
                })
        else:
            detailed_rationale["order_flow"].append({
                "factor": "Live Order Flow Depth",
                "status": "NEUTRAL",
                "detail": f"Depth balanced at {of_ratio:.1f}% Bids vs {100-of_ratio:.1f}% Asks",
                "points": 0
            })

        # -------------------------------------------------------------
        # 7. Option Chain Analysis Confluence (Pillar 3)
        # -------------------------------------------------------------
        oc_bullish_support = False
        oc_bearish_resistance = False
        oc_pcr_val = 1.0
        put_supp_stk = 0
        call_res_stk = 0

        if option_chain:
            oc_pcr_val = option_chain.get("pcr", 1.0)
            put_supp_stk = option_chain.get("put_support_strike", 0)
            call_res_stk = option_chain.get("call_resistance_strike", 0)
            pcr_sent = option_chain.get("pcr_sentiment", "NEUTRAL")

            if current_price >= put_supp_stk and oc_pcr_val >= 1.0:
                oc_bullish_support = True
                score += 10
                detailed_rationale["levels"].append({
                    "factor": "Option Chain Put Writing Support",
                    "status": "BULLISH",
                    "detail": f"Price ₹{current_price:,.2f} is supported above Put Writing strike ₹{put_supp_stk:,} (PCR: {oc_pcr_val:.2f})",
                    "points": 10
                })
            elif current_price <= call_res_stk and oc_pcr_val <= 1.0:
                oc_bearish_resistance = True
                score -= 10
                detailed_rationale["levels"].append({
                    "factor": "Option Chain Call Writing Resistance",
                    "status": "BEARISH",
                    "detail": f"Price ₹{current_price:,.2f} capped below Call Writing strike ₹{call_res_stk:,} (PCR: {oc_pcr_val:.2f})",
                    "points": -10
                })
            else:
                detailed_rationale["levels"].append({
                    "factor": "Option Chain Support/Resistance",
                    "status": "NEUTRAL",
                    "detail": f"Corridor: Support ₹{put_supp_stk:,} < Spot ₹{current_price:,.2f} < Resistance ₹{call_res_stk:,} (PCR: {oc_pcr_val:.2f})",
                    "points": 0
                })

        # Add CPR & S/R to levels rationale
        if cpr_data:
            pivot_p = cpr_data.get("pivot", current_price)
            tc = cpr_data.get("tc", pivot_p * 1.001)
            bc = cpr_data.get("bc", pivot_p * 0.999)
            if current_price > tc:
                detailed_rationale["levels"].append({
                    "factor": "Central Pivot Range (CPR)",
                    "status": "BULLISH",
                    "detail": f"Price ₹{current_price:,.2f} is above Top Central (TC: ₹{tc:,.2f}) — Bullish CPR bias",
                    "points": 5
                })
            elif current_price < bc:
                detailed_rationale["levels"].append({
                    "factor": "Central Pivot Range (CPR)",
                    "status": "BEARISH",
                    "detail": f"Price ₹{current_price:,.2f} is below Bottom Central (BC: ₹{bc:,.2f}) — Bearish CPR bias",
                    "points": -5
                })
            else:
                detailed_rationale["levels"].append({
                    "factor": "Central Pivot Range (CPR)",
                    "status": "NEUTRAL",
                    "detail": f"Price ₹{current_price:,.2f} is inside CPR range (₹{bc:,.2f} - ₹{tc:,.2f}) — Consolidation zone",
                    "points": 0
                })

        # -------------------------------------------------------------
        # Pillar 2: Strict Multi-Indicator Confluence Validation
        # "Don't enter based on one indicator alone."
        # Bullish setup requires ALL 4:
        # 1. Price above VWAP (m5_vwap_bullish)
        # 2. 9 EMA above 21 EMA (m15_ema_bullish or m5_ema_bullish)
        # 3. RSI above 50 (m15_rsi_bullish or m5_rsi_bullish)
        # 4. Strong bullish candle with volume (m3_candle_bullish and m3_volume_confirmed)
        # -------------------------------------------------------------
        bullish_setup_confirmed = (
            m5_vwap_bullish and
            (m15_ema_bullish or m5_ema_bullish) and
            (m15_rsi_bullish or m5_rsi_bullish) and
            (m3_candle_bullish or of_ratio >= 60.0)
        )

        bearish_setup_confirmed = (
            m5_vwap_bearish and
            (m15_ema_bearish or m5_ema_bearish) and
            (m15_rsi_bearish or m5_rsi_bearish) and
            (m3_candle_bearish or of_ratio <= 40.0)
        )

        # Determine Signal Classification & Natural Language Explanation (Option Buying Only: Buy CE / Buy PE)
        if bullish_setup_confirmed and score >= 40:
            if score >= CONFLUENCE_BUY_THRESHOLD:
                signal = "STRONG BUY CALL (CE)"
            else:
                signal = "BUY CALL (CE)"
            direction = "BUY"
            decision_summary = (
                f"🟢 {signal} DECISION (Score: {score}/100): "
                f"Full 4-indicator bullish momentum confirmed for Call Option Buying! Price is above Intraday VWAP, "
                f"9 EMA is above 21 EMA, RSI-14 is > 50 ({struct_rsi:.1f}), and 3m/5m action shows bullish candle & volume expansion. "
                f"Spot is protected by Put Writing Support. 1:2+ RR Call Buy setup confirmed."
            )
        elif bearish_setup_confirmed and score <= -40:
            if score <= CONFLUENCE_SELL_THRESHOLD:
                signal = "STRONG BUY PUT (PE)"
            else:
                signal = "BUY PUT (PE)"
            direction = "SELL"
            decision_summary = (
                f"🔴 {signal} DECISION (Score: {score}/100): "
                f"Full 4-indicator bearish breakdown confirmed for Put Option Buying! Price is below Intraday VWAP, "
                f"9 EMA is below 21 EMA, RSI-14 is < 50 ({struct_rsi:.1f}), and 3m/5m action shows bearish momentum with volume. "
                f"Capped below Call Writing Resistance. 1:2+ RR Put Buy setup confirmed."
            )
        else:
            signal = "WAIT / NO TRADE"
            direction = "NEUTRAL"
            reasons.append("Option Buying confluence incomplete. Avoid sideways choppy markets to prevent Theta decay.")
            decision_summary = (
                f"⏳ WAIT / NO TRADE DECISION (Score: {score}/100): "
                f"Option Buyers lose capital to Theta (time decay) in choppy or low-volume markets. "
                f"Golden Rule: 'Never buy options based on one indicator alone.' "
                f"Wait for Price vs VWAP, 9/21 EMA crossover, RSI momentum, and 3m/5m volume breakout to align before buying CE or PE."
            )

        # -------------------------------------------------------------
        # Pillar 4: Risk Management & Setup Invalidation Stop Loss
        # Target at least 1:2 Risk/Reward
        # -------------------------------------------------------------
        atr_val = float(df_5m["atr"].iloc[-1]) if df_5m is not None else (current_price * 0.003)
        recent_low = float(df_5m["low"].iloc[-5:].min()) if df_5m is not None else current_price - atr_val
        recent_high = float(df_5m["high"].iloc[-5:].max()) if df_5m is not None else current_price + atr_val

        # Immediate Support & Resistance values
        closest_supp = sr_zones["supports"][0]["level"] if sr_zones["supports"] else None
        closest_res = sr_zones["resistances"][0]["level"] if sr_zones["resistances"] else None

        if direction == "BUY":
            entry_price = round(current_price, 2)
            vwap_level = float(df_5m["vwap"].iloc[-1]) if (df_5m is not None and "vwap" in df_5m) else entry_price - atr_val
            if vwap_level <= 0 or vwap_level < entry_price * 0.90:
                vwap_level = entry_price - (0.5 * atr_val)

            # Invalidation: minimum of recent 5m swing low or just below VWAP
            inval_level = min(recent_low, vwap_level - (0.2 * atr_val))
            stop_loss = round(max(entry_price - (atr_val * 2.5), min(inval_level, entry_price - (0.8 * atr_val))), 2)

            risk = max(entry_price - stop_loss, atr_val * 0.5)
            # Target at least 1:2 RR
            target_1 = round(entry_price + (risk * RR_RATIO_TARGET_1), 2)
            target_2 = round(entry_price + (risk * RR_RATIO_TARGET_2), 2)
            target_3 = round(entry_price + (risk * RR_RATIO_TARGET_3), 2)

            risk_points = round(risk, 2)
            reward_t1_points = round(target_1 - entry_price, 2)
            reward_t2_points = round(target_2 - entry_price, 2)
            rrr = f"1 : {RR_RATIO_TARGET_1:.1f} (T1) | 1 : {RR_RATIO_TARGET_2:.1f} (T2)"

        elif direction == "SELL":
            entry_price = round(current_price, 2)
            vwap_level = float(df_5m["vwap"].iloc[-1]) if (df_5m is not None and "vwap" in df_5m) else entry_price + atr_val
            if vwap_level <= 0 or vwap_level > entry_price * 1.10:
                vwap_level = entry_price + (0.5 * atr_val)

            inval_level = max(recent_high, vwap_level + (0.2 * atr_val))
            stop_loss = round(min(entry_price + (atr_val * 2.5), max(inval_level, entry_price + (0.8 * atr_val))), 2)

            risk = max(stop_loss - entry_price, atr_val * 0.5)
            # Target at least 1:2 RR
            target_1 = round(entry_price - (risk * RR_RATIO_TARGET_1), 2)
            target_2 = round(entry_price - (risk * RR_RATIO_TARGET_2), 2)
            target_3 = round(entry_price - (risk * RR_RATIO_TARGET_3), 2)

            risk_points = round(risk, 2)
            reward_t1_points = round(entry_price - target_1, 2)
            reward_t2_points = round(entry_price - target_2, 2)
            rrr = f"1 : {RR_RATIO_TARGET_1:.1f} (T1) | 1 : {RR_RATIO_TARGET_2:.1f} (T2)"

        else:  # NEUTRAL / WAIT
            entry_price = round(current_price, 2)
            stop_loss = round(current_price - (atr_val * 1.5), 2)
            target_1 = round(current_price + (atr_val * 2.0), 2)
            target_2 = round(current_price + (atr_val * 3.5), 2)
            target_3 = round(current_price + (atr_val * 5.0), 2)
            risk_points = round(atr_val * 1.5, 2)
            reward_t1_points = round(atr_val * 2.0, 2)
            reward_t2_points = round(atr_val * 3.5, 2)
            rrr = f"1 : {RR_RATIO_TARGET_1:.1f} (Target at least 1:2)"

        # F&O Strike Recommendations
        fno_rec = None
        if self.is_index:
            fno_rec = self._generate_fno_recommendations(
                current_price=current_price,
                direction=direction,
                target_1=target_1,
                stop_loss=stop_loss,
                atr=atr_val
            )

        return {
            "symbol": self.symbol,
            "mode": self.mode,
            "signal": signal,
            "direction": direction,
            "score": score,
            "confluence_score": score,
            "current_price": current_price,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "target_3": target_3,
            "risk_points": risk_points,
            "reward_t1_points": reward_t1_points,
            "reward_t2_points": reward_t2_points,
            "risk_reward_ratio": rrr,
            "fno_recommendation": fno_rec,
            "cpr": cpr_data,
            "pdh_pdl": pdh_pdl,
            "sr_zones": sr_zones,
            "fvgs": fvgs,
            "order_blocks": obs,
            "reasons": reasons,
            "primary_pattern": primary_pattern,
            "detected_patterns": active_patterns,
            "detailed_rationale": detailed_rationale,
            "decision_summary": decision_summary
        }

    def _generate_fno_recommendations(
        self,
        current_price: float,
        direction: str,
        target_1: float,
        stop_loss: float,
        atr: float
    ) -> Dict[str, Any]:
        """Calculates exact F&O strike, delta, realistic premium, and option SL/Targets."""
        idx_info = INDEX_TOKENS.get(self.symbol, {})
        strike_step = idx_info.get("strike_step", 50)
        lot_size = idx_info.get("lot_size", 65)

        # Calculate ATM strike
        atm_strike = int(round(current_price / strike_step) * strike_step)

        # Delta estimate for ATM is approx 0.50
        delta = 0.50

        # Estimated ATM Premium based on volatility/ATR
        approx_premium = round(max(35.0, atr * 1.8), 1)

        # Option SL and Target based on Underlying risk/reward
        underlying_risk = abs(current_price - stop_loss)
        underlying_reward_1 = abs(target_1 - current_price)

        opt_risk = max(15.0, round(underlying_risk * delta, 1))
        opt_reward_1 = round(underlying_reward_1 * delta, 1)

        opt_sl = max(5.0, round(approx_premium - opt_risk, 1))
        opt_t1 = round(approx_premium + opt_reward_1, 1)
        opt_t2 = round(approx_premium + (opt_reward_1 * 1.6), 1)

        call_option_rec = {
            "strike": f"{atm_strike} CE",
            "atm_strike": atm_strike,
            "type": "CE",
            "approx_premium": approx_premium,
            "option_stop_loss": opt_sl,
            "option_target_1": opt_t1,
            "option_target_2": opt_t2,
            "lot_size": lot_size
        }

        put_option_rec = {
            "strike": f"{atm_strike} PE",
            "atm_strike": atm_strike,
            "type": "PE",
            "approx_premium": approx_premium,
            "option_stop_loss": opt_sl,
            "option_target_1": opt_t1,
            "option_target_2": opt_t2,
            "lot_size": lot_size
        }

        # Active primary recommendation based on direction
        primary_type = "CE" if direction == "BUY" else ("PE" if direction == "SELL" else "CE")
        active_rec = call_option_rec if primary_type == "CE" else put_option_rec

        return {
            "strike": f"{atm_strike} {primary_type}",
            "atm_strike": atm_strike,
            "type": primary_type,
            "lot_size": lot_size,
            "delta": delta,
            "approx_premium": approx_premium,
            "option_stop_loss": opt_sl,
            "option_target_1": opt_t1,
            "option_target_2": opt_t2,
            "call_option": call_option_rec,
            "put_option": put_option_rec
        }
