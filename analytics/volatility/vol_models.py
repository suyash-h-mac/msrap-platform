"""
MSRAP Volatility Module
-----------------------
Provides:
  - realised_vol(df)       — close-to-close, Parkinson, Rogers-Satchell
  - garch_vol(series)      — GARCH(1,1) and GJR-GARCH conditional vol
  - vol_risk_premium(df)   — realised vs implied vol spread (when IV available)
  - vol_cone(series)       — percentile cones across windows
  - annualise(vol, freq)   — annualisation helper
"""

import warnings
import logging
import numpy as np
import pandas as pd
from typing import Optional

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

TRADING_DAYS = 252


# ─────────────────────────────────────────────────────────
# ANNUALISATION
# ─────────────────────────────────────────────────────────

def annualise(vol: pd.Series, freq: str = "daily") -> pd.Series:
    """Scale volatility to annual."""
    multipliers = {"daily": TRADING_DAYS, "weekly": 52, "monthly": 12}
    return vol * np.sqrt(multipliers.get(freq, TRADING_DAYS))


# ─────────────────────────────────────────────────────────
# CLOSE-TO-CLOSE REALISED VOL
# ─────────────────────────────────────────────────────────

def close_to_close_vol(close: pd.Series, window: int = 21) -> pd.Series:
    """
    Standard close-to-close log-return volatility.
    Returns annualised daily vol.
    """
    log_ret = np.log(close / close.shift(1))
    rv = log_ret.rolling(window).std()
    return annualise(rv)


# ─────────────────────────────────────────────────────────
# PARKINSON HIGH-LOW ESTIMATOR
# ─────────────────────────────────────────────────────────

def parkinson_vol(high: pd.Series, low: pd.Series, window: int = 21) -> pd.Series:
    """
    Parkinson (1980) range-based volatility estimator.
    More efficient than close-to-close (uses H/L range).
    sigma² = 1/(4*ln2) * E[(ln H/L)²]
    """
    hl_sq = (np.log(high / low)) ** 2
    park = np.sqrt(hl_sq.rolling(window).mean() / (4 * np.log(2)))
    return annualise(park)


# ─────────────────────────────────────────────────────────
# ROGERS-SATCHELL ESTIMATOR
# ─────────────────────────────────────────────────────────

def rogers_satchell_vol(open_: pd.Series, high: pd.Series,
                        low: pd.Series, close: pd.Series,
                        window: int = 21) -> pd.Series:
    """
    Rogers-Satchell (1991) estimator — handles non-zero drift.
    sigma² = E[ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O)]
    """
    rs = (
        np.log(high / close) * np.log(high / open_)
        + np.log(low / close) * np.log(low / open_)
    )
    rv = np.sqrt(rs.rolling(window).mean())
    return annualise(rv)


# ─────────────────────────────────────────────────────────
# YANG-ZHANG ESTIMATOR
# ─────────────────────────────────────────────────────────

def yang_zhang_vol(open_: pd.Series, high: pd.Series,
                   low: pd.Series, close: pd.Series,
                   window: int = 21) -> pd.Series:
    """
    Yang-Zhang (2000) — minimum variance unbiased estimator.
    Handles opening jumps (overnight gaps).
    """
    k = 0.34 / (1.34 + (window + 1) / (window - 1))

    # Overnight vol
    log_oc = np.log(open_ / close.shift(1))
    overnight_var = log_oc.rolling(window).var()

    # Rogers-Satchell
    rs = (
        np.log(high / close) * np.log(high / open_)
        + np.log(low / close) * np.log(low / open_)
    )
    rs_var = rs.rolling(window).mean()

    # Open-to-close vol
    log_co = np.log(close / open_)
    oc_var = log_co.rolling(window).var()

    yz = np.sqrt(overnight_var + k * oc_var + (1 - k) * rs_var)
    return annualise(yz)


# ─────────────────────────────────────────────────────────
# COMPOSITE REALISED VOL
# ─────────────────────────────────────────────────────────

def realised_vol(df: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """
    Compute all realised vol estimators.
    df must have columns: open, high, low, close
    Returns DataFrame with all vol series.
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    result = pd.DataFrame(index=df.index)
    result["cc_vol"]  = close_to_close_vol(c, window)
    result["park_vol"] = parkinson_vol(h, l, window)
    result["rs_vol"]   = rogers_satchell_vol(o, h, l, c, window)
    result["yz_vol"]   = yang_zhang_vol(o, h, l, c, window)

    # 5d, 21d, 63d, 126d windows for cc
    for w in [5, 21, 63, 126, 252]:
        result[f"rv_{w}d"] = close_to_close_vol(c, w)

    return result.dropna(how="all")


# ─────────────────────────────────────────────────────────
# GARCH FAMILY
# ─────────────────────────────────────────────────────────

def garch_vol(close: pd.Series,
              model_type: str = "Garch",
              p: int = 1, q: int = 1,
              dist: str = "studentst") -> Optional[pd.DataFrame]:
    """
    Fit GARCH-family model and return conditional volatility.
    model_type: 'Garch' | 'EGARCH' | 'GJR-GARCH'
    Returns DataFrame with conditional_vol, forecast_vol_1d, aic, bic.
    """
    try:
        from arch import arch_model

        log_ret = (np.log(close / close.shift(1)).dropna() * 100)  # in percent

        if model_type == "GJR-GARCH":
            am = arch_model(log_ret, vol="Garch", p=p, o=1, q=q, dist=dist)
        elif model_type == "EGARCH":
            am = arch_model(log_ret, vol="EGARCH", p=p, q=q, dist=dist)
        else:
            am = arch_model(log_ret, vol="Garch", p=p, q=q, dist=dist)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = am.fit(disp="off", show_warning=False)

        cond_vol = res.conditional_volatility / 100  # back to decimal
        ann_cond_vol = annualise(cond_vol)

        # 1-day ahead forecast
        fc = res.forecast(horizon=1, reindex=False)
        forecast_1d = float(np.sqrt(fc.variance.iloc[-1, 0])) / 100

        result = pd.DataFrame({
            "conditional_vol": cond_vol,
            "ann_conditional_vol": ann_cond_vol,
        }, index=log_ret.index)

        result.attrs["aic"] = res.aic
        result.attrs["bic"] = res.bic
        result.attrs["params"] = res.params.to_dict()
        result.attrs["forecast_1d_ann"] = forecast_1d * np.sqrt(TRADING_DAYS)
        result.attrs["model"] = model_type

        log.info("GARCH fit: AIC=%.2f BIC=%.2f forecast_ann=%.4f",
                 res.aic, res.bic, result.attrs["forecast_1d_ann"])
        return result

    except Exception as e:
        log.error("GARCH fitting failed: %s", e)
        return None


def select_best_garch(close: pd.Series) -> dict:
    """
    Fit GARCH, GJR-GARCH, EGARCH and select by AIC.
    Returns best model result dict.
    """
    candidates = ["Garch", "GJR-GARCH", "EGARCH"]
    best = None
    best_aic = np.inf

    for model_type in candidates:
        result = garch_vol(close, model_type=model_type)
        if result is not None:
            aic = result.attrs.get("aic", np.inf)
            if aic < best_aic:
                best_aic = aic
                best = {"model_type": model_type, "result": result, "aic": aic}

    return best or {}


# ─────────────────────────────────────────────────────────
# VOLATILITY CONE
# ─────────────────────────────────────────────────────────

def vol_cone(close: pd.Series,
             windows: list[int] = [5, 10, 21, 42, 63, 126, 252],
             percentiles: list[float] = [5, 25, 50, 75, 95]) -> pd.DataFrame:
    """
    Compute vol cone: percentile distribution of realised vol
    across different rolling windows over the full history.
    Useful for identifying whether current vol is elevated or suppressed.
    """
    log_ret = np.log(close / close.shift(1))
    rows = []
    for w in windows:
        rv = log_ret.rolling(w).std() * np.sqrt(TRADING_DAYS)
        rv = rv.dropna()
        if len(rv) < 2:
            continue
        row = {"window": w, "current": float(rv.iloc[-1])}
        for p in percentiles:
            row[f"p{p}"] = float(np.percentile(rv, p))
        rows.append(row)

    return pd.DataFrame(rows).set_index("window")


# ─────────────────────────────────────────────────────────
# VOL RISK PREMIUM
# ─────────────────────────────────────────────────────────

def vol_risk_premium(realised: pd.Series, implied: pd.Series,
                     window: int = 21) -> pd.DataFrame:
    """
    VRP = implied vol (lagged) - realised vol over that period.
    Positive VRP: options rich. Negative: options cheap.
    """
    vrp = implied.shift(window) - realised
    result = pd.DataFrame({
        "realised": realised,
        "implied":  implied,
        "vrp":      vrp,
        "vrp_ma21": vrp.rolling(21).mean(),
    })
    return result
