"""
Automated Level Detector:
Calculates Support & Resistance zones, CPR, PDH/PDL, Today's Open,
and Smart Money Concepts (Fair Value Gaps, Order Blocks).
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple


class LevelDetector:
    @staticmethod
    def calculate_cpr_and_pivots(daily_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate Central Pivot Range (CPR) and Classic Floor Pivots from daily candle.
        """
        if daily_df.empty or len(daily_df) < 1:
            return {}
        
        # Use previous day's data
        prev_candle = daily_df.iloc[-2] if len(daily_df) >= 2 else daily_df.iloc[-1]
        high = float(prev_candle["high"])
        low = float(prev_candle["low"])
        close = float(prev_candle["close"])
        
        pivot = (high + low + close) / 3.0
        bc = (high + low) / 2.0
        tc = (pivot - bc) + pivot
        
        # Ensure tc and bc orientation
        tc_val = max(tc, bc)
        bc_val = min(tc, bc)
        cpr_width_pct = ((tc_val - bc_val) / pivot) * 100.0
        
        # Classic Pivots
        r1 = (2.0 * pivot) - low
        s1 = (2.0 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2.0 * (pivot - low)
        s3 = low - 2.0 * (high - pivot)
        
        # CPR width category
        if cpr_width_pct < 0.25:
            cpr_type = "Narrow CPR (High Trend Potential)"
        elif cpr_width_pct > 0.65:
            cpr_type = "Wide CPR (Range-Bound / Mean-Reversion)"
        else:
            cpr_type = "Average CPR (Normal Volatility)"
            
        return {
            "pivot": round(pivot, 2),
            "tc": round(tc_val, 2),
            "bc": round(bc_val, 2),
            "cpr_width_pct": round(cpr_width_pct, 3),
            "cpr_type": cpr_type,
            "r1": round(r1, 2),
            "s1": round(s1, 2),
            "r2": round(r2, 2),
            "s2": round(s2, 2),
            "r3": round(r3, 2),
            "s3": round(s3, 2)
        }

    @staticmethod
    def get_pdh_pdl_open(df: pd.DataFrame) -> Dict[str, float]:
        """Extract Previous Day High, Low, and Current Day Open."""
        if df.empty:
            return {}
        
        res = df.copy()
        if "datetime" not in res.columns:
            return {
                "pdh": round(res["high"].max(), 2),
                "pdl": round(res["low"].min(), 2),
                "today_open": round(res["open"].iloc[0], 2)
            }
            
        res["date"] = pd.to_datetime(res["datetime"]).dt.date
        unique_dates = res["date"].unique()
        
        if len(unique_dates) >= 2:
            prev_date = unique_dates[-2]
            curr_date = unique_dates[-1]
            prev_day_data = res[res["date"] == prev_date]
            curr_day_data = res[res["date"] == curr_date]
            
            pdh = float(prev_day_data["high"].max())
            pdl = float(prev_day_data["low"].min())
            pdc = float(prev_day_data["close"].iloc[-1])
            today_open = float(curr_day_data["open"].iloc[0]) if not curr_day_data.empty else float(res["open"].iloc[-1])
            
            return {
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "pdc": round(pdc, 2),
                "today_open": round(today_open, 2)
            }
        else:
            return {
                "pdh": round(float(res["high"].max()), 2),
                "pdl": round(float(res["low"].min()), 2),
                "pdc": round(float(res["close"].iloc[0]), 2),
                "today_open": round(float(res["open"].iloc[0]), 2)
            }

    @staticmethod
    def detect_support_resistance_zones(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 0.25) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects fractal peaks & valleys and clusters them into high-probability
        Support and Resistance price bands.
        """
        if df.empty or len(df) < window * 2 + 1:
            return {"supports": [], "resistances": []}
            
        current_price = float(df["close"].iloc[-1])
        highs = df["high"].values
        lows = df["low"].values
        
        peak_levels = []
        valley_levels = []
        
        # Fractal peaks (resistances) & valleys (supports)
        for i in range(window, len(df) - window):
            # Peak: higher than surrounding bars
            if all(highs[i] >= highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                peak_levels.append(highs[i])
                
            # Valley: lower than surrounding bars
            if all(lows[i] <= lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                valley_levels.append(lows[i])
                
        def cluster_levels(levels: List[float], is_resistance: bool) -> List[Dict[str, Any]]:
            if not levels:
                return []
            levels = sorted(levels)
            clusters = []
            curr_cluster = [levels[0]]
            
            for lvl in levels[1:]:
                # If level is within tolerance_pct of cluster median
                median = np.median(curr_cluster)
                if abs(lvl - median) / median * 100.0 <= tolerance_pct:
                    curr_cluster.append(lvl)
                else:
                    clusters.append(curr_cluster)
                    curr_cluster = [lvl]
            if curr_cluster:
                clusters.append(curr_cluster)
                
            results = []
            for cluster in clusters:
                avg_price = float(np.mean(cluster))
                strength = len(cluster)
                # Filter by relationship to current price
                if is_resistance and avg_price > current_price:
                    results.append({
                        "level": round(avg_price, 2),
                        "min_price": round(min(cluster), 2),
                        "max_price": round(max(cluster), 2),
                        "touches": strength,
                        "type": "RESISTANCE"
                    })
                elif not is_resistance and avg_price < current_price:
                    results.append({
                        "level": round(avg_price, 2),
                        "min_price": round(min(cluster), 2),
                        "max_price": round(max(cluster), 2),
                        "touches": strength,
                        "type": "SUPPORT"
                    })
            # Sort resistances ascending (closest to price first) and supports descending (closest first)
            if is_resistance:
                results.sort(key=lambda x: x["level"])
            else:
                results.sort(key=lambda x: x["level"], reverse=True)
            return results[:4]  # Return top 4 most immediate levels
            
        return {
            "resistances": cluster_levels(peak_levels, is_resistance=True),
            "supports": cluster_levels(valley_levels, is_resistance=False)
        }

    @staticmethod
    def detect_fair_value_gaps(df: pd.DataFrame, min_gap_pct: float = 0.05) -> List[Dict[str, Any]]:
        """
        Detects Smart Money Concept (SMC) Fair Value Gaps (FVG) across recent candles.
        """
        if df.empty or len(df) < 5:
            return []
            
        fvgs = []
        # Inspect recent 60 candles
        start_idx = max(2, len(df) - 60)
        for i in range(start_idx, len(df)):
            c1_high = df["high"].iloc[i-2]
            c1_low = df["low"].iloc[i-2]
            c3_high = df["high"].iloc[i]
            c3_low = df["low"].iloc[i]
            curr_c = df["close"].iloc[i-1]
            
            # Bullish FVG: Candle 3 Low > Candle 1 High
            if c3_low > c1_high:
                gap_size = c3_low - c1_high
                gap_pct = (gap_size / curr_c) * 100.0
                if gap_pct >= min_gap_pct:
                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "top": round(float(c3_low), 2),
                        "bottom": round(float(c1_high), 2),
                        "index": i - 1,
                        "time": df["datetime"].iloc[i-1] if "datetime" in df.columns else i - 1
                    })
            # Bearish FVG: Candle 3 High < Candle 1 Low
            elif c3_high < c1_low:
                gap_size = c1_low - c3_high
                gap_pct = (gap_size / curr_c) * 100.0
                if gap_pct >= min_gap_pct:
                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "top": round(float(c1_low), 2),
                        "bottom": round(float(c3_high), 2),
                        "index": i - 1,
                        "time": df["datetime"].iloc[i-1] if "datetime" in df.columns else i - 1
                    })
        return fvgs[-4:]  # Return most recent 4 FVGs

    @staticmethod
    def detect_order_blocks(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects Bullish and Bearish Order Blocks (OB).
        """
        if df.empty or len(df) < 10:
            return []
            
        obs = []
        start_idx = max(3, len(df) - 40)
        for i in range(start_idx, len(df) - 1):
            prev_candle = df.iloc[i-1]
            curr_candle = df.iloc[i]
            next_candle = df.iloc[i+1]
            
            # Bullish Order Block: Down candle followed by aggressive displacement upward
            if prev_candle["close"] < prev_candle["open"]:
                body_prev = abs(prev_candle["close"] - prev_candle["open"])
                displacement = next_candle["close"] - curr_candle["open"]
                if displacement > body_prev * 1.8 and next_candle["close"] > prev_candle["high"]:
                    obs.append({
                        "type": "BULLISH_OB",
                        "top": round(float(prev_candle["high"]), 2),
                        "bottom": round(float(prev_candle["low"]), 2),
                        "time": prev_candle["datetime"] if "datetime" in df.columns else i - 1
                    })
            # Bearish Order Block: Up candle followed by aggressive displacement downward
            elif prev_candle["close"] > prev_candle["open"]:
                body_prev = abs(prev_candle["close"] - prev_candle["open"])
                displacement = curr_candle["open"] - next_candle["close"]
                if displacement > body_prev * 1.8 and next_candle["close"] < prev_candle["low"]:
                    obs.append({
                        "type": "BEARISH_OB",
                        "top": round(float(prev_candle["high"]), 2),
                        "bottom": round(float(prev_candle["low"]), 2),
                        "time": prev_candle["datetime"] if "datetime" in df.columns else i - 1
                    })
        return obs[-3:]
