#!/usr/bin/env python3
"""
MSRAP Regime Worker
-------------------
Fits HMM regime model and persists states to regime_states table.
"""

import sys
import os
import logging
import argparse
from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import load_ohlcv, save_regime_states, save_analytics
from regime.regime_models import HMMRegimeClassifier, detect_changepoints

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [regime_worker] %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run(symbol: str):
    log.info("Running regime worker for %s", symbol)

    df = load_ohlcv(symbol, interval="1d", days=1825)
    if df is None or len(df) < 63:
        log.warning("Insufficient data for %s", symbol)
        return

    # ── HMM fit + predict ──
    clf   = HMMRegimeClassifier(n_states=3, n_iter=200)
    states = clf.fit_predict(df)

    # ── Persist regime states ──
    records = []
    for ts, row in states.iterrows():
        records.append({
            "ts":          ts.to_pydatetime().replace(tzinfo=timezone.utc),
            "state":       int(row["state"]),
            "state_label": str(row["state_label"]),
            "prob_state0": round(float(row["prob_state0"]), 6),
            "prob_state1": round(float(row["prob_state1"]), 6),
            "prob_state2": round(float(row["prob_state2"]), 6),
        })

    save_regime_states(symbol, records)
    log.info("Saved %d regime states for %s", len(records), symbol)

    # ── Save transition matrix as analytics_results ──
    tmat = clf.transition_matrix()
    latest_ts = df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    analytics = []
    for from_state in tmat.index:
        for to_state in tmat.columns:
            analytics.append({
                "ts":     latest_ts,
                "metric": f"tmat_{from_state}_to_{to_state}",
                "value":  round(float(tmat.loc[from_state, to_state]), 6),
            })

    # ── Changepoints ──
    bkps = detect_changepoints(df["close"])
    if bkps:
        analytics.append({
            "ts":        latest_ts,
            "metric":    "changepoint_count",
            "value":     float(len(bkps)),
        })

    save_analytics(symbol, "regime", analytics)
    log.info("Regime worker completed for %s", symbol)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    run(args.symbol)
