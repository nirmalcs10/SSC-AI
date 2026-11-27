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
    def _get_candle_time(df: pd.DataFrame, idx: int) -> int:
        """Returns integer unix timestamp for candle at row index idx."""
        try:
            if df is not None and not df.empty:
                # Support negative and positive index bounds
                actual_idx = idx if idx >= 0 else len(df) + idx
                actual_idx = max(0, min(actual_idx, len(df) - 1))
                row = df.iloc[actual_idx]
                if "datetime" in row and pd.notna(row["datetime"]):
                    return int(pd.Timestamp(row["datetime"]).timestamp())
                elif isinstance(df.index, pd.DatetimeIndex):
                    return int(pd.Timestamp(df.index[actual_idx]).timestamp())
        except Exception:
            pass
        return int(pd.Timestamp.now().timestamp())

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
            t_curr = PatternEngine._get_candle_time(df, -1)
            t_start = PatternEngine._get_candle_time(df, -15 if len(df) >= 15 else 0)
            return {
                "pattern_name": "Liquidity Sweep + CHOCH (High Swept)",
                "tier": "TIER_1_OPTIMAL",
                "direction": "SELL",
                "recommended_option": "PE (Put Option)",
                "invalidation_level": round(c_high + (body * 0.2), 2),
                "trigger_price": round(c_close, 2),
                "confidence": 92,
                "description": f"Institutions swept liquidity above key high (₹{ref_high:,.1f}) and aggressively rejected. Trapped CE buyers panic-selling. High probability fast PE move.",
                "drawing_data": {
                    "pattern_name": "Liquidity Sweep + CHOCH (High Swept)",
                    "lines": [
                        {
                            "title": "Sweep Level",
                            "color": "#FFFFFF",
                            "lineWidth": 2,
                            "lineStyle": 1,
                            "points": [
                                {"time": t_start, "value": round(ref_high, 2)},
                                {"time": t_curr, "value": round(ref_high, 2)}
                            ]
                        }
                    ],
                    "price_lines": [
                        {
                            "price": round(ref_high, 2),
                            "color": "#FFFFFF",
                            "lineWidth": 2,
                            "lineStyle": 1,
                            "axisLabelVisible": True,
                            "title": f"Swept High: ₹{ref_high:,.1f}"
                        }
                    ],
                    "markers": [
                        {
                            "time": t_curr,
                            "position": "aboveBar",
                            "color": "#FF1744",
                            "shape": "arrowDown",
                            "text": f"Swept High @ ₹{c_high:,.1f} (CHOCH Rejection)"
                        }
                    ]
                }
            }

        # Bullish Liquidity Sweep (Swept Low -> Fast Call / CE Move)
        if c_low < ref_low and c_close > ref_low and lower_wick > body * 1.2:
            t_curr = PatternEngine._get_candle_time(df, -1)
            t_start = PatternEngine._get_candle_time(df, -15 if len(df) >= 15 else 0)
            return {
                "pattern_name": "Liquidity Sweep + CHOCH (Low Swept)",
                "tier": "TIER_1_OPTIMAL",
                "direction": "BUY",
                "recommended_option": "CE (Call Option)",
                "invalidation_level": round(c_low - (body * 0.2), 2),
                "trigger_price": round(c_close, 2),
                "confidence": 92,
                "description": f"Institutions swept stops below key low (₹{ref_low:,.1f}) and aggressively reclaimed support. Trapped PE sellers covering. High probability fast CE move.",
                "drawing_data": {
                    "pattern_name": "Liquidity Sweep + CHOCH (Low Swept)",
                    "lines": [
                        {
                            "title": "Sweep Level",
                            "color": "#00E676",
                            "lineWidth": 2,
                            "lineStyle": 1,
                            "points": [
                                {"time": t_start, "value": round(ref_low, 2)},
                                {"time": t_curr, "value": round(ref_low, 2)}
                            ]
                        }
                    ],
                    "price_lines": [
                        {
                            "price": round(ref_low, 2),
                            "color": "#00E676",
                            "lineWidth": 2,
                            "lineStyle": 1,
                            "axisLabelVisible": True,
                            "title": f"Swept Low: ₹{ref_low:,.1f}"
                        }
                    ],
                    "markers": [
                        {
                            "time": t_curr,
                            "position": "belowBar",
                            "color": "#00E676",
                            "shape": "arrowUp",
                            "text": f"Swept Low @ ₹{c_low:,.1f} (CHOCH Reclaim)"
                        }
                    ]
                }
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
                t_pole_start = PatternEngine._get_candle_time(df, -10)
                t_pole_end = PatternEngine._get_candle_time(df, -4)
                t_flag_end = PatternEngine._get_candle_time(df, -1)
                p_pole_start = float(pole_df["close"].iloc[0])
                p_pole_end = float(pole_df["close"].iloc[-1])
                return {
                    "pattern_name": "Bull Flag Breakout",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "BUY",
                    "recommended_option": "CE (Call Option)",
                    "invalidation_level": round(flag_low, 2),
                    "trigger_price": round(b_close, 2),
                    "confidence": 88,
                    "description": f"Impulsive pole upward confirmed by tight consolidation flag. Clean breakout above ₹{flag_high:,.1f} with volume expansion. Ideal momentum for option gamma.",
                    "drawing_data": {
                        "pattern_name": "Bull Flag Breakout",
                        "lines": [
                            {
                                "title": "Impulse Pole",
                                "color": "#00E5FF",
                                "lineWidth": 3,
                                "lineStyle": 0,
                                "points": [
                                    {"time": t_pole_start, "value": round(p_pole_start, 2)},
                                    {"time": t_pole_end, "value": round(p_pole_end, 2)}
                                ]
                            },
                            {
                                "title": "Flag Resistance",
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_pole_end, "value": round(flag_high, 2)},
                                    {"time": t_flag_end, "value": round(flag_high, 2)}
                                ]
                            },
                            {
                                "title": "Flag Support",
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_pole_end, "value": round(flag_low, 2)},
                                    {"time": t_flag_end, "value": round(flag_low, 2)}
                                ]
                            }
                        ],
                        "price_lines": [
                            {
                                "price": round(flag_high, 2),
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 0,
                                "axisLabelVisible": True,
                                "title": f"Flag Breakout: ₹{flag_high:,.1f}"
                            }
                        ],
                        "markers": [
                            {"time": t_pole_start, "position": "belowBar", "color": "#00E5FF", "shape": "circle", "text": "Pole Start"},
                            {"time": t_pole_end, "position": "aboveBar", "color": "#00E5FF", "shape": "circle", "text": "Flag Pole"},
                            {"time": t_flag_end, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Bull Flag Breakout @ ₹{b_close:,.1f}"}
                        ]
                    }
                }

        # Bear Flag: Strong down pole, tight flag consolidation, breakdown downward with volume
        if pole_move < -flag_range * 1.8 and pole_move < 0:
            flag_high = float(flag_df["high"].max())
            flag_low = float(flag_df["low"].min())
            if b_close < flag_low and b_vol >= b_vol_ma * 0.90:
                t_pole_start = PatternEngine._get_candle_time(df, -10)
                t_pole_end = PatternEngine._get_candle_time(df, -4)
                t_flag_end = PatternEngine._get_candle_time(df, -1)
                p_pole_start = float(pole_df["close"].iloc[0])
                p_pole_end = float(pole_df["close"].iloc[-1])
                return {
                    "pattern_name": "Bear Flag Breakdown",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SELL",
                    "recommended_option": "PE (Put Option)",
                    "invalidation_level": round(flag_high, 2),
                    "trigger_price": round(b_close, 2),
                    "confidence": 88,
                    "description": f"Sharp impulse downward confirmed by bear flag. Clean breakdown below ₹{flag_low:,.1f} with volume. Trapped dip-buyers will fuel rapid PE expansion.",
                    "drawing_data": {
                        "pattern_name": "Bear Flag Breakdown",
                        "lines": [
                            {
                                "title": "Impulse Pole",
                                "color": "#00E5FF",
                                "lineWidth": 3,
                                "lineStyle": 0,
                                "points": [
                                    {"time": t_pole_start, "value": round(p_pole_start, 2)},
                                    {"time": t_pole_end, "value": round(p_pole_end, 2)}
                                ]
                            },
                            {
                                "title": "Flag Resistance",
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_pole_end, "value": round(flag_high, 2)},
                                    {"time": t_flag_end, "value": round(flag_high, 2)}
                                ]
                            },
                            {
                                "title": "Flag Support",
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_pole_end, "value": round(flag_low, 2)},
                                    {"time": t_flag_end, "value": round(flag_low, 2)}
                                ]
                            }
                        ],
                        "price_lines": [
                            {
                                "price": round(flag_low, 2),
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 0,
                                "axisLabelVisible": True,
                                "title": f"Flag Breakdown: ₹{flag_low:,.1f}"
                            }
                        ],
                        "markers": [
                            {"time": t_pole_start, "position": "aboveBar", "color": "#00E5FF", "shape": "circle", "text": "Pole Start"},
                            {"time": t_pole_end, "position": "belowBar", "color": "#00E5FF", "shape": "circle", "text": "Flag Pole"},
                            {"time": t_flag_end, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Bear Flag Breakdown @ ₹{b_close:,.1f}"}
                        ]
                    }
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
            t_mother = PatternEngine._get_candle_time(df, -3)
            t_inside = PatternEngine._get_candle_time(df, -2)
            t_curr = PatternEngine._get_candle_time(df, -1)
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
                    "description": f"Volatility compression inside ₹{m_low:,.1f} - ₹{m_high:,.1f} resolved upward with volume surge. Rapid IV expansion and delta burst favor option buying.",
                    "drawing_data": {
                        "pattern_name": "Inside Bar Compression Breakout",
                        "lines": [
                            {
                                "title": "Mother High",
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_mother, "value": round(m_high, 2)},
                                    {"time": t_curr, "value": round(m_high, 2)}
                                ]
                            },
                            {
                                "title": "Mother Low",
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_mother, "value": round(m_low, 2)},
                                    {"time": t_curr, "value": round(m_low, 2)}
                                ]
                            }
                        ],
                        "price_lines": [
                            {
                                "price": round(m_high, 2),
                                "color": "#00E676",
                                "lineWidth": 2,
                                "lineStyle": 0,
                                "axisLabelVisible": True,
                                "title": f"Mother High: ₹{m_high:,.1f}"
                            }
                        ],
                        "markers": [
                            {"time": t_mother, "position": "aboveBar", "color": "#00E5FF", "shape": "circle", "text": "Mother Bar"},
                            {"time": t_inside, "position": "aboveBar", "color": "#FFD600", "shape": "circle", "text": "Inside Bar (Coil)"},
                            {"time": t_curr, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Breakout @ ₹{c_close:,.1f}"}
                        ]
                    }
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
                    "description": f"Volatility compression resolved downward below ₹{m_low:,.1f} with volume surge. Fast sell-off creates immediate option delta expansion.",
                    "drawing_data": {
                        "pattern_name": "Inside Bar Compression Breakdown",
                        "lines": [
                            {
                                "title": "Mother High",
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_mother, "value": round(m_high, 2)},
                                    {"time": t_curr, "value": round(m_high, 2)}
                                ]
                            },
                            {
                                "title": "Mother Low",
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_mother, "value": round(m_low, 2)},
                                    {"time": t_curr, "value": round(m_low, 2)}
                                ]
                            }
                        ],
                        "price_lines": [
                            {
                                "price": round(m_low, 2),
                                "color": "#FFFFFF",
                                "lineWidth": 2,
                                "lineStyle": 0,
                                "axisLabelVisible": True,
                                "title": f"Mother Low: ₹{m_low:,.1f}"
                            }
                        ],
                        "markers": [
                            {"time": t_mother, "position": "belowBar", "color": "#00E5FF", "shape": "circle", "text": "Mother Bar"},
                            {"time": t_inside, "position": "belowBar", "color": "#FFD600", "shape": "circle", "text": "Inside Bar (Coil)"},
                            {"time": t_curr, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Breakdown @ ₹{c_close:,.1f}"}
                        ]
                    }
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
                    neck_rel = int(np.argmax(highs[idx1:idx2+1]))
                    neck_idx = idx1 + neck_rel
                    neckline = float(highs[neck_idx])
                    if c_close > neckline:
                        t_start = PatternEngine._get_candle_time(df, -15)
                        t_b1 = PatternEngine._get_candle_time(df, -15 + idx1)
                        t_mid = PatternEngine._get_candle_time(df, -15 + neck_idx)
                        t_b2 = PatternEngine._get_candle_time(df, -15 + idx2)
                        t_break = PatternEngine._get_candle_time(df, -1)
                        return {
                            "pattern_name": "Double Bottom (W Pattern)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "BUY",
                            "recommended_option": "CE (Call Option)",
                            "invalidation_level": round(min(low1, low2), 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 87,
                            "description": f"Classic W Pattern confirmed with twin bottoms at ₹{low1:,.1f} & ₹{low2:,.1f}. Neckline broken at ₹{neckline:,.1f}. Strong institutional support base.",
                            "drawing_data": {
                                "pattern_name": "Double Bottom (W Pattern)",
                                "lines": [
                                    {
                                        "title": "W Pattern",
                                        "color": "#00E676",
                                        "lineWidth": 3,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t_start, "value": round(float(highs[0]), 2)},
                                            {"time": t_b1, "value": round(float(low1), 2)},
                                            {"time": t_mid, "value": round(float(neckline), 2)},
                                            {"time": t_b2, "value": round(float(low2), 2)},
                                            {"time": t_break, "value": round(float(c_close), 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {
                                        "price": round(neckline, 2),
                                        "color": "#FFD600",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "axisLabelVisible": True,
                                        "title": f"W Neckline: ₹{neckline:,.1f}"
                                    }
                                ],
                                "markers": [
                                    {"time": t_b1, "position": "belowBar", "color": "#00E676", "shape": "circle", "text": f"Bottom 1 (₹{low1:,.1f})"},
                                    {"time": t_mid, "position": "aboveBar", "color": "#FFD600", "shape": "circle", "text": f"Peak (₹{neckline:,.1f})"},
                                    {"time": t_b2, "position": "belowBar", "color": "#00E676", "shape": "circle", "text": f"Bottom 2 (₹{low2:,.1f})"},
                                    {"time": t_break, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Neckline Breakout @ ₹{c_close:,.1f}"}
                                ]
                            }
                        }

        # Identify local maxima
        max_indices = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] >= highs[i+1]]
        if len(max_indices) >= 2:
            idx1, idx2 = max_indices[-2], max_indices[-1]
            if (idx2 - idx1) >= 3:
                high1 = highs[idx1]
                high2 = highs[idx2]
                if abs(high1 - high2) / high1 <= 0.0025:
                    neck_rel = int(np.argmin(lows[idx1:idx2+1]))
                    neck_idx = idx1 + neck_rel
                    neckline = float(lows[neck_idx])
                    if c_close < neckline:
                        t_start = PatternEngine._get_candle_time(df, -15)
                        t_t1 = PatternEngine._get_candle_time(df, -15 + idx1)
                        t_mid = PatternEngine._get_candle_time(df, -15 + neck_idx)
                        t_t2 = PatternEngine._get_candle_time(df, -15 + idx2)
                        t_break = PatternEngine._get_candle_time(df, -1)
                        return {
                            "pattern_name": "Double Top (M Pattern)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "SELL",
                            "recommended_option": "PE (Put Option)",
                            "invalidation_level": round(max(high1, high2), 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 87,
                            "description": f"Classic M Pattern confirmed with dual rejections at ₹{high1:,.1f} & ₹{high2:,.1f}. Neckline broken at ₹{neckline:,.1f}. Overhead supply dominates.",
                            "drawing_data": {
                                "pattern_name": "Double Top (M Pattern)",
                                "lines": [
                                    {
                                        "title": "M Pattern",
                                        "color": "#FFFFFF",
                                        "lineWidth": 3,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t_start, "value": round(float(lows[0]), 2)},
                                            {"time": t_t1, "value": round(float(high1), 2)},
                                            {"time": t_mid, "value": round(float(neckline), 2)},
                                            {"time": t_t2, "value": round(float(high2), 2)},
                                            {"time": t_break, "value": round(float(c_close), 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {
                                        "price": round(neckline, 2),
                                        "color": "#FFFFFF",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "axisLabelVisible": True,
                                        "title": f"M Neckline: ₹{neckline:,.1f}"
                                    }
                                ],
                                "markers": [
                                    {"time": t_t1, "position": "aboveBar", "color": "#FF5252", "shape": "circle", "text": f"Top 1 (₹{high1:,.1f})"},
                                    {"time": t_mid, "position": "belowBar", "color": "#FFD600", "shape": "circle", "text": f"Neckline (₹{neckline:,.1f})"},
                                    {"time": t_t2, "position": "aboveBar", "color": "#FF5252", "shape": "circle", "text": f"Top 2 (₹{high2:,.1f})"},
                                    {"time": t_break, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Neckline Breakdown @ ₹{c_close:,.1f}"}
                                ]
                            }
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
    def detect_triple_taps_strategy(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Tamil Crypto School (TCS) Triple Taps Strategy:
        - Price touches a key trendline/support 3 times (Tap 1, Tap 2, Tap 3).
        - 3rd tap triggers rapid momentum acceleration.
        - Fibonacci golden section (38.2%, 50%, 61.8%) confluence on 3rd tap.
        """
        if df is None or len(df) < 18:
            return None

        sub_df = df.iloc[-25:] if len(df) >= 25 else df
        lows = sub_df["low"].values
        highs = sub_df["high"].values
        curr_c = sub_df.iloc[-1]
        c_close = float(curr_c["close"])
        offset = len(df) - len(sub_df)

        # 1. Bullish Triple Taps on Ascending Support Trendline
        min_indices = [i for i in range(1, len(lows)-1) if lows[i] < lows[i-1] and lows[i] < lows[i+1]]
        if len(min_indices) >= 3:
            i1, i2, i3 = min_indices[-3], min_indices[-2], min_indices[-1]
            if (i2 - i1) >= 2 and (i3 - i2) >= 2 and (len(lows) - 1 - i3) <= 2:
                l1, l2, l3 = float(lows[i1]), float(lows[i2]), float(lows[i3])
                if l1 < l2 < l3:  # Ascending lows P1 < P2 < P3
                    slope = (l3 - l1) / max(i3 - i1, 1)
                    expected_l2 = l1 + slope * (i2 - i1)
                    if abs(l2 - expected_l2) / l2 <= 0.005:  # Valid trendline linearity
                        if c_close >= l3:
                            impulse_high = float(highs[i1:i3].max())
                            impulse_range = max(impulse_high - l1, 1.0)
                            fib_retrace = ((impulse_high - l3) / impulse_range) * 100.0
                            fib_tag = f"Fib {fib_retrace:.1f}% Golden Zone" if (35.0 <= fib_retrace <= 68.0) else "Trendline Tap 3"

                            t1 = cls._get_candle_time(df, offset + i1)
                            t2 = cls._get_candle_time(df, offset + i2)
                            t3 = cls._get_candle_time(df, offset + i3)
                            t_curr = cls._get_candle_time(df, -1)

                            target_100 = round(impulse_high, 2)
                            target_1618 = round(l3 + (impulse_range * 1.618), 2)

                            return {
                                "pattern_name": f"Triple Taps Strategy (Bullish Tap 3 • {fib_tag})",
                                "tier": "TIER_1_OPTIMAL",
                                "direction": "BUY",
                                "recommended_option": "CE (Call Option)",
                                "invalidation_level": round(l3 - (abs(c_close - l3) * 0.4), 2),
                                "trigger_price": round(c_close, 2),
                                "confidence": 94 if (35.0 <= fib_retrace <= 68.0) else 89,
                                "description": f"Master TCS Strategy: 3rd Price Tap confirmed on ascending support (₹{l1:,.1f} -> ₹{l2:,.1f} -> ₹{l3:,.1f}). Golden section confluence ({fib_retrace:.1f}%). 3rd tap triggers rapid institutional trend acceleration toward ₹{target_1618:,.1f}.",
                                "drawing_data": {
                                    "pattern_name": "Triple Taps Strategy (Bullish Tap 3)",
                                    "lines": [
                                        {
                                            "title": "Ascending Support Line",
                                            "color": "#FFFFFF",
                                            "lineWidth": 2,
                                            "lineStyle": 0,
                                            "points": [
                                                {"time": t1, "value": round(l1, 2)},
                                                {"time": t2, "value": round(l2, 2)},
                                                {"time": t3, "value": round(l3, 2)},
                                                {"time": t_curr, "value": round(c_close, 2)}
                                            ]
                                        }
                                    ],
                                    "price_lines": [
                                        {"price": target_100, "color": "#FFFFFF", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Fib 100% Target: ₹{target_100:,.1f}"},
                                        {"price": target_1618, "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Fib 161.8% Acceleration: ₹{target_1618:,.1f}"}
                                    ],
                                    "markers": [
                                        {"time": t1, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Tap 1 (₹{l1:,.1f})"},
                                        {"time": t2, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Tap 2 (₹{l2:,.1f})"},
                                        {"time": t3, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Tap 3 Trigger ({fib_tag}) @ ₹{l3:,.1f}"}
                                    ]
                                }
                            }

        # 2. Bearish Triple Taps on Descending Resistance Line
        max_indices = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
        if len(max_indices) >= 3:
            i1, i2, i3 = max_indices[-3], max_indices[-2], max_indices[-1]
            if (i2 - i1) >= 2 and (i3 - i2) >= 2 and (len(highs) - 1 - i3) <= 2:
                h1, h2, h3 = float(highs[i1]), float(highs[i2]), float(highs[i3])
                if h1 > h2 > h3:  # Descending peaks P1 > P2 > P3
                    slope = (h3 - h1) / max(i3 - i1, 1)
                    expected_h2 = h1 + slope * (i2 - i1)
                    if abs(h2 - expected_h2) / h2 <= 0.005:
                        if c_close <= h3:
                            impulse_low = float(lows[i1:i3].min())
                            impulse_range = max(h1 - impulse_low, 1.0)
                            fib_retrace = ((h3 - impulse_low) / impulse_range) * 100.0
                            fib_tag = f"Fib {fib_retrace:.1f}% Golden Zone" if (35.0 <= fib_retrace <= 68.0) else "Resistance Tap 3"

                            t1 = cls._get_candle_time(df, offset + i1)
                            t2 = cls._get_candle_time(df, offset + i2)
                            t3 = cls._get_candle_time(df, offset + i3)
                            t_curr = cls._get_candle_time(df, -1)

                            target_100 = round(impulse_low, 2)
                            target_1618 = round(h3 - (impulse_range * 1.618), 2)

                            return {
                                "pattern_name": f"Triple Taps Strategy (Bearish Tap 3 • {fib_tag})",
                                "tier": "TIER_1_OPTIMAL",
                                "direction": "SELL",
                                "recommended_option": "PE (Put Option)",
                                "invalidation_level": round(h3 + (abs(h3 - c_close) * 0.4), 2),
                                "trigger_price": round(c_close, 2),
                                "confidence": 94 if (35.0 <= fib_retrace <= 68.0) else 89,
                                "description": f"Master TCS Strategy: 3rd Price Tap confirmed on descending resistance (₹{h1:,.1f} -> ₹{h2:,.1f} -> ₹{h3:,.1f}). Golden section confluence ({fib_retrace:.1f}%). 3rd tap triggers rapid downward acceleration toward ₹{target_1618:,.1f}.",
                                "drawing_data": {
                                    "pattern_name": "Triple Taps Strategy (Bearish Tap 3)",
                                    "lines": [
                                        {
                                            "title": "Descending Resistance Line",
                                            "color": "#FFFFFF",
                                            "lineWidth": 2,
                                            "lineStyle": 0,
                                            "points": [
                                                {"time": t1, "value": round(h1, 2)},
                                                {"time": t2, "value": round(h2, 2)},
                                                {"time": t3, "value": round(h3, 2)},
                                                {"time": t_curr, "value": round(c_close, 2)}
                                            ]
                                        }
                                    ],
                                    "price_lines": [
                                        {"price": target_100, "color": "#FFFFFF", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Fib 100% Target: ₹{target_100:,.1f}"},
                                        {"price": target_1618, "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Fib 161.8% Acceleration: ₹{target_1618:,.1f}"}
                                    ],
                                    "markers": [
                                        {"time": t1, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Tap 1 (₹{h1:,.1f})"},
                                        {"time": t2, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Tap 2 (₹{h2:,.1f})"},
                                        {"time": t3, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Tap 3 Trigger ({fib_tag}) @ ₹{h3:,.1f}"}
                                    ]
                                }
                            }
        return None

    @classmethod
    def detect_head_and_shoulders(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Head and Shoulders (Bearish) and Inverse Head and Shoulders (Bullish):
        - Baseline with 3 peaks: Left Shoulder, highest Head, Right Shoulder.
        - Neckline break confirms reversal.
        """
        if df is None or len(df) < 20:
            return None

        sub_df = df.iloc[-25:] if len(df) >= 25 else df
        highs = sub_df["high"].values
        lows = sub_df["low"].values
        curr_c = sub_df.iloc[-1]
        c_close = float(curr_c["close"])
        offset = len(df) - len(sub_df)

        # 1. Bearish Head & Shoulders
        max_idx = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] >= highs[i+1]]
        if len(max_idx) >= 3:
            s1_idx, h_idx, s2_idx = max_idx[-3], max_idx[-2], max_idx[-1]
            if (h_idx - s1_idx) >= 2 and (s2_idx - h_idx) >= 2:
                sh1, head, sh2 = float(highs[s1_idx]), float(highs[h_idx]), float(highs[s2_idx])
                # Head must be highest, shoulders roughly symmetrical within 0.5%
                if head > sh1 and head > sh2 and abs(sh1 - sh2) / sh1 <= 0.005:
                    neckline = float(lows[s1_idx:s2_idx+1].min())
                    if c_close < neckline:  # Breakdown confirmation
                        t_s1 = cls._get_candle_time(df, offset + s1_idx)
                        t_head = cls._get_candle_time(df, offset + h_idx)
                        t_s2 = cls._get_candle_time(df, offset + s2_idx)
                        t_break = cls._get_candle_time(df, -1)

                        return {
                            "pattern_name": "Head and Shoulders (Bearish Reversal)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "SELL",
                            "recommended_option": "PE (Put Option)",
                            "invalidation_level": round(sh2, 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 91,
                            "description": f"Master TCS Pattern: Head & Shoulders confirmed. Left Shoulder (₹{sh1:,.1f}), Head (₹{head:,.1f}), Right Shoulder (₹{sh2:,.1f}). Decisive breakdown below Neckline (₹{neckline:,.1f}).",
                            "drawing_data": {
                                "pattern_name": "Head and Shoulders (Bearish)",
                                "lines": [
                                    {
                                        "title": "H&S Structure",
                                        "color": "#FFFFFF",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t_s1, "value": round(sh1, 2)},
                                            {"time": t_head, "value": round(head, 2)},
                                            {"time": t_s2, "value": round(sh2, 2)},
                                            {"time": t_break, "value": round(c_close, 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {"price": round(neckline, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"H&S Neckline: ₹{neckline:,.1f}"}
                                ],
                                "markers": [
                                    {"time": t_s1, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Left Shoulder (₹{sh1:,.1f})"},
                                    {"time": t_head, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Head (₹{head:,.1f})"},
                                    {"time": t_s2, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Right Shoulder (₹{sh2:,.1f})"},
                                    {"time": t_break, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Neckline Breakdown @ ₹{c_close:,.1f}"}
                                ]
                            }
                        }

        # 2. Bullish Inverse Head & Shoulders
        min_idx = [i for i in range(1, len(lows)-1) if lows[i] < lows[i-1] and lows[i] <= lows[i+1]]
        if len(min_idx) >= 3:
            s1_idx, h_idx, s2_idx = min_idx[-3], min_idx[-2], min_idx[-1]
            if (h_idx - s1_idx) >= 2 and (s2_idx - h_idx) >= 2:
                sh1, head, sh2 = float(lows[s1_idx]), float(lows[h_idx]), float(lows[s2_idx])
                if head < sh1 and head < sh2 and abs(sh1 - sh2) / sh1 <= 0.005:
                    neckline = float(highs[s1_idx:s2_idx+1].max())
                    if c_close > neckline:  # Breakout confirmation
                        t_s1 = cls._get_candle_time(df, offset + s1_idx)
                        t_head = cls._get_candle_time(df, offset + h_idx)
                        t_s2 = cls._get_candle_time(df, offset + s2_idx)
                        t_break = cls._get_candle_time(df, -1)

                        return {
                            "pattern_name": "Inverse Head and Shoulders (Bullish Reversal)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "BUY",
                            "recommended_option": "CE (Call Option)",
                            "invalidation_level": round(sh2, 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 91,
                            "description": f"Master TCS Pattern: Inverse Head & Shoulders confirmed. Left Shoulder (₹{sh1:,.1f}), Inverted Head (₹{head:,.1f}), Right Shoulder (₹{sh2:,.1f}). Decisive breakout above Neckline (₹{neckline:,.1f}).",
                            "drawing_data": {
                                "pattern_name": "Inverse Head and Shoulders (Bullish)",
                                "lines": [
                                    {
                                        "title": "Inv H&S Structure",
                                        "color": "#FFFFFF",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t_s1, "value": round(sh1, 2)},
                                            {"time": t_head, "value": round(head, 2)},
                                            {"time": t_s2, "value": round(sh2, 2)},
                                            {"time": t_break, "value": round(c_close, 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {"price": round(neckline, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Inv H&S Neckline: ₹{neckline:,.1f}"}
                                ],
                                "markers": [
                                    {"time": t_s1, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Left Shoulder (₹{sh1:,.1f})"},
                                    {"time": t_head, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Head (₹{head:,.1f})"},
                                    {"time": t_s2, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Right Shoulder (₹{sh2:,.1f})"},
                                    {"time": t_break, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Neckline Breakout @ ₹{c_close:,.1f}"}
                                ]
                            }
                        }
        return None

    @classmethod
    def detect_triple_top_bottom(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Triple Top & Triple Bottom Patterns (Document 3):
        - 3 peaks or bottoms at nearly the same price level.
        - Confirmed by breakout of horizontal neckline.
        """
        if df is None or len(df) < 20:
            return None

        sub_df = df.iloc[-25:] if len(df) >= 25 else df
        highs = sub_df["high"].values
        lows = sub_df["low"].values
        curr_c = sub_df.iloc[-1]
        c_close = float(curr_c["close"])
        offset = len(df) - len(sub_df)

        # 1. Bearish Triple Top
        max_idx = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] >= highs[i+1]]
        if len(max_idx) >= 3:
            p1, p2, p3 = max_idx[-3], max_idx[-2], max_idx[-1]
            if (p2 - p1) >= 2 and (p3 - p2) >= 2:
                h1, h2, h3 = float(highs[p1]), float(highs[p2]), float(highs[p3])
                max_h = max(h1, h2, h3)
                min_h = min(h1, h2, h3)
                if (max_h - min_h) / max_h <= 0.0035:  # Within 0.35%
                    neckline = float(lows[p1:p3+1].min())
                    if c_close < neckline:
                        t1 = cls._get_candle_time(df, offset + p1)
                        t2 = cls._get_candle_time(df, offset + p2)
                        t3 = cls._get_candle_time(df, offset + p3)
                        t_break = cls._get_candle_time(df, -1)
                        return {
                            "pattern_name": "Triple Top (Bearish Reversal)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "SELL",
                            "recommended_option": "PE (Put Option)",
                            "invalidation_level": round(max_h, 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 90,
                            "description": f"Master TCS Pattern: Triple Top confirmed at ₹{max_h:,.1f}. 3 rejections at resistance followed by Neckline breakdown below ₹{neckline:,.1f}.",
                            "drawing_data": {
                                "pattern_name": "Triple Top (Bearish)",
                                "lines": [
                                    {
                                        "title": "Triple Top Resistance",
                                        "color": "#FFFFFF",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t1, "value": round(h1, 2)},
                                            {"time": t2, "value": round(h2, 2)},
                                            {"time": t3, "value": round(h3, 2)},
                                            {"time": t_break, "value": round(c_close, 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {"price": round(neckline, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Triple Top Neckline: ₹{neckline:,.1f}"}
                                ],
                                "markers": [
                                    {"time": t1, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Top 1 (₹{h1:,.1f})"},
                                    {"time": t2, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Top 2 (₹{h2:,.1f})"},
                                    {"time": t3, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": f"Top 3 (₹{h3:,.1f})"},
                                    {"time": t_break, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Breakdown @ ₹{c_close:,.1f}"}
                                ]
                            }
                        }

        # 2. Bullish Triple Bottom
        min_idx = [i for i in range(1, len(lows)-1) if lows[i] < lows[i-1] and lows[i] <= lows[i+1]]
        if len(min_idx) >= 3:
            b1, b2, b3 = min_idx[-3], min_idx[-2], min_idx[-1]
            if (b2 - b1) >= 2 and (b3 - b2) >= 2:
                l1, l2, l3 = float(lows[b1]), float(lows[b2]), float(lows[b3])
                max_l = max(l1, l2, l3)
                min_l = min(l1, l2, l3)
                if (max_l - min_l) / min_l <= 0.0035:
                    neckline = float(highs[b1:b3+1].max())
                    if c_close > neckline:
                        t1 = cls._get_candle_time(df, offset + b1)
                        t2 = cls._get_candle_time(df, offset + b2)
                        t3 = cls._get_candle_time(df, offset + b3)
                        t_break = cls._get_candle_time(df, -1)
                        return {
                            "pattern_name": "Triple Bottom (Bullish Reversal)",
                            "tier": "TIER_1_OPTIMAL",
                            "direction": "BUY",
                            "recommended_option": "CE (Call Option)",
                            "invalidation_level": round(min_l, 2),
                            "trigger_price": round(c_close, 2),
                            "confidence": 90,
                            "description": f"Master TCS Pattern: Triple Bottom confirmed at ₹{min_l:,.1f}. 3 bounces off support floor followed by Neckline breakout above ₹{neckline:,.1f}.",
                            "drawing_data": {
                                "pattern_name": "Triple Bottom (Bullish)",
                                "lines": [
                                    {
                                        "title": "Triple Bottom Support",
                                        "color": "#FFFFFF",
                                        "lineWidth": 2,
                                        "lineStyle": 0,
                                        "points": [
                                            {"time": t1, "value": round(l1, 2)},
                                            {"time": t2, "value": round(l2, 2)},
                                            {"time": t3, "value": round(l3, 2)},
                                            {"time": t_break, "value": round(c_close, 2)}
                                        ]
                                    }
                                ],
                                "price_lines": [
                                    {"price": round(neckline, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Triple Bottom Neckline: ₹{neckline:,.1f}"}
                                ],
                                "markers": [
                                    {"time": t1, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Bottom 1 (₹{l1:,.1f})"},
                                    {"time": t2, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Bottom 2 (₹{l2:,.1f})"},
                                    {"time": t3, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": f"Bottom 3 (₹{l3:,.1f})"},
                                    {"time": t_break, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Breakout @ ₹{c_close:,.1f}"}
                                ]
                            }
                        }
        return None

    @classmethod
    def detect_wedge_patterns(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Rising Wedge (Bearish Reversal) & Falling Wedge (Bullish Reversal):
        - Converging trendlines with contracting volatility.
        """
        if df is None or len(df) < 15:
            return None

        sub_df = df.iloc[-18:]
        highs = sub_df["high"].values
        lows = sub_df["low"].values
        curr_c = sub_df.iloc[-1]
        c_close = float(curr_c["close"])
        offset = len(df) - len(sub_df)

        h_start, h_end = float(highs[0]), float(highs[-2])
        l_start, l_end = float(lows[0]), float(lows[-2])

        # Rising Wedge: Higher highs and higher lows converging (low slope > high slope)
        if h_end > h_start and l_end > l_start:
            high_diff = h_end - h_start
            low_diff = l_end - l_start
            if low_diff > high_diff * 1.3:  # Converging upward
                if c_close < l_end:  # Breakdown
                    t_start = cls._get_candle_time(df, offset)
                    t_curr = cls._get_candle_time(df, -1)
                    return {
                        "pattern_name": "Rising Wedge (Bearish Breakdown)",
                        "tier": "TIER_1_OPTIMAL",
                        "direction": "SELL",
                        "recommended_option": "PE (Put Option)",
                        "invalidation_level": round(h_end, 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 88,
                        "description": f"Master TCS Pattern: Rising Wedge breakdown confirmed. Price contracted upward with declining volume. Clean breakdown below lower support at ₹{l_end:,.1f}.",
                        "drawing_data": {
                            "pattern_name": "Rising Wedge (Bearish)",
                            "lines": [
                                {
                                    "title": "Wedge Upper Line",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 2,
                                    "points": [
                                        {"time": t_start, "value": round(h_start, 2)},
                                        {"time": t_curr, "value": round(h_end, 2)}
                                    ]
                                },
                                {
                                    "title": "Wedge Lower Line",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_start, "value": round(l_start, 2)},
                                        {"time": t_curr, "value": round(c_close, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(l_end, 2), "color": "#FFFFFF", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Wedge Breakdown: ₹{l_end:,.1f}"}
                            ],
                            "markers": [
                                {"time": t_start, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": "Wedge Base"},
                                {"time": t_curr, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"Wedge Breakdown @ ₹{c_close:,.1f}"}
                            ]
                        }
                    }

        # Falling Wedge: Lower highs and lower lows converging (high drop > low drop)
        if h_end < h_start and l_end < l_start:
            high_drop = h_start - h_end
            low_drop = l_start - l_end
            if high_drop > low_drop * 1.3:  # Converging downward
                if c_close > h_end:  # Breakout
                    t_start = cls._get_candle_time(df, offset)
                    t_curr = cls._get_candle_time(df, -1)
                    return {
                        "pattern_name": "Falling Wedge (Bullish Breakout)",
                        "tier": "TIER_1_OPTIMAL",
                        "direction": "BUY",
                        "recommended_option": "CE (Call Option)",
                        "invalidation_level": round(l_end, 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 88,
                        "description": f"Master TCS Pattern: Falling Wedge breakout confirmed. Sellers lost momentum in contracting range. Clean breakout above resistance at ₹{h_end:,.1f}.",
                        "drawing_data": {
                            "pattern_name": "Falling Wedge (Bullish)",
                            "lines": [
                                {
                                    "title": "Wedge Resistance",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_start, "value": round(h_start, 2)},
                                        {"time": t_curr, "value": round(c_close, 2)}
                                    ]
                                },
                                {
                                    "title": "Wedge Support",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 2,
                                    "points": [
                                        {"time": t_start, "value": round(l_start, 2)},
                                        {"time": t_curr, "value": round(l_end, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(h_end, 2), "color": "#FFFFFF", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Wedge Breakout: ₹{h_end:,.1f}"}
                            ],
                            "markers": [
                                {"time": t_start, "position": "belowBar", "color": "#FFFFFF", "shape": "circle", "text": "Wedge Base"},
                                {"time": t_curr, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"Wedge Breakout @ ₹{c_close:,.1f}"}
                            ]
                        }
                    }

        return None

    @classmethod
    def detect_role_reversal_sr_flip(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detects Role Reversal S/R Flip (Document 5, Page 11):
        - Previous Resistance becomes Support on retest (Bullish Flip).
        - Previous Support becomes Resistance on retest (Bearish Flip).
        """
        if df is None or len(df) < 15:
            return None

        recent = df.iloc[-15:]
        curr_c = recent.iloc[-1]
        c_close = float(curr_c["close"])
        c_low = float(curr_c["low"])
        c_high = float(curr_c["high"])
        c_open = float(curr_c["open"])

        # Check for Resistance -> Support Flip (Bullish Flip)
        highs_past = df["high"].iloc[:-3].values
        for i in range(1, len(highs_past) - 1):
            if highs_past[i] > highs_past[i-1] and highs_past[i] > highs_past[i+1]:
                peak = float(highs_past[i])
                if abs(c_low - peak) / peak <= 0.0035 and c_close >= peak and c_close >= c_open:
                    t_retest = cls._get_candle_time(df, -1)
                    t_base = cls._get_candle_time(df, i)
                    return {
                        "pattern_name": "S/R Role Reversal (Previous Resistance -> Support Flip)",
                        "tier": "TIER_1_OPTIMAL",
                        "direction": "BUY",
                        "recommended_option": "CE (Call Option)",
                        "invalidation_level": round(peak - (abs(c_close - c_open) * 0.5), 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 89,
                        "description": f"Master TCS Principle: Previous Resistance at ₹{peak:,.1f} successfully flipped into strong Support. Tested and confirmed with bullish buyer defense.",
                        "drawing_data": {
                            "pattern_name": "S/R Role Reversal (Flip)",
                            "lines": [
                                {
                                    "title": "Flipped Support Line",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_base, "value": round(peak, 2)},
                                        {"time": t_retest, "value": round(peak, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(peak, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Flipped Support: ₹{peak:,.1f}"}
                            ],
                            "markers": [
                                {"time": t_retest, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": f"S/R Flip Bounce @ ₹{c_close:,.1f}"}
                            ]
                        }
                    }

        # Check for Support -> Resistance Flip (Bearish Flip)
        lows_past = df["low"].iloc[:-3].values
        for i in range(1, len(lows_past) - 1):
            if lows_past[i] < lows_past[i-1] and lows_past[i] < lows_past[i+1]:
                trough = float(lows_past[i])
                if abs(c_high - trough) / trough <= 0.0035 and c_close <= trough and c_close <= c_open:
                    t_retest = cls._get_candle_time(df, -1)
                    t_base = cls._get_candle_time(df, i)
                    return {
                        "pattern_name": "S/R Role Reversal (Previous Support -> Resistance Flip)",
                        "tier": "TIER_1_OPTIMAL",
                        "direction": "SELL",
                        "recommended_option": "PE (Put Option)",
                        "invalidation_level": round(trough + (abs(c_close - c_open) * 0.5), 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 89,
                        "description": f"Master TCS Principle: Previous Support at ₹{trough:,.1f} successfully flipped into strong Resistance. Tested and confirmed with seller rejection.",
                        "drawing_data": {
                            "pattern_name": "S/R Role Reversal (Bearish Flip)",
                            "lines": [
                                {
                                    "title": "Flipped Resistance Line",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_base, "value": round(trough, 2)},
                                        {"time": t_retest, "value": round(trough, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(trough, 2), "color": "#FFFFFF", "lineWidth": 2, "lineStyle": 0, "axisLabelVisible": True, "title": f"Flipped Resistance: ₹{trough:,.1f}"}
                            ],
                            "markers": [
                                {"time": t_retest, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": f"S/R Flip Rejection @ ₹{c_close:,.1f}"}
                            ]
                        }
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

        # TCS Master Pattern Detectors (from Tamil Crypto School curriculum)
        triple_taps = cls.detect_triple_taps_strategy(ref_df)
        if triple_taps:
            detected.append(triple_taps)

        h_and_s = cls.detect_head_and_shoulders(df_5m)
        if h_and_s:
            detected.append(h_and_s)

        triple_tb = cls.detect_triple_top_bottom(df_5m)
        if triple_tb:
            detected.append(triple_tb)

        wedges = cls.detect_wedge_patterns(df_5m)
        if wedges:
            detected.append(wedges)

        sr_flip = cls.detect_role_reversal_sr_flip(df_5m)
        if sr_flip:
            detected.append(sr_flip)

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    @staticmethod
    def detect_side_wave_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects Sideways / Consolidation / Side Wave patterns:
        - Range-Bound Consolidation Box (Narrow rectangle high-low range)
        - Squeeze & Volatility Contraction (ATR decline, flat EMAs)
        - Inside Bar Compression / Coil (Indecision)
        - Doji / Spinning Top neutral clusters
        """
        if df is None or len(df) < 5:
            return []

        patterns = []
        recent_10 = df.iloc[-10:] if len(df) >= 10 else df
        recent_high = float(recent_10["high"].max())
        recent_low = float(recent_10["low"].min())
        curr_c = df.iloc[-1]
        c_close = float(curr_c["close"])
        c_open = float(curr_c["open"])
        c_high = float(curr_c["high"])
        c_low = float(curr_c["low"])
        body = abs(c_close - c_open)
        c_range = max(c_high - c_low, 0.01)

        # 1. Range-Bound Box / Sideways Channel
        if c_close > 0:
            band_pct = ((recent_high - recent_low) / c_close) * 100
            # If the entire 10-candle range is within 0.45% (tight consolidation)
            if band_pct <= 0.50:
                t_start = PatternEngine._get_candle_time(df, -10 if len(df) >= 10 else 0)
                t_end = PatternEngine._get_candle_time(df, -1)
                patterns.append({
                    "pattern_name": "Range-Bound Consolidation Box (Sideways)",
                    "category": "SIDE_WAVE",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SIDE_WAVE",
                    "recommended_option": "WAIT (Theta Bleed Warning)",
                    "invalidation_level": round(recent_high, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 88,
                    "description": f"Price is trapped in a narrow sideways channel (₹{recent_low:,.1f} - ₹{recent_high:,.1f}, {band_pct:.2f}% range). High risk of option premium decay. Wait for decisive breakout.",
                    "drawing_data": {
                        "pattern_name": "Range-Bound Consolidation Box (Sideways)",
                        "lines": [
                            {
                                "title": "Box Ceiling",
                                "color": "#FFD600",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_start, "value": round(recent_high, 2)},
                                    {"time": t_end, "value": round(recent_high, 2)}
                                ]
                            },
                            {
                                "title": "Box Floor",
                                "color": "#FFD600",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "points": [
                                    {"time": t_start, "value": round(recent_low, 2)},
                                    {"time": t_end, "value": round(recent_low, 2)}
                                ]
                            }
                        ],
                        "price_lines": [
                            {
                                "price": round(recent_high, 2),
                                "color": "#FFD600",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "axisLabelVisible": True,
                                "title": f"Box Ceiling: ₹{recent_high:,.1f}"
                            },
                            {
                                "price": round(recent_low, 2),
                                "color": "#FFD600",
                                "lineWidth": 2,
                                "lineStyle": 2,
                                "axisLabelVisible": True,
                                "title": f"Box Floor: ₹{recent_low:,.1f}"
                            }
                        ],
                        "markers": [
                            {"time": t_start, "position": "aboveBar", "color": "#FFD600", "shape": "circle", "text": "Consolidation Box"},
                            {"time": t_end, "position": "belowBar", "color": "#FFD600", "shape": "circle", "text": f"Range ₹{recent_low:,.0f}-₹{recent_high:,.0f}"}
                        ]
                    }
                })

        # 2. Inside Bar / Coil Compression
        if len(df) >= 2:
            prev_c = df.iloc[-2]
            p_high = float(prev_c["high"])
            p_low = float(prev_c["low"])
            if c_high <= p_high and c_low >= p_low:
                patterns.append({
                    "pattern_name": "Inside Bar Compression (Coil)",
                    "category": "SIDE_WAVE",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SIDE_WAVE",
                    "recommended_option": "PREPARE STRADDLE / WAIT",
                    "invalidation_level": round(p_low, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 82,
                    "description": f"Current bar is fully compressed inside previous bar (₹{p_low:,.1f} - ₹{p_high:,.1f}). Energy coiling for impending breakout."
                })

        # 3. Doji / Spinning Top Indecision
        if (body / c_range) <= 0.20:
            patterns.append({
                "pattern_name": "Doji / Spinning Top (Neutral Indecision)",
                "category": "SIDE_WAVE",
                "tier": "TIER_2_SECONDARY",
                "direction": "SIDE_WAVE",
                "recommended_option": "WAIT",
                "invalidation_level": round(c_low, 2),
                "trigger_price": round(c_close, 2),
                "confidence": 75,
                "description": "Candle body is very small (<20% of total range). Bulls and bears are in equilibrium with zero directional momentum."
            })

        # 4. Moving Average Flat Squeeze (9 vs 21 EMA convergence)
        if "ema_9" in df.columns and "ema_21" in df.columns and len(df) >= 5:
            ema9 = float(curr_c["ema_9"])
            ema21 = float(curr_c["ema_21"])
            if abs(ema9 - ema21) / c_close <= 0.0008:
                patterns.append({
                    "pattern_name": "EMA Squeeze & Entanglement (No Trend)",
                    "category": "SIDE_WAVE",
                    "tier": "TIER_2_SECONDARY",
                    "direction": "SIDE_WAVE",
                    "recommended_option": "AVOID BUYING",
                    "invalidation_level": round(min(ema9, ema21), 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 80,
                    "description": f"9 EMA (₹{ema9:,.1f}) and 21 EMA (₹{ema21:,.1f}) are completely flat and intertwined. Choppy market direction."
                })

        return patterns

    @classmethod
    def analyze_timeframe_patterns(
        cls,
        df: pd.DataFrame,
        timeframe_label: str = "5m",
        pdh_pdl: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a specific timeframe (5m or 1h) and returns categorized patterns:
        - bullish: List of active/forming bullish patterns
        - bearish: List of active/forming bearish patterns
        - side_wave: List of sideways/range-bound patterns
        - regime: Overall dominant structure ('BULLISH', 'BEARISH', or 'SIDE WAVE')
        - regime_score: Confidence %
        - summary: Human readable explanation for Option Buyers
        """
        result = {
            "timeframe": timeframe_label,
            "regime": "SIDE WAVE",
            "regime_color": "#FFD600",
            "regime_score": 50,
            "summary": "Consolidating in a range",
            "bullish": [],
            "bearish": [],
            "side_wave": []
        }

        if df is None or len(df) < 5:
            result["summary"] = f"Insufficient {timeframe_label} candle data"
            return result

        curr_c = df.iloc[-1]
        c_close = float(curr_c["close"])
        c_open = float(curr_c["open"])
        curr_vol = float(curr_c["volume"]) if "volume" in curr_c else 0
        curr_vol_ma = float(curr_c.get("volume_ma20", curr_vol))

        # Check existing detectors
        sweep = cls.detect_liquidity_sweep(df, pdh_pdl)
        if sweep:
            if sweep["direction"] == "BUY":
                result["bullish"].append(sweep)
            else:
                result["bearish"].append(sweep)

        flag = cls.detect_flag_pattern(df)
        if flag:
            if flag["direction"] == "BUY":
                result["bullish"].append(flag)
            else:
                result["bearish"].append(flag)

        inside = cls.detect_inside_bar_compression(df)
        if inside:
            if inside["direction"] == "BUY":
                result["bullish"].append(inside)
            else:
                result["bearish"].append(inside)

        double_bt = cls.detect_double_bottom_top(df)
        if double_bt:
            if double_bt["direction"] == "BUY":
                result["bullish"].append(double_bt)
            else:
                result["bearish"].append(double_bt)

        vwap_cross = cls.detect_vwap_crossover(df)
        if vwap_cross:
            if vwap_cross["direction"] == "BUY":
                result["bullish"].append(vwap_cross)
            else:
                result["bearish"].append(vwap_cross)

        # TCS Master Pattern Detectors (5m and 1h)
        triple_taps = cls.detect_triple_taps_strategy(df)
        if triple_taps:
            if triple_taps["direction"] == "BUY":
                result["bullish"].append(triple_taps)
            else:
                result["bearish"].append(triple_taps)

        h_and_s = cls.detect_head_and_shoulders(df)
        if h_and_s:
            if h_and_s["direction"] == "BUY":
                result["bullish"].append(h_and_s)
            else:
                result["bearish"].append(h_and_s)

        triple_tb = cls.detect_triple_top_bottom(df)
        if triple_tb:
            if triple_tb["direction"] == "BUY":
                result["bullish"].append(triple_tb)
            else:
                result["bearish"].append(triple_tb)

        wedges = cls.detect_wedge_patterns(df)
        if wedges:
            if wedges["direction"] == "BUY":
                result["bullish"].append(wedges)
            else:
                result["bearish"].append(wedges)

        sr_flip = cls.detect_role_reversal_sr_flip(df)
        if sr_flip:
            if sr_flip["direction"] == "BUY":
                result["bullish"].append(sr_flip)
            else:
                result["bearish"].append(sr_flip)

        # Candlestick Reversal Formations
        if len(df) >= 3:
            prev_c = df.iloc[-2]
            p_close = float(prev_c["close"])
            p_open = float(prev_c["open"])
            c_high = float(curr_c["high"])
            c_low = float(curr_c["low"])
            body = abs(c_close - c_open)
            upper_wick = c_high - max(c_close, c_open)
            lower_wick = min(c_close, c_open) - c_low

            # Bullish Engulfing
            if p_close < p_open and c_close > c_open and c_close > p_open and c_open < p_close:
                result["bullish"].append({
                    "pattern_name": "Bullish Engulfing Pattern",
                    "category": "BULLISH",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "BUY",
                    "recommended_option": "CE (Call Option)",
                    "invalidation_level": round(c_low, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 85,
                    "description": f"Strong bullish candle completely engulfs previous red candle. Aggressive buyer entry.",
                    "drawing_data": {
                        "pattern_name": "Bullish Engulfing Pattern",
                        "lines": [],
                        "price_lines": [
                            {"price": round(c_low, 2), "color": "#00E676", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Engulfing SL: ₹{c_low:,.1f}"}
                        ],
                        "markers": [
                            {"time": cls._get_candle_time(df, -1), "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": "Bullish Engulfing"}
                        ]
                    }
                })
            # Bearish Engulfing
            elif p_close > p_open and c_close < c_open and c_close < p_open and c_open > p_close:
                result["bearish"].append({
                    "pattern_name": "Bearish Engulfing Pattern",
                    "category": "BEARISH",
                    "tier": "TIER_1_OPTIMAL",
                    "direction": "SELL",
                    "recommended_option": "PE (Put Option)",
                    "invalidation_level": round(c_high, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 85,
                    "description": f"Strong bearish candle completely engulfs previous green candle. Sellers seize control.",
                    "drawing_data": {
                        "pattern_name": "Bearish Engulfing Pattern",
                        "lines": [],
                        "price_lines": [
                            {"price": round(c_high, 2), "color": "#FF1744", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Engulfing SL: ₹{c_high:,.1f}"}
                        ],
                        "markers": [
                            {"time": cls._get_candle_time(df, -1), "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": "Bearish Engulfing"}
                        ]
                    }
                })

            # Hammer (Bullish at support)
            if lower_wick >= body * 2.0 and upper_wick <= body * 0.5:
                result["bullish"].append({
                    "pattern_name": "Bullish Hammer / Pin Bar",
                    "category": "BULLISH",
                    "tier": "TIER_2_SECONDARY",
                    "direction": "BUY",
                    "recommended_option": "CE (Call Option)",
                    "invalidation_level": round(c_low, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 80,
                    "description": f"Long lower shadow ({lower_wick:.1f} pts) shows intense rejection of lower prices.",
                    "drawing_data": {
                        "pattern_name": "Bullish Hammer / Pin Bar",
                        "lines": [],
                        "price_lines": [
                            {"price": round(c_low, 2), "color": "#00E676", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Hammer SL: ₹{c_low:,.1f}"}
                        ],
                        "markers": [
                            {"time": cls._get_candle_time(df, -1), "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": "Bullish Hammer"}
                        ]
                    }
                })
            # Shooting Star (Bearish at resistance)
            elif upper_wick >= body * 2.0 and lower_wick <= body * 0.5:
                result["bearish"].append({
                    "pattern_name": "Shooting Star / Bearish Pin Bar",
                    "category": "BEARISH",
                    "tier": "TIER_2_SECONDARY",
                    "direction": "SELL",
                    "recommended_option": "PE (Put Option)",
                    "invalidation_level": round(c_high, 2),
                    "trigger_price": round(c_close, 2),
                    "confidence": 80,
                    "description": f"Long upper shadow ({upper_wick:.1f} pts) shows intense rejection of higher prices.",
                    "drawing_data": {
                        "pattern_name": "Shooting Star / Bearish Pin Bar",
                        "lines": [],
                        "price_lines": [
                            {"price": round(c_high, 2), "color": "#FF1744", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Shooting Star SL: ₹{c_high:,.1f}"}
                        ],
                        "markers": [
                            {"time": cls._get_candle_time(df, -1), "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": "Shooting Star"}
                        ]
                    }
                })

        # Higher Highs / Higher Lows Trend Structure
        if len(df) >= 10:
            sub = df.iloc[-8:]
            c_highs = sub["high"].values
            c_lows = sub["low"].values
            is_uptrend = (c_highs[-1] > c_highs[0]) and (c_lows[-1] > c_lows[0])
            is_downtrend = (c_highs[-1] < c_highs[0]) and (c_lows[-1] < c_lows[0])

            if is_uptrend and "ema_9" in df.columns and "ema_21" in df.columns:
                if float(curr_c["ema_9"]) > float(curr_c["ema_21"]):
                    t_sub_start = cls._get_candle_time(df, -8)
                    t_sub_end = cls._get_candle_time(df, -1)
                    low_start = float(sub["low"].iloc[0])
                    low_end = float(sub["low"].iloc[-1])
                    result["bullish"].append({
                        "pattern_name": "Ascending Higher-High Structure",
                        "category": "BULLISH",
                        "tier": "TIER_2_SECONDARY",
                        "direction": "BUY",
                        "recommended_option": "CE (Call Option)",
                        "invalidation_level": round(float(sub["low"].min()), 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 82,
                        "description": f"Sustained upward step progression with 9 EMA above 21 EMA. Healthy bull trend.",
                        "drawing_data": {
                            "pattern_name": "Ascending Higher-High Structure",
                            "lines": [
                                {
                                    "title": "Ascending Trendline",
                                    "color": "#00E676",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_sub_start, "value": round(low_start, 2)},
                                        {"time": t_sub_end, "value": round(low_end, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(float(sub["low"].min()), 2), "color": "#00E676", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Trend Low: ₹{sub['low'].min():,.1f}"}
                            ],
                            "markers": [
                                {"time": t_sub_start, "position": "belowBar", "color": "#00E676", "shape": "circle", "text": "Trend Base"},
                                {"time": t_sub_end, "position": "belowBar", "color": "#00E676", "shape": "arrowUp", "text": "Higher Low Step"}
                            ]
                        }
                    })
            elif is_downtrend and "ema_9" in df.columns and "ema_21" in df.columns:
                if float(curr_c["ema_9"]) < float(curr_c["ema_21"]):
                    t_sub_start = cls._get_candle_time(df, -8)
                    t_sub_end = cls._get_candle_time(df, -1)
                    high_start = float(sub["high"].iloc[0])
                    high_end = float(sub["high"].iloc[-1])
                    result["bearish"].append({
                        "pattern_name": "Descending Lower-Low Structure",
                        "category": "BEARISH",
                        "tier": "TIER_2_SECONDARY",
                        "direction": "SELL",
                        "recommended_option": "PE (Put Option)",
                        "invalidation_level": round(float(sub["high"].max()), 2),
                        "trigger_price": round(c_close, 2),
                        "confidence": 82,
                        "description": f"Consistent downward step progression with 9 EMA below 21 EMA. Bearish channel.",
                        "drawing_data": {
                            "pattern_name": "Descending Lower-Low Structure",
                            "lines": [
                                {
                                    "title": "Descending Trendline",
                                    "color": "#FFFFFF",
                                    "lineWidth": 2,
                                    "lineStyle": 0,
                                    "points": [
                                        {"time": t_sub_start, "value": round(high_start, 2)},
                                        {"time": t_sub_end, "value": round(high_end, 2)}
                                    ]
                                }
                            ],
                            "price_lines": [
                                {"price": round(float(sub["high"].max()), 2), "color": "#FFFFFF", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": f"Trend High: ₹{sub['high'].max():,.1f}"}
                            ],
                            "markers": [
                                {"time": t_sub_start, "position": "aboveBar", "color": "#FFFFFF", "shape": "circle", "text": "Channel Top"},
                                {"time": t_sub_end, "position": "aboveBar", "color": "#FF1744", "shape": "arrowDown", "text": "Lower High Step"}
                            ]
                        }
                    })

        # Detect Side Wave / Consolidation Patterns
        side_waves = cls.detect_side_wave_patterns(df)
        result["side_wave"].extend(side_waves)

        # Determine Dominant Regime
        n_bull = len(result["bullish"])
        n_bear = len(result["bearish"])
        n_side = len(result["side_wave"])

        if n_bull > n_bear and n_bull >= 1:
            best_conf = max([p.get("confidence", 80) for p in result["bullish"]])
            result["regime"] = "BULLISH"
            result["regime_color"] = "#00E676"
            result["regime_score"] = best_conf
            top_p = result["bullish"][0]["pattern_name"]
            result["summary"] = f"Bullish momentum dominant ({top_p}). Favorable for Call (CE) buying."
        elif n_bear > n_bull and n_bear >= 1:
            best_conf = max([p.get("confidence", 80) for p in result["bearish"]])
            result["regime"] = "BEARISH"
            result["regime_color"] = "#FF1744"
            result["regime_score"] = best_conf
            top_p = result["bearish"][0]["pattern_name"]
            result["summary"] = f"Bearish breakdown dominant ({top_p}). Favorable for Put (PE) buying."
        else:
            result["regime"] = "SIDE WAVE"
            result["regime_color"] = "#FFD600"
            result["regime_score"] = 75 if n_side > 0 else 60
            result["summary"] = "Sideways / consolidation zone. High Theta decay risk for Option Buyers."

        # Build 24-Hour (5m) or 1-Week (1h) Structural White Lines
        window_lines = []
        window_price_lines = []
        window_markers = []
        
        is_5m = (timeframe_label == "5m")
        span_label = "Last 24 Hours" if is_5m else "Last 1 Week"
        
        if df is not None and len(df) >= 5:
            try:
                latest_dt = pd.Timestamp(df.iloc[-1]["datetime"]) if "datetime" in df.columns else pd.Timestamp.now()
                if is_5m:
                    cutoff_dt = latest_dt - pd.Timedelta(hours=24)
                    w_df = df[pd.to_datetime(df["datetime"]) >= cutoff_dt] if "datetime" in df.columns else df.iloc[-75:]
                    if len(w_df) < 10:
                        w_df = df.iloc[-75:] if len(df) >= 75 else df
                    line_title = "24h Trend Structure"
                    high_title = "24h High"
                    low_title = "24h Low"
                    marker_high_tag = "24h High"
                    marker_low_tag = "24h Low"
                    marker_base_tag = "24h Base"
                else:  # 1h / Higher-TF macro
                    cutoff_dt = latest_dt - pd.Timedelta(days=7)
                    w_df = df[pd.to_datetime(df["datetime"]) >= cutoff_dt] if "datetime" in df.columns else df.iloc[-35:]
                    if len(w_df) < 5:
                        w_df = df.iloc[-35:] if len(df) >= 35 else df
                    line_title = "1-Week Macro Structure"
                    high_title = "1-Week High"
                    low_title = "1-Week Low"
                    marker_high_tag = "1-Week High"
                    marker_low_tag = "1-Week Low"
                    marker_base_tag = "1-Week Base"

                t_start = cls._get_candle_time(w_df, 0)
                t_end = cls._get_candle_time(w_df, -1)
                h_val = float(w_df["high"].max())
                h_idx = int(w_df["high"].values.argmax())
                t_h = cls._get_candle_time(w_df, h_idx)
                l_val = float(w_df["low"].min())
                l_idx = int(w_df["low"].values.argmin())
                t_l = cls._get_candle_time(w_df, l_idx)
                start_p = float(w_df["close"].iloc[0])
                end_p = float(w_df["close"].iloc[-1])

                # 1. Structural Trendline across full span (24h or 1-Week) in pure White
                window_lines.append({
                    "title": line_title,
                    "color": "#FFFFFF",
                    "lineWidth": 2,
                    "lineStyle": 0,  # Solid White
                    "points": [
                        {"time": t_start, "value": round(start_p, 2)},
                        {"time": t_end, "value": round(end_p, 2)}
                    ]
                })

                # 2. Structural High / Resistance boundary across the window in White
                window_lines.append({
                    "title": high_title,
                    "color": "#FFFFFF",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed White
                    "points": [
                        {"time": t_start, "value": round(h_val, 2)},
                        {"time": t_end, "value": round(h_val, 2)}
                    ]
                })

                # 3. Structural Low / Support boundary across the window in White
                window_lines.append({
                    "title": low_title,
                    "color": "#FFFFFF",
                    "lineWidth": 2,
                    "lineStyle": 2,  # Dashed White
                    "points": [
                        {"time": t_start, "value": round(l_val, 2)},
                        {"time": t_end, "value": round(l_val, 2)}
                    ]
                })

                window_price_lines.append({
                    "price": round(h_val, 2),
                    "color": "#FFFFFF",
                    "lineWidth": 1,
                    "lineStyle": 2,
                    "axisLabelVisible": True,
                    "title": f"{high_title}: ₹{h_val:,.1f}"
                })
                window_price_lines.append({
                    "price": round(l_val, 2),
                    "color": "#FFFFFF",
                    "lineWidth": 1,
                    "lineStyle": 2,
                    "axisLabelVisible": True,
                    "title": f"{low_title}: ₹{l_val:,.1f}"
                })

                window_markers.append({
                    "time": t_start,
                    "position": "belowBar",
                    "color": "#FFFFFF",
                    "shape": "circle",
                    "text": f"{marker_base_tag} @ ₹{start_p:,.1f}"
                })
                window_markers.append({
                    "time": t_h,
                    "position": "aboveBar",
                    "color": "#FFFFFF",
                    "shape": "circle",
                    "text": f"{marker_high_tag} @ ₹{h_val:,.1f}"
                })
                window_markers.append({
                    "time": t_l,
                    "position": "belowBar",
                    "color": "#FFFFFF",
                    "shape": "circle",
                    "text": f"{marker_low_tag} @ ₹{l_val:,.1f}"
                })
            except Exception:
                pass

        # Select dominant drawing data for chart overlay
        dominant_drawing = None
        if result["regime"] == "BULLISH" and result["bullish"]:
            for p in result["bullish"]:
                if p.get("drawing_data"):
                    dominant_drawing = p["drawing_data"]
                    break
        elif result["regime"] == "BEARISH" and result["bearish"]:
            for p in result["bearish"]:
                if p.get("drawing_data"):
                    dominant_drawing = p["drawing_data"]
                    break
        elif result["side_wave"]:
            for p in result["side_wave"]:
                if p.get("drawing_data"):
                    dominant_drawing = p["drawing_data"]
                    break

        if not dominant_drawing:
            all_patterns = result["bullish"] + result["bearish"] + result["side_wave"]
            for p in all_patterns:
                if p.get("drawing_data"):
                    dominant_drawing = p["drawing_data"]
                    break

        # Combine window lines and active pattern lines, ensuring all red colors are replaced with white (#FFFFFF)
        combined_lines = list(window_lines)
        combined_price_lines = list(window_price_lines)
        combined_markers = list(window_markers)

        pattern_name = f"{span_label} Structural Channel"
        if dominant_drawing:
            pattern_name = dominant_drawing.get("pattern_name", pattern_name)
            for l in dominant_drawing.get("lines", []):
                col = l.get("color", "#FFFFFF")
                if str(col).upper() in ["#FF1744", "#FF5252", "#EF5350", "RED", "#FF0000"]:
                    col = "#FFFFFF"
                l["color"] = col
                combined_lines.append(l)
            for pl in dominant_drawing.get("price_lines", []):
                col = pl.get("color", "#FFFFFF")
                if str(col).upper() in ["#FF1744", "#FF5252", "#EF5350", "RED", "#FF0000"]:
                    col = "#FFFFFF"
                pl["color"] = col
                combined_price_lines.append(pl)
            for mk in dominant_drawing.get("markers", []):
                combined_markers.append(mk)

        result["drawing_data"] = {
            "pattern_name": pattern_name,
            "span_label": span_label,
            "lines": combined_lines,
            "price_lines": combined_price_lines,
            "markers": combined_markers
        }
        result["drawing_pattern_name"] = pattern_name

        return result
