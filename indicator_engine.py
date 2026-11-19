"""
Technical indicator computation engine.
Calculates VWAP, EMAs, Supertrend, ATR, RSI, Volume MA, and Bollinger Bands with high performance.
"""
import pandas as pd
import numpy as np


class IndicatorEngine:
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
        """Exponential Moving Average."""
        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
        """Simple Moving Average."""
        return df[column].rolling(window=period).mean()

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range (ATR)."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        return atr.fillna(tr.rolling(window=period).mean()).fillna(tr)

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
        """Relative Strength Index (RSI)."""
        delta = df[column].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculates 20-period moving average of volume for breakout confirmation."""
        if "volume" not in df.columns:
            return pd.Series([0.0] * len(df), index=df.index)
        return df["volume"].rolling(window=period, min_periods=1).mean()

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates intraday VWAP that resets every market day.
        Also computes +1 and -1 standard deviation bands.
        Handles zero-volume index spot feeds gracefully by using price-range proxy.
        """
        res = df.copy()
        typical_price = (res["high"] + res["low"] + res["close"]) / 3.0

        # If volume is zero across the dataset (common for index tickers), use price range as activity weight
        if "volume" not in res.columns or res["volume"].sum() == 0:
            res["volume"] = ((res["high"] - res["low"]).abs() + (res["close"] * 0.0005)) * 1000.0

        res["pv"] = typical_price * res["volume"]
        
        # Group by date if datetime column is present
        if "datetime" in res.columns:
            res["date"] = pd.to_datetime(res["datetime"]).dt.date
            res["cum_pv"] = res.groupby("date")["pv"].cumsum()
            res["cum_vol"] = res.groupby("date")["volume"].cumsum()
            res["vwap"] = res["cum_pv"] / (res["cum_vol"] + 1e-10)
            
            # VWAP Variance and standard deviation
            res["dev_sq"] = ((typical_price - res["vwap"]) ** 2) * res["volume"]
            res["cum_dev_sq"] = res.groupby("date")["dev_sq"].cumsum()
            res["vwap_std"] = np.sqrt(res["cum_dev_sq"] / (res["cum_vol"] + 1e-10))
            res["vwap_upper"] = res["vwap"] + res["vwap_std"]
            res["vwap_lower"] = res["vwap"] - res["vwap_std"]
            res.drop(columns=["pv", "dev_sq", "cum_pv", "cum_vol", "cum_dev_sq", "date"], errors="ignore", inplace=True)
        else:
            cum_pv = res["pv"].cumsum()
            cum_vol = res["volume"].cumsum()
            res["vwap"] = cum_pv / (cum_vol + 1e-10)
            res["vwap_upper"] = res["vwap"] * 1.002
            res["vwap_lower"] = res["vwap"] * 0.998
            res.drop(columns=["pv"], errors="ignore", inplace=True)
            
        # Ensure no remaining zero VWAP values
        res["vwap"] = res["vwap"].replace(0, np.nan).fillna(typical_price)
        return res

    @staticmethod
    def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """
        Computes the Supertrend indicator.
        Returns DataFrame with 'supertrend' and 'supertrend_dir' (1 for Bullish, -1 for Bearish).
        """
        res = df.copy()
        atr = IndicatorEngine.calculate_atr(res, period)
        hl2 = (res["high"] + res["low"]) / 2.0
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = [0.0] * len(res)
        direction = [1] * len(res)
        
        for i in range(1, len(res)):
            curr_close = res["close"].iloc[i]
            prev_close = res["close"].iloc[i-1]
            prev_upper = upper_band.iloc[i-1]
            prev_lower = lower_band.iloc[i-1]
            
            # Lower band adjustment
            if curr_close > prev_lower or prev_close < prev_lower:
                lower_band.iloc[i] = max(lower_band.iloc[i], prev_lower)
            
            # Upper band adjustment
            if curr_close < prev_upper or prev_close > prev_upper:
                upper_band.iloc[i] = min(upper_band.iloc[i], prev_upper)
                
            # Direction switch
            if curr_close > prev_upper:
                direction[i] = 1
            elif curr_close < prev_lower:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
                
            supertrend[i] = lower_band.iloc[i] if direction[i] == 1 else upper_band.iloc[i]
            
        res["supertrend"] = supertrend
        res["supertrend_dir"] = direction
        res["st_upper"] = upper_band
        res["st_lower"] = lower_band
        return res

    @classmethod
    def apply_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Applies all standard indicators to an OHLCV dataframe."""
        if df.empty:
            return df
        res = df.copy()

        # If volume is zero across the dataset (common for index tickers), synthesize volume from price volatility
        if "volume" not in res.columns or res["volume"].sum() == 0:
            res["volume"] = ((res["high"] - res["low"]).abs() + (res["close"] * 0.0005)) * 1000.0

        res["ema_9"] = cls.calculate_ema(res, 9)
        res["ema_21"] = cls.calculate_ema(res, 21)
        res["ema_50"] = cls.calculate_ema(res, 50)
        res["ema_200"] = cls.calculate_ema(res, 200)
        res["atr"] = cls.calculate_atr(res, 14)
        res["rsi"] = cls.calculate_rsi(res, 14)
        res["volume_ma20"] = cls.calculate_volume_ma(res, 20)
        
        # Apply VWAP
        res = cls.calculate_vwap(res)
        
        # Apply Supertrend
        res = cls.calculate_supertrend(res, period=10, multiplier=3.0)
        
        return res
