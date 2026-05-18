#!/usr/bin/env python3
"""
MSRAP Factor Worker
--------------------
Builds factor returns from universe, runs rolling OLS per symbol,
persists factor_loadings to TimescaleDB.
"""

import sys
import os
import logging
import argparse
from datetime import timezone

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import load_ohlcv, save_factor_loadings, save_analytics, engine
from factor.factor_models import IndiaFactorLibrary, FactorModel, PCAFactorModel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [factor_worker] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "BAJFINANCE.NS", "HINDUNILVR.NS", "WIPRO.NS", "MARUTI.NS",
]

WINDOW = 252


def load_universe_prices(days: int = 1825) -> pd.DataFrame:
    """Load close prices for all universe symbols."""
    frames = {}
    for sym in UNIVERSE:
        df = load_ohlcv(sym, interval="1d", days=days)
        if df is not None and len(df) > 30:
            frames[sym] = df["close"]
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index()


def run(symbol: str):
    log.info("Running factor worker for %s", symbol)

    # ── Load universe ──
    log.info("Loading universe prices (%d symbols)...", len(UNIVERSE))
    universe_prices = load_universe_prices(days=1825)

    if universe_prices.empty or len(universe_prices) < WINDOW + 30:
        log.warning("Not enough universe data; got %d rows", len(universe_prices))
        return

    # ── Build factor returns ──
    lib = IndiaFactorLibrary(universe_prices)
    factor_returns = lib.build_factor_returns()
    log.info("Factor returns built: %s rows x %s factors",
             len(factor_returns), len(factor_returns.columns))

    # ── Load target symbol ──
    target_df = load_ohlcv(symbol, interval="1d", days=1825)
    if target_df is None or len(target_df) < WINDOW:
        log.warning("Insufficient data for target symbol %s", symbol)
        return

    log_ret = np.log(target_df["close"] / target_df["close"].shift(1)).dropna()

    # ── Rolling OLS ──
    model   = FactorModel(factor_returns, window=WINDOW)
    rolling = model.fit_rolling(log_ret)

    if rolling.empty:
        log.warning("Rolling OLS returned no results for %s", symbol)
        return

    # ── Persist factor loadings ──
    records = []
    for ts, row in rolling.iterrows():
        record = {
            "ts":           ts.to_pydatetime().replace(tzinfo=timezone.utc),
            "window_days":  WINDOW,
            "beta_market":  row.get("beta_mkt"),
            "beta_size":    row.get("beta_smb"),
            "beta_value":   row.get("beta_hml"),
            "beta_momentum": row.get("beta_mom"),
            "beta_quality": row.get("beta_qmj"),
            "alpha":        row.get("alpha"),
            "r_squared":    row.get("r_squared"),
            "residual_vol": row.get("residual_vol"),
        }
        # Replace NaN with None for DB
        record = {k: (None if (v is not None and isinstance(v, float) and np.isnan(v)) else v)
                  for k, v in record.items()}
        records.append(record)

    save_factor_loadings(symbol, records)
    log.info("Saved %d factor loading rows for %s", len(records), symbol)

    # ── PCA summary (universe-level, run once per day) ──
    if symbol == UNIVERSE[0]:
        log.info("Running PCA on universe returns...")
        universe_returns = np.log(universe_prices / universe_prices.shift(1)).dropna(how="all")
        pca_model = PCAFactorModel(n_components=5)
        try:
            pca_model.fit(universe_returns)
            summary   = pca_model.summary()
            latest_ts = universe_returns.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
            analytics = [
                {"ts": latest_ts, "metric": "pca_cum_explained",
                 "value": round(summary["cumulative_explained"], 6)},
            ]
            for i, ev in enumerate(summary["explained_variance_ratio"]):
                analytics.append({
                    "ts":     latest_ts,
                    "metric": f"pca_pc{i+1}_explained",
                    "value":  round(float(ev), 6),
                })
            save_analytics(symbol, "factor", analytics)
        except Exception as e:
            log.error("PCA failed: %s", e)

    log.info("Factor worker completed for %s", symbol)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    run(args.symbol)
