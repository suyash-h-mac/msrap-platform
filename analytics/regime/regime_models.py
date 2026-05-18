"""
MSRAP Regime Classification Module
------------------------------------
Implements:
  - HMMRegimeClassifier  : 3-state Gaussian HMM on vol+return features
  - BreadthAnalyser      : market breadth metrics (A/D ratio, % above MA)
  - SectorRotation       : relative strength ranking
"""

import logging
import warnings
import numpy as np
import pandas as pd
from typing import Optional

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

TRADING_DAYS = 252
STATE_LABELS = {0: "low-vol", 1: "trending", 2: "high-vol"}


# ─────────────────────────────────────────────────────────
# HMM REGIME CLASSIFIER
# ─────────────────────────────────────────────────────────

class HMMRegimeClassifier:
    """
    3-state Gaussian HMM on daily log-returns + rolling realised vol.
    States are labelled post-hoc by vol level:
      0 = low-vol / calm
      1 = trending / moderate
      2 = high-vol / stressed
    """

    def __init__(self, n_states: int = 3, n_iter: int = 200, seed: int = 42):
        self.n_states = n_states
        self.n_iter   = n_iter
        self.seed     = seed
        self.model    = None
        self.state_map = {}  # model state → labelled state

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        """Feature matrix: log_return, rv_21d, rv_5d."""
        close = df["close"]
        log_ret = np.log(close / close.shift(1))
        rv_21   = log_ret.rolling(21).std() * np.sqrt(TRADING_DAYS)
        rv_5    = log_ret.rolling(5).std()  * np.sqrt(TRADING_DAYS)
        feat = pd.DataFrame({
            "log_ret": log_ret,
            "rv_21":   rv_21,
            "rv_5":    rv_5,
        }).dropna()
        return feat, feat.values

    def fit(self, df: pd.DataFrame) -> "HMMRegimeClassifier":
        from hmmlearn.hmm import GaussianHMM

        feat_df, X = self._build_features(df)
        self._feat_index = feat_df.index

        self.model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=self.n_iter,
            random_state=self.seed,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model.fit(X)

        # Label states by average realised vol (col index 1 = rv_21)
        means_vol = self.model.means_[:, 1]
        sorted_states = np.argsort(means_vol)  # ascending vol
        self.state_map = {int(s): i for i, s in enumerate(sorted_states)}

        log.info("HMM fitted. State vol means: %s", means_vol.round(4))
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
          state, state_label, prob_state0, prob_state1, prob_state2
        """
        if self.model is None:
            raise RuntimeError("Model not fitted yet.")

        feat_df, X = self._build_features(df)
        raw_states  = self.model.predict(X)
        posteriors  = self.model.predict_proba(X)

        # Re-map to labelled states
        mapped = np.array([self.state_map.get(s, s) for s in raw_states])

        result = pd.DataFrame({
            "state":       mapped,
            "state_label": [STATE_LABELS.get(s, "unknown") for s in mapped],
            "prob_state0": posteriors[:, self.state_map.get(0, 0)
                                       if 0 in self.state_map.values() else 0],
            "prob_state1": posteriors[:, self.state_map.get(1, 1)
                                       if 1 in self.state_map.values() else 1],
            "prob_state2": posteriors[:, self.state_map.get(2, 2)
                                       if 2 in self.state_map.values() else 2],
        }, index=feat_df.index)

        return result

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).predict(df)

    def transition_matrix(self) -> pd.DataFrame:
        if self.model is None:
            return pd.DataFrame()
        return pd.DataFrame(
            self.model.transmat_,
            index=[STATE_LABELS.get(self.state_map.get(i, i), i) for i in range(self.n_states)],
            columns=[STATE_LABELS.get(self.state_map.get(i, i), i) for i in range(self.n_states)],
        )


# ─────────────────────────────────────────────────────────
# CHANGEPOINT DETECTION (RUPTURES)
# ─────────────────────────────────────────────────────────

def detect_changepoints(close: pd.Series,
                        model: str = "rbf",
                        n_bkps: int = 5) -> list:
    """
    Use ruptures library for offline changepoint detection.
    Returns list of changepoint indices.
    Falls back gracefully if ruptures not installed.
    """
    try:
        import ruptures as rpt
        log_ret = np.log(close / close.shift(1)).dropna().values
        algo    = rpt.Pelt(model=model).fit(log_ret)
        bkps    = algo.predict(pen=10)
        return bkps
    except ImportError:
        log.warning("ruptures not installed; skipping changepoint detection")
        return []
    except Exception as e:
        log.error("Changepoint detection failed: %s", e)
        return []


# ─────────────────────────────────────────────────────────
# BREADTH METRICS
# ─────────────────────────────────────────────────────────

class BreadthAnalyser:
    """
    Market breadth metrics from a universe of equities.
    Input: dict of {symbol: close_series}
    """

    def __init__(self, universe: dict[str, pd.Series]):
        self.universe = universe
        self.prices   = pd.DataFrame(universe).sort_index()

    def advance_decline_ratio(self, window: int = 1) -> pd.Series:
        """
        Daily A/D ratio: advancing / declining issues.
        """
        changes = self.prices.pct_change(window)
        advancing  = (changes > 0).sum(axis=1)
        declining  = (changes < 0).sum(axis=1)
        return (advancing / declining.replace(0, np.nan)).rename("ad_ratio")

    def pct_above_ma(self, ma_period: int = 200) -> pd.Series:
        """% of symbols trading above their MA."""
        mas = self.prices.rolling(ma_period).mean()
        above = (self.prices > mas).sum(axis=1)
        total = self.prices.notna().sum(axis=1)
        return (above / total * 100).rename(f"pct_above_{ma_period}ma")

    def new_highs_lows(self, lookback: int = 252) -> pd.DataFrame:
        """Count new 52-week highs and lows each day."""
        rolling_high = self.prices.rolling(lookback).max()
        rolling_low  = self.prices.rolling(lookback).min()
        new_highs = (self.prices >= rolling_high).sum(axis=1)
        new_lows  = (self.prices <= rolling_low).sum(axis=1)
        return pd.DataFrame({
            "new_highs": new_highs,
            "new_lows":  new_lows,
            "hl_ratio":  new_highs / (new_highs + new_lows + 1e-9),
        })

    def all_metrics(self) -> pd.DataFrame:
        result = pd.concat([
            self.advance_decline_ratio(),
            self.pct_above_ma(50),
            self.pct_above_ma(200),
            self.new_highs_lows(),
        ], axis=1)
        return result


# ─────────────────────────────────────────────────────────
# SECTOR ROTATION — RELATIVE STRENGTH
# ─────────────────────────────────────────────────────────

def relative_strength(sector_prices: pd.DataFrame,
                      benchmark: pd.Series,
                      window: int = 63) -> pd.DataFrame:
    """
    Rolling RS-ratio: sector momentum vs benchmark.
    RS = (sector / benchmark), normalised over window.
    Returns wide DataFrame of RS-ratio per sector.
    """
    rs_raw = sector_prices.divide(benchmark, axis=0)
    rs_norm = rs_raw.rolling(window).mean().divide(
        rs_raw.rolling(window * 4).mean().replace(0, np.nan)
    )
    return rs_norm.dropna(how="all")


def sector_momentum_rank(rs_df: pd.DataFrame) -> pd.Series:
    """
    Cross-sectional rank of sectors by RS-ratio on latest date.
    Returns Series sorted descending (strongest first).
    """
    latest = rs_df.iloc[-1].dropna()
    return latest.sort_values(ascending=False)
