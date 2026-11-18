"""
Angel One Token & Option Scrip Manager.
Downloads, caches, and parses NFO index options (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY)
to resolve exact active weekly/monthly option contract tokens (e.g. NIFTY23NOV2625200CE -> 64451).
"""
import os
import json
import requests
import datetime
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger("TokenManager")

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
NFO_CACHE_FILE = CACHE_DIR / "nfo_active_tokens.json"
SCRIP_MASTER_FILE = CACHE_DIR / "OpenAPIScripMaster.json"
SCRIP_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"

TARGET_INDICES = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}


class TokenManager:
    _instance = None
    _df_tokens = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TokenManager()
        return cls._instance

    def __init__(self):
        self.load_scrip_master()

    def download_and_filter_nfo_scrips(self, force: bool = False) -> bool:
        """Download latest scrip master JSON from Angel One and filter compact NFO table."""
        try:
            if not force and NFO_CACHE_FILE.exists():
                if NFO_CACHE_FILE.stat().st_size > 100 * 1024:
                    return True

            logger.info("Downloading Angel One Scrip Master JSON...")
            resp = requests.get(SCRIP_MASTER_URL, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                nfo_filtered = []
                for item in data:
                    if item.get("exch_seg") == "NFO" and item.get("name") in TARGET_INDICES:
                        nfo_filtered.append({
                            "token": str(item.get("token")),
                            "symbol": str(item.get("symbol")),
                            "name": str(item.get("name")),
                            "expiry": str(item.get("expiry")),
                            "strike": float(item.get("strike", 0)),
                            "lotsize": item.get("lotsize")
                        })
                with open(NFO_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(nfo_filtered, f)
                logger.info(f"Cached {len(nfo_filtered)} active NFO contracts to {NFO_CACHE_FILE}")
                return True
        except Exception as e:
            logger.warning(f"Could not download Scrip Master: {e}")
        return False

    def load_scrip_master(self):
        """Loads compact NFO active scrip cache into Pandas DataFrame."""
        if self._df_tokens is not None and not self._df_tokens.empty:
            return

        if not NFO_CACHE_FILE.exists():
            self.download_and_filter_nfo_scrips()

        if NFO_CACHE_FILE.exists():
            try:
                with open(NFO_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                df["strike_num"] = pd.to_numeric(df["strike"], errors="coerce") / 100.0
                df["expiry_dt"] = pd.to_datetime(df["expiry"], format="%d%b%Y", errors="coerce")
                self._df_tokens = df
                logger.info(f"Loaded {len(self._df_tokens)} active NFO instruments into TokenManager.")
            except Exception as e:
                logger.warning(f"Failed to load cached scrip master: {e}")

    def find_option_token(self, name: str, strike: float, option_type: str, expiry: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Finds exact instrument token for the nearest active weekly/monthly option contract.
        Example: name='NIFTY', strike=25200, option_type='CE' -> Token 64451 (NIFTY23NOV2625200CE)
        """
        if self._df_tokens is None or self._df_tokens.empty:
            self.load_scrip_master()

        if self._df_tokens is None or self._df_tokens.empty:
            return None

        try:
            sym_name = name.upper().strip()
            opt_type = option_type.upper().strip()
            stk_target = float(strike)

            # Match underlying name and strike
            df_match = self._df_tokens[
                (self._df_tokens["name"] == sym_name) &
                (self._df_tokens["strike_num"] == stk_target) &
                (self._df_tokens["symbol"].str.endswith(opt_type))
            ].copy()

            if df_match.empty:
                return None

            # Filter expiries on or after today and sort chronologically ascending
            today = pd.Timestamp.now().normalize()
            df_active = df_match[df_match["expiry_dt"] >= today].sort_values("expiry_dt")

            target_row = df_active.iloc[0] if not df_active.empty else df_match.iloc[0]

            return {
                "token": str(target_row["token"]),
                "symbol": str(target_row["symbol"]),
                "name": str(target_row["name"]),
                "expiry": str(target_row.get("expiry", "")),
                "strike": float(stk_target),
                "option_type": opt_type,
                "lotsize": target_row.get("lotsize")
            }
        except Exception as e:
            logger.warning(f"Option token lookup failed for {name} {strike} {option_type}: {e}")
        return None

    def find_dual_option_tokens(self, name: str, strike: float) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Resolves both CE and PE contracts for the active weekly expiry."""
        ce = self.find_option_token(name, strike, "CE")
        pe = self.find_option_token(name, strike, "PE")
        return ce, pe
