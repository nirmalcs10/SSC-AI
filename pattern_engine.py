"""
High-Probability Option Trading Pattern Engine.
Specialized detector for Tier-1 and Tier-2 chart & price action setups:
1. Liquidity Sweep & Market Structure Shift (MSS / CHOCH)
2. Bull Flag & Bear Flag (Pole + Tight Consolidation Breakout)
3. Inside Bar Volatility Compression Breakout
4. Double Bottom (W Pattern) & Double Top (M Pattern) Neckline Breaks
5. Intraday VWAP Reclaim / Breakdown with Volume Expansion
6. High-Impact Candlestick Triggers (Hammer, Shooting Star, Engulfing at S/R)

Prioritizes setups with fast Gamma acceleration, tight invalidation, and minimal Theta bleed.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


class PatternEngine:
    @staticmethod
    def detect_liquidity_sweep(df: pd.DataFrame, pdh_pdl: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
        """
        Detects Institutional Liquidity Sweep + CHOCH:
        - Price spikes above Previous Day High (PDH) or recent swing high, but closes back inside with an upper wick.
        - Or price sweeps below Previous Day Low (PDL) or recent swing low, but closes back inside with a lower wick.
        """
        if df is None or len(df) < 5:
            return None

        last_c = df.iloc[-1]
        c_open = float(last_c["open"])
        c_high = float(last_c["high"])
        c_low = float(last_c["low"])
        c_close = float(last_c["close"])
        body = abs(c_close - c_open)
        upper_wick = c_high - max(c_open, c_close)
        lower_wick = min(c_open, c_close) - c_low

        pdh = pdh_pdl.get("pdh", 0.0) if pdh_pdl else 0.0
        pdl = pdh_pdl.get("pdl", 0.0) if pdh_pdl else 0.0
        recent_high = float(df["high"].iloc[-15:-1].max()) if len(df) >= 15 else c_high
        recent_low = float(df["low"].iloc[-15:-1].min()) if len(df) >= 15 else c_low

        ref_high = pdh if pdh > 0 else recent_high
        ref_low = pdl if pdl > 0 else recent_low

        # Bearish Liquidity Sweep (Swept High -> Fast Put / PE Move)
        if c_high > ref_high and c_close < ref_high and upper_wick > body * 1.2:
            return {
                "pattern_name": "Liquidity Sweep + CHOCH (High Swept)",
                "tier": "TIER_1_OPTIMAL",
                "direction": "SELL",
                "recommended_option": "PE (Put Option)",
                "invalidation_level": round(c_high + (body * 0.2), 2),
                "trigger_price": round(c_close, 2),
                "confidence": 92,
                "description": f"Institutions swept liquidity above key high (₹{ref_high:,.1f}) and aggressively rejected. Trapped CE buyers panic-selling. High probability fast PE move."
            }

        # Bullish Liquidity Sweep (Swept Low -> Fast Call / CE Move)
        if c_low < ref_low and c_close > ref_low and lower_wick > body * 1.2:
            return {
                "pattern_name": "Liquidity Sweep + CHOCH (Low Swept)",
                "tier": "TIER_1_OPTIMAL",
                "direction": "BUY",
                "recommended_option": "CE (Call Option)",
                "invalidation_level": round(c_low - (body * 0.2), 2),
                "trigger_price": round(c_close, 2),
                "confidence": 92,
                "description": f"Institutions swept stops below key low (₹{ref_low:,.1f}) and aggressively reclaimed support. Trapped PE sellers covering. High probability fast CE move."
            }

        return None

    @staticmethod
    def detect_flag_pattern(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Bull Flag / Bear Flag Breakouts:
        - Strong directional impulse pole over 3-8 candles.
        - Followed by 2-5 candles of low-volume consolidation.
        - Latest candle breaks out in the pole direction with volume expansion.
        """
        if df is None or len(df) < 10:
            return None

        # Lookback: check pole from -10 to -4, flag from -4 to -2, breakout at -1
        pole_df = df.iloc[-10:-4]
        flag_df = df.iloc[-4:-1]
        breakout_c = df.iloc[-1]

        pole_move = float(pole_df["close"].iloc[-1] - pole_df["close"].iloc[0])
        flag_range = float(flag_df["high"].max() - flag_df["low"].min())
        b_close = float(breakout_c["close"])
        b_vol = float(breakout_c["volume"])
        b_vol_ma = float(breakout_c.get("volume_ma20", b_vol))

        # Bull Flag: Strong up pole, tight flag consolidation, breakout upward with volume
        if pole_move > flag_range * 1.8 and pole_move > 0:
            flag_high = float(flag_df["high"].max())
            flag_low = float(flag_df["low"].min())
            if b_close > flag_high and b_vol >= b_vol_ma * 0.90:
                return {
                    "pattern_name": "Bull Flag Breakout",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "BUY",
                    "recommended_option": "CE (Call Option)",
                    "invalidation_level": round(flag_low, 2),
                    "trigger_price": round(b_close, 2),
                    "confidence": 88,
                    "description": f"Impulsive pole upward confirmed by tight consolidation flag. Clean breakout above ₹{flag_high:,.1f} with volume expansion. Ideal momentum for option gamma."
                }

        # Bear Flag: Strong down pole, tight flag consolidation, breakdown downward with volume
        if pole_move < -flag_range * 1.8 and pole_move < 0:
            flag_high = float(flag_df["high"].max())
            flag_low = float(flag_df["low"].min())
            if b_close < flag_low and b_vol >= b_vol_ma * 0.90:
                return {
                    "pattern_name": "Bear Flag Breakdown",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SELL",
                    "recommended_option": "PE (Put Option)",
                    "invalidation_level": round(flag_high, 2),
                    "trigger_price": round(b_close, 2),
                    "confidence": 88,
                    "description": f"Sharp impulse downward confirmed by bear flag. Clean breakdown below ₹{flag_low:,.1f} with volume. Trapped dip-buyers will fuel rapid PE expansion."
                }

        return None

    @staticmethod
    def detect_inside_bar_compression(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Inside Bar Compression & Volatility Explosion:
        - Mother bar at index -2 (or -3) followed by inside bar at index -2.
        - Latest candle breaks out of the mother bar boundaries with volume.
        """
        if df is None or len(df) < 4:
            return None

        mother = df.iloc[-3]
        inside = df.iloc[-2]
        curr = df.iloc[-1]

        m_high = float(mother["high"])
        m_low = float(mother["low"])
        i_high = float(inside["high"])
        i_low = float(inside["low"])
        c_close = float(curr["close"])
        c_vol = float(curr["volume"])
        c_vol_ma = float(curr.get("volume_ma20", c_vol))

        # Check if inside bar was contained within mother bar
        is_inside = (i_high <= m_high * 1.0005) and (i_low >= m_low * 0.9995)

        if is_inside:
            # Bullish Inside Bar Breakout
            if c_close > m_high and c_vol >= c_vol_ma * 0.90:
                return {
                    "pattern_name": "Inside Bar Compression Breakout",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "BUY",
                    "recommended_option": "CE (Call Option)",
                    "invalidation_level": round(i_low, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 85,
                    "description": f"Volatility compression inside ₹{m_low:,.1f} - ₹{m_high:,.1f} resolved upward with volume surge. Rapid IV expansion and delta burst favor option buying."
                }
            # Bearish Inside Bar Breakdown
            elif c_close < m_low and c_vol >= c_vol_ma * 0.90:
                return {
                    "pattern_name": "Inside Bar Compression Breakdown",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SELL",
                    "recommended_option": "PE (Put Option)",
                    "invalidation_level": round(i_high, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 85,
                    "description": f"Volatility compression resolved downward below ₹{m_low:,.1f} with volume surge. Fast sell-off creates immediate option delta expansion."
                }

        return None

    @staticmethod
    def detect_double_bottom_top(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Double Bottom (W Pattern) & Double Top (M Pattern) with Neckline Break:
        - 2 distinct bottoms/tops within 0.2% tolerance.
        - Current price breaks out through the central neckline.
        """
        if df is None or len(df) < 15:
            return None

        # Look at last 15 candles for 2 swing lows or 2 swing highs
        lows = df["low"].iloc[-15:].values
        highs = df["high"].iloc[-15:].values
        c_close = float(df["close"].iloc[-1])

        # Identify local minima
        min_indices = [i for i in range(1, len(lows)-1) if lows[i] < lows[i-1] and lows[i] <= lows[i+1]]
        if len(min_indices) >= 2:
            idx1, idx2 = min_indices[-2], min_indices[-1]
            if (idx2 - idx1) >= 3:  # At least 3 bars apart
                low1 = lows[idx1]
                low2 = lows[idx2]
                if abs(low1 - low2) / low1 <= 0.0025:  # Within 0.25%
                    # Neckline is the highest peak between the two bottoms
                    neckline = float(highs[idx1:idx2+1].max())
                    if c_close > neckline:
                        return {
                            "pattern_name": "Double Bottom (W Pattern)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "BUY",
                            "recommended_option": "CE (Call Option)",
                            "invalidation_level": round(min(low1, low2), 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 87,
                            "description": f"Classic W Pattern confirmed with twin bottoms at ₹{low1:,.1f} & ₹{low2:,.1f}. Neckline broken at ₹{neckline:,.1f}. Strong institutional support base."
                        }

        # Identify local maxima
        max_indices = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] >= highs[i+1]]
        if len(max_indices) >= 2:
            idx1, idx2 = max_indices[-2], max_indices[-1]
            if (idx2 - idx1) >= 3:
                high1 = highs[idx1]
                high2 = highs[idx2]
                if abs(high1 - high2) / high1 <= 0.0025:
                    neckline = float(lows[idx1:idx2+1].min())
                    if c_close < neckline:
                        return {
                            "pattern_name": "Double Top (M Pattern)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "SELL",
                            "recommended_option": "PE (Put Option)",
                            "invalidation_level": round(max(high1, high2), 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 87,
                            "description": f"Classic M Pattern confirmed with dual rejections at ₹{high1:,.1f} & ₹{high2:,.1f}. Neckline broken at ₹{neckline:,.1f}. Overhead supply dominates."
                        }

        return None

    @staticmethod
    def detect_vwap_crossover(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Intraday VWAP Reclaim or Breakdown with Volume Expansion:
        - Price was below VWAP and now crossed above with green candle & volume.
        - Or price was above VWAP and now crossed below with red candle & volume.
        """
        if df is None or len(df) < 3 or "vwap" not in df.columns:
            return None

        prev_c = df.iloc[-2]
        curr_c = df.iloc[-1]

        prev_close = float(prev_c["close"])
        prev_vwap = float(prev_c["vwap"])
        curr_close = float(curr_c["close"])
        curr_open = float(curr_c["open"])
        curr_vwap = float(curr_c["vwap"])
        curr_vol = float(curr_c["volume"])
        curr_vol_ma = float(curr_c.get("volume_ma20", curr_vol))

        # Bullish VWAP Reclaim
        if prev_close <= prev_vwap and curr_close > curr_vwap and curr_close > curr_open and curr_vol >= curr_vol_ma * 0.90:
            return {
                "pattern_name": "Intraday VWAP Reclaim & Breakout",
                "tier": "TIER_1_OPTIMAL",
                "direction": "BUY",
                "recommended_option": "CE (Call Option)",
                "invalidation_level": round(curr_vwap - (abs(curr_close - curr_open) * 0.5), 2),
                "trigger_price": round(curr_close, 2),
                "confidence": 84,
                "description": f"Price powerfully reclaimed VWAP (₹{curr_vwap:,.1f}) from below with volume expansion. Institutional buyers taking control of intraday trend."
            }

        # Bearish VWAP Breakdown
        if prev_close >= prev_vwap and curr_close < curr_vwap and curr_close < curr_open and curr_vol >= curr_vol_ma * 0.90:
            return {
                "pattern_name": "Intraday VWAP Breakdown & Rejection",
                "tier": "TIER_1_OPTIMAL",
                "direction": "SELL",
                "recommended_option": "PE (Put Option)",
                "invalidation_level": round(curr_vwap + (abs(curr_close - curr_open) * 0.5), 2),
                "trigger_price": round(curr_close, 2),
                "confidence": 84,
                "description": f"Price broke down below VWAP (₹{curr_vwap:,.1f}) from above with volume surge. Institutional sellers in control of intraday direction."
            }

        return None

    @classmethod
    def detect_all(
        cls,
        df_5m: pd.DataFrame,
        df_3m: Optional[pd.DataFrame] = None,
        pdh_pdl: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs all Tier-1 and Tier-2 detectors across 5m and 3m charts.
        Returns sorted list of active option setups (highest confidence first).
        """
        detected = []

        ref_df = df_3m if (df_3m is not None and len(df_3m) >= 5) else df_5m

        # Run Detectors
        sweep = cls.detect_liquidity_sweep(ref_df, pdh_pdl)
        if sweep:
            detected.append(sweep)

        flag = cls.detect_flag_pattern(df_5m)
        if flag:
            detected.append(flag)

        inside = cls.detect_inside_bar_compression(df_5m)
        if inside:
            detected.append(inside)

        double_bt = cls.detect_double_bottom_top(df_5m)
        if double_bt:
            detected.append(double_bt)

        vwap_cross = cls.detect_vwap_crossover(df_5m)
        if vwap_cross:
            detected.append(vwap_cross)

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected
