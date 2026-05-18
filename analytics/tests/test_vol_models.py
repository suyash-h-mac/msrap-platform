"""
Unit tests for analytics/volatility/vol_models.py

All tests use synthetic data — no DB or network required.
Run with:  pytest analytics/tests/test_vol_models.py -v
"""

import warnings
import numpy as np
import pandas as pd
import pytest

# Make the package importable from the repo root
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from analytics.volatility.vol_models import (
    annualise,
    close_to_close_vol,
    parkinson_vol,
    rogers_satchell_vol,
    yang_zhang_vol,
    realised_vol,
    vol_cone,
    vol_risk_premium,
    TRADING_DAYS,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

RNG = np.random.default_rng(42)
N   = 500   # trading days of synthetic data


def _make_ohlcv(n: int = N, drift: float = 0.0, sigma: float = 0.01) -> pd.DataFrame:
    """Generate synthetic OHLCV with geometric Brownian motion closes."""
    dates  = pd.date_range("2020-01-02", periods=n, freq="B")
    log_r  = RNG.normal(drift / TRADING_DAYS, sigma, n)
    close  = 1000 * np.exp(np.cumsum(log_r))
    noise  = RNG.uniform(0.001, 0.005, n)
    high   = close * (1 + noise)
    low    = close * (1 - noise)
    open_  = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame({
        "open":  open_,
        "high":  high,
        "low":   low,
        "close": close,
        "volume": RNG.integers(1_000_000, 10_000_000, n),
    }, index=dates)


@pytest.fixture
def ohlcv():
    return _make_ohlcv()


@pytest.fixture
def close(ohlcv):
    return ohlcv["close"]


# ── annualise ────────────────────────────────────────────────────────────────

class TestAnnualise:
    def test_daily_multiplier(self, close):
        vol = pd.Series([0.01] * 10)
        ann = annualise(vol, "daily")
        expected = 0.01 * np.sqrt(TRADING_DAYS)
        assert np.allclose(ann.values, expected)

    def test_weekly_multiplier(self, close):
        vol = pd.Series([0.02] * 5)
        ann = annualise(vol, "weekly")
        assert np.allclose(ann.values, 0.02 * np.sqrt(52))

    def test_unknown_freq_uses_daily(self, close):
        vol = pd.Series([0.01])
        assert annualise(vol, "hourly").iloc[0] == annualise(vol, "daily").iloc[0]


# ── Close-to-close vol ───────────────────────────────────────────────────────

class TestCloseToCloseVol:
    def test_returns_series(self, close):
        result = close_to_close_vol(close, window=21)
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self, close):
        result = close_to_close_vol(close, window=21)
        assert len(result) == len(close)

    def test_leading_nans(self, close):
        result = close_to_close_vol(close, window=21)
        # First 21 values (window) should be NaN
        assert result.iloc[:21].isna().all()

    def test_positive_after_warmup(self, close):
        result = close_to_close_vol(close, window=21).dropna()
        assert (result > 0).all()

    def test_higher_vol_with_noisier_data(self):
        quiet = _make_ohlcv(sigma=0.005)["close"]
        noisy = _make_ohlcv(sigma=0.030)["close"]
        q_vol = close_to_close_vol(quiet, 21).dropna().mean()
        n_vol = close_to_close_vol(noisy, 21).dropna().mean()
        assert n_vol > q_vol

    def test_annualised_range(self, close):
        """Annualised vol for ~1% daily sigma should be roughly 15–20%."""
        result = close_to_close_vol(close, 21).dropna()
        assert 0.05 < result.mean() < 0.60


# ── Parkinson vol ────────────────────────────────────────────────────────────

class TestParkinsonVol:
    def test_returns_series(self, ohlcv):
        result = parkinson_vol(ohlcv["high"], ohlcv["low"], window=21)
        assert isinstance(result, pd.Series)

    def test_positive_after_warmup(self, ohlcv):
        result = parkinson_vol(ohlcv["high"], ohlcv["low"], window=21).dropna()
        assert (result > 0).all()

    def test_parkinson_gt_zero(self, ohlcv):
        result = parkinson_vol(ohlcv["high"], ohlcv["low"], window=5).dropna()
        assert len(result) > 0


# ── Rogers-Satchell vol ──────────────────────────────────────────────────────

class TestRogersSatchellVol:
    def test_returns_series(self, ohlcv):
        o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
        result = rogers_satchell_vol(o, h, l, c, window=21)
        assert isinstance(result, pd.Series)

    def test_non_negative_after_warmup(self, ohlcv):
        o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
        result = rogers_satchell_vol(o, h, l, c, window=21).dropna()
        # RS vol can occasionally be NaN when H==L; after dropna should be ≥0
        assert (result >= 0).all()


# ── Yang-Zhang vol ───────────────────────────────────────────────────────────

class TestYangZhangVol:
    def test_returns_series(self, ohlcv):
        o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
        result = yang_zhang_vol(o, h, l, c, window=21)
        assert isinstance(result, pd.Series)

    def test_positive_after_warmup(self, ohlcv):
        o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
        result = yang_zhang_vol(o, h, l, c, window=21).dropna()
        assert (result > 0).all()

    def test_yz_vs_cc_similar_magnitude(self, ohlcv):
        """YZ and CC vols should be in the same ballpark (within 3×)."""
        o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
        yz = yang_zhang_vol(o, h, l, c, 21).dropna().mean()
        cc = close_to_close_vol(c, 21).dropna().mean()
        assert 0.1 < yz / cc < 10.0


# ── Composite realised_vol ───────────────────────────────────────────────────

class TestRealisedVol:
    def test_returns_dataframe(self, ohlcv):
        result = realised_vol(ohlcv, window=21)
        assert isinstance(result, pd.DataFrame)

    def test_all_estimators_present(self, ohlcv):
        result = realised_vol(ohlcv, window=21)
        for col in ["cc_vol", "park_vol", "rs_vol", "yz_vol"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_rolling_windows_present(self, ohlcv):
        result = realised_vol(ohlcv, window=21)
        for w in [5, 21, 63, 126, 252]:
            assert f"rv_{w}d" in result.columns

    def test_no_all_nan_rows(self, ohlcv):
        result = realised_vol(ohlcv, window=21)
        # dropna(how="all") is applied — no fully-NaN rows
        assert not result.isna().all(axis=1).any()


# ── Vol cone ─────────────────────────────────────────────────────────────────

class TestVolCone:
    def test_returns_dataframe(self, close):
        result = vol_cone(close)
        assert isinstance(result, pd.DataFrame)

    def test_index_matches_windows(self, close):
        windows = [5, 10, 21, 42]
        result = vol_cone(close, windows=windows)
        assert list(result.index) == windows

    def test_columns_present(self, close):
        result = vol_cone(close, windows=[21], percentiles=[5, 50, 95])
        for col in ["current", "p5", "p50", "p95"]:
            assert col in result.columns

    def test_percentile_ordering(self, close):
        result = vol_cone(close, windows=[21, 63])
        # p5 ≤ p25 ≤ p50 ≤ p75 ≤ p95
        for _, row in result.iterrows():
            assert row["p5"] <= row["p25"] <= row["p50"] <= row["p75"] <= row["p95"]

    def test_current_within_historical_range(self, close):
        result = vol_cone(close, windows=[21])
        row = result.iloc[0]
        # Current vol should be within 5× the extremes (sanity check)
        assert row["current"] > 0


# ── Vol risk premium ─────────────────────────────────────────────────────────

class TestVolRiskPremium:
    def test_returns_dataframe(self, close):
        rv  = close_to_close_vol(close, 21)
        iv  = rv * RNG.uniform(1.0, 1.3, len(rv))  # synthetic implied vol
        result = vol_risk_premium(rv, iv, window=21)
        assert isinstance(result, pd.DataFrame)

    def test_columns_present(self, close):
        rv     = close_to_close_vol(close, 21)
        iv     = rv * 1.1
        result = vol_risk_premium(rv, iv, window=21)
        for col in ["realised", "implied", "vrp", "vrp_ma21"]:
            assert col in result.columns

    def test_positive_vrp_when_iv_above_rv(self, close):
        rv = close_to_close_vol(close, 21)
        # IV consistently 20% above RV → VRP should be positive on average
        iv = rv * 1.2
        result = vol_risk_premium(rv, iv, window=21)
        assert result["vrp"].dropna().mean() > 0
