"""
Angel One Token & Option Scrip Manager.
Downloads, caches, and parses OpenAPIScripMaster.json to look up instrument tokens
and option contracts (Nifty, Bank Nifty, FinNifty CE/PE).
"""
import os
import json
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("TokenManager")

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
SCRIP_MASTER_FILE = CACHE_DIR / "OpenAPIScripMaster.json"
SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"


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

    def download_scrip_master(self, force: bool = False) -> bool:
        """Download latest scrip master JSON from Angel One."""
        try:
            if not force and SCRIP_MASTER_FILE.exists():
                # Check file size
                if SCRIP_MASTER_FILE.stat().st_size > 1024 * 1024:
                    return True
            logger.info("Downloading Angel One Scrip Master JSON...")
            resp = requests.get(SCRIP_MASTER_URL, timeout=30)
            if resp.status_code == 200:
                with open(SCRIP_MASTER_FILE, "wb") as f:
                    f.write(resp.content)
                logger.info("Scrip Master downloaded successfully.")
                return True
        except Exception as e:
            logger.warning(f"Could not download Scrip Master: {e}")
        return False

    def load_scrip_master(self):
        """Loads scrip master into a Pandas DataFrame."""
        if self._df_tokens is not None:
            return
        if not SCRIP_MASTER_FILE.exists():
            # Don't block app launch if offline
            return
        try:
            with open(SCRIP_MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._df_tokens = pd.DataFrame(data)
            logger.info(f"Loaded {len(self._df_tokens)} instruments into TokenManager.")
        except Exception as e:
            logger.warning(f"Failed to load cached scrip master: {e}")

    def find_option_token(self, name: str, strike: float, option_type: str, expiry: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Finds exact instrument token for an option contract.
        Example: name='NIFTY', strike=24150, option_type='CE'
        """
        if self._df_tokens is None or self._df_tokens.empty:
            return None
            
        try:
            opt_type = option_type.upper().strip()
            # NFO options
            df_nfo = self._df_tokens[
                (self._df_tokens["exch_seg"] == "NFO") &
                (self._df_tokens["name"] == name.upper()) &
                (self._df_tokens["symbol"].str.endswith(opt_type))
            ]
            if df_nfo.empty:
                return None
            
            # Match strike (Angel stores strike multiplied by 100 in some feeds or decimal)
            df_strike = df_nfo[
                (df_nfo["strike"].astype(float) == float(strike)) |
                (df_nfo["strike"].astype(float) == float(strike) * 100)
            ]
            if not df_strike.empty:
                # Return closest upcoming expiry
                row = df_strike.iloc[0]
                return {
                    "token": str(row["token"]),
                    "symbol": str(row["symbol"]),
                    "name": str(row["name"]),
                    "expiry": str(row.get("expiry", "")),
                    "strike": float(strike),
                    "option_type": opt_type
                }
        except Exception as e:
            logger.warning(f"Option token lookup failed: {e}")
        return None
