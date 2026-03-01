"""
live_incident_feed.py
Fire data loader — tries multiple real sources in order:
  1. WiDS geo_events_geoevent.csv (local only)
  2. NASA FIRMS public CSV (no API key needed)
  3. MODIS public CSV fallback
  4. Empty DataFrame with honest label

Public FIRMS URLs (no key required, updated every ~1 hour):
  VIIRS: https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv
  MODIS: https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.csv
"""

import streamlit as st
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone

FIRMS_VIIRS = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
    "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv"
)
FIRMS_MODIS = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
    "modis-c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.csv"
)


@st.cache_data(ttl=300, show_spinner=False)
def load_fire_data():
    """
    Returns (df, source_key, display_label)
    source_key: 'wids' | 'firms_viirs' | 'firms_modis' | 'none'
    """
    # 1. Try WiDS local file
    for p in [Path("geo_events_geoevent.csv"),
               Path("01_raw_data/geo_events_geoevent.csv"),
               Path("../01_raw_data/geo_events_geoevent.csv")]:
        if p.exists():
            try:
                df = pd.read_csv(p, low_memory=False, nrows=10000)
                if "lat" in df.columns and "lon" in df.columns:
                    active = df[df.get("is_active", pd.Series(dtype=bool)) == True].copy()
                    if len(active) > 0:
                        active["source"] = "wids"
                        return active, "wids", "🟢 WiDS Geo Events (Local)"
            except Exception:
                pass

    # 2. NASA FIRMS VIIRS (no key)
    for url, key, label in [
        (FIRMS_VIIRS, "firms_viirs", "🟡 NASA FIRMS VIIRS (Live)"),
        (FIRMS_MODIS, "firms_modis", "🟡 NASA FIRMS MODIS (Live)"),
    ]:
        try:
            r = requests.get(url, timeout=12)
            if r.status_code == 200 and len(r.text) > 100:
                df = pd.read_csv(StringIO(r.text))
                # Normalize column names
                df.columns = [c.lower() for c in df.columns]
                for lat_col in ["latitude", "lat"]:
                    if lat_col in df.columns:
                        df["lat"] = pd.to_numeric(df[lat_col], errors="coerce")
                        break
                for lon_col in ["longitude", "lon"]:
                    if lon_col in df.columns:
                        df["lon"] = pd.to_numeric(df[lon_col], errors="coerce")
                        break
                df = df.dropna(subset=["lat", "lon"])
                # US only
                df = df[(df["lat"].between(24, 50)) & (df["lon"].between(-125, -65))]
                if len(df) > 0:
                    df["source"] = key
                    return df, key, label
        except Exception:
            continue

    # 3. No data
    return pd.DataFrame(), "none", "⚪ No live fire data available"


def get_fire_summary(df, source):
    """Return dict of summary stats for sidebar badge."""
    if source == "none" or len(df) == 0:
        return {"n_fires": 0, "n_high_conf": 0, "states": []}

    n = len(df)
    high_conf = 0
    if "confidence" in df.columns:
        try:
            conf_num = pd.to_numeric(df["confidence"], errors="coerce")
            high_conf = int((conf_num >= 80).sum())
            if high_conf == 0:
                high_conf = int(df["confidence"].isin(["h", "high", "n", "nominal"]).sum())
        except Exception:
            high_conf = 0

    states = []
    if "state" in df.columns:
        states = df["state"].value_counts().head(5).index.tolist()

    return {"n_fires": n, "n_high_conf": high_conf, "states": states}
