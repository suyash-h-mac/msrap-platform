#!/usr/bin/env python3
"""
MSRAP Volatility Worker
-----------------------
Triggered by Spring Boot AnalyticsService.
Loads OHLCV from TimescaleDB, runs all vol models, saves results.
"""

import sys
import os
import logging
import argparse
from datetime import timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import load_ohlcv, save_analytics
from volatility.vol_models import (
    realised_vol, garch_vol, select_best_garch, vol_cone
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [vol_worker] %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run(symbol: str):
    log.info("Running volatility worker for %s", symbol)

    df = load_ohlcv(symbol, interval="1d", days=1825)
    if df is None or len(df) < 30:
        log.warning("Insufficient data for %s (%d rows)", symbol, len(df) if df is not None else 0)
        return

    records = []

    # ── Realised vol estimators ──
    rv_df = realised_vol(df)
    for col in rv_df.columns:
        for ts, val in rv_df[col].dropna().items():
            records.append({
                "ts":     ts.to_pydatetime().replace(tzinfo=timezone.utc),
                "metric": col,
                "value":  round(float(val), 8),
            })

    # ── GARCH ──
    best_garch = select_best_garch(df["close"])
    if best_garch:
        garch_result = best_garch["result"]
        model_type   = best_garch["model_type"]
        forecast_ann = garch_result.attrs.get("forecast_1d_ann", None)

        for ts, val in garch_result["ann_conditional_vol"].dropna().items():
            records.append({
                "ts":        ts.to_pydatetime().replace(tzinfo=timezone.utc),
                "metric":    f"garch_cond_vol_{model_type.lower().replace('-', '_')}",
                "value":     round(float(val), 8),
            })

        # Save model metadata as latest-row scalar
        latest_ts = garch_result.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
        if forecast_ann is not None:
            records.append({
                "ts": latest_ts, "metric": "garch_forecast_ann",
                "value": round(float(forecast_ann), 8),
            })
        records.append({
            "ts": latest_ts, "metric": "garch_best_model",
            "value_str": model_type,
        })
        records.append({
            "ts": latest_ts, "metric": "garch_aic",
            "value": round(float(best_garch["aic"]), 4),
        })

    # ── Vol cone (save as latest-date scalar per window/percentile) ──
    cone = vol_cone(df["close"])
    latest_ts = df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    for window, row in cone.iterrows():
        for col, val in row.items():
            records.append({
                "ts":     latest_ts,
                "metric": f"cone_w{window}_{col}",
                "value":  round(float(val), 8),
            })

    # ── Persist ──
    save_analytics(symbol, "volatility", records)
    log.info("Saved %d volatility records for %s", len(records), symbol)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    run(args.symbol)
