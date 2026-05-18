"""
MSRAP Analytics FastAPI Service
---------------------------------
Provides HTTP endpoints that the Spring Boot backend can call,
and also serves as a standalone analytics API.
"""

import os
import sys
import logging
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.db import load_ohlcv, engine
from volatility.vol_models import realised_vol, garch_vol, vol_cone, select_best_garch
from regime.regime_models import HMMRegimeClassifier
from factor.factor_models import IndiaFactorLibrary, FactorModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="MSRAP Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# HEALTH
# ──────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "msrap-analytics"}


# ──────────────────────────────────────────────
# VOLATILITY
# ──────────────────────────────────────────────

@app.get("/analytics/volatility/{symbol}")
def get_volatility(symbol: str, days: int = 365, window: int = 21):
    df = load_ohlcv(symbol, days=days)
    if df is None or df.empty:
        raise HTTPException(404, f"No data for {symbol}")

    rv = realised_vol(df, window=window)
    cone = vol_cone(df["close"])

    # GARCH
    garch_res = select_best_garch(df["close"])
    garch_data = {}
    if garch_res:
        gr = garch_res["result"]
        garch_data = {
            "model":       garch_res["model_type"],
            "forecast_ann": round(float(gr.attrs.get("forecast_1d_ann", 0)), 6),
            "aic":         round(float(garch_res["aic"]), 4),
        }

    return {
        "symbol":    symbol,
        "window":    window,
        "latest": {
            "cc_vol":   round(float(rv["cc_vol"].dropna().iloc[-1]), 6) if "cc_vol" in rv.columns else None,
            "park_vol": round(float(rv["park_vol"].dropna().iloc[-1]), 6) if "park_vol" in rv.columns else None,
            "rs_vol":   round(float(rv["rs_vol"].dropna().iloc[-1]), 6) if "rs_vol" in rv.columns else None,
            "yz_vol":   round(float(rv["yz_vol"].dropna().iloc[-1]), 6) if "yz_vol" in rv.columns else None,
        },
        "garch":  garch_data,
        "cone":   cone.reset_index().to_dict(orient="records"),
        "series": rv.reset_index().rename(columns={"ts": "date"}).to_dict(orient="records"),
    }


# ──────────────────────────────────────────────
# REGIME
# ──────────────────────────────────────────────

@app.get("/analytics/regime/{symbol}")
def get_regime(symbol: str, days: int = 1825):
    df = load_ohlcv(symbol, days=days)
    if df is None or len(df) < 63:
        raise HTTPException(404, f"Insufficient data for {symbol}")

    clf    = HMMRegimeClassifier(n_states=3)
    states = clf.fit_predict(df)
    tmat   = clf.transition_matrix()

    return {
        "symbol": symbol,
        "current": {
            "state":       int(states["state"].iloc[-1]),
            "state_label": str(states["state_label"].iloc[-1]),
            "prob_state0": round(float(states["prob_state0"].iloc[-1]), 4),
            "prob_state1": round(float(states["prob_state1"].iloc[-1]), 4),
            "prob_state2": round(float(states["prob_state2"].iloc[-1]), 4),
        },
        "transition_matrix": tmat.to_dict(),
        "history": states.reset_index().rename(columns={"ts": "date"}).to_dict(orient="records"),
    }


# ──────────────────────────────────────────────
# FACTOR
# ──────────────────────────────────────────────

UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
]

@app.get("/analytics/factor/{symbol}")
def get_factor(symbol: str, window: int = 252, days: int = 1825):
    # Load universe
    frames = {}
    for sym in UNIVERSE:
        df = load_ohlcv(sym, days=days)
        if df is not None and len(df) > 60:
            frames[sym] = df["close"]

    if not frames:
        raise HTTPException(500, "Could not load universe prices")

    prices = pd.DataFrame(frames).sort_index()
    lib    = IndiaFactorLibrary(prices)
    factor_returns = lib.build_factor_returns()

    target_df = load_ohlcv(symbol, days=days)
    if target_df is None or len(target_df) < window:
        raise HTTPException(404, f"Insufficient data for {symbol}")

    log_ret = np.log(target_df["close"] / target_df["close"].shift(1)).dropna()
    model   = FactorModel(factor_returns, window=window)
    rolling = model.fit_rolling(log_ret)
    single  = model.fit_single(log_ret)

    latest = rolling.iloc[-1].to_dict() if not rolling.empty else {}

    return {
        "symbol":  symbol,
        "window":  window,
        "latest":  {k: (round(float(v), 6) if v is not None and not (isinstance(v, float) and np.isnan(v)) else None)
                    for k, v in latest.items()},
        "full_period": {k: (round(float(v), 6) if isinstance(v, (int, float)) else v)
                       for k, v in single.items()},
        "rolling": rolling.reset_index().rename(columns={"ts": "date"}).fillna(0).to_dict(orient="records"),
    }


# ──────────────────────────────────────────────
# TRIGGER WORKERS (background)
# ──────────────────────────────────────────────

class WorkerRequest(BaseModel):
    symbol: str

def _run_worker(script: str, symbol: str):
    import subprocess
    base = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(["python3", os.path.join(base, script), "--symbol", symbol])

@app.post("/workers/volatility")
def trigger_vol(req: WorkerRequest, bg: BackgroundTasks):
    bg.add_task(_run_worker, "volatility/vol_worker.py", req.symbol)
    return {"status": "triggered", "symbol": req.symbol}

@app.post("/workers/regime")
def trigger_regime(req: WorkerRequest, bg: BackgroundTasks):
    bg.add_task(_run_worker, "regime/regime_worker.py", req.symbol)
    return {"status": "triggered", "symbol": req.symbol}

@app.post("/workers/factor")
def trigger_factor(req: WorkerRequest, bg: BackgroundTasks):
    bg.add_task(_run_worker, "factor/factor_worker.py", req.symbol)
    return {"status": "triggered", "symbol": req.symbol}
