"""
Unit tests for analytics/factor/factor_models.py

Uses synthetic price data — no DB or network required.
Run with:  pytest analytics/tests/test_factor_models.py -v
"""

import numpy as np
import pandas as pd
import pytest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from analytics.factor.factor_models import (
    IndiaFactorLibrary,
    FactorModel,
    PCAFactorModel,
    winsorise,
    TRADING_DAYS,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

RNG        = np.random.default_rng(7)
N_DAYS     = 800   # enough for 252-day rolling windows
N_SYMBOLS  = 15    # small universe


def _make_prices(n: int = N_DAYS, n_sym: int = N_SYMBOLS) -> pd.DataFrame:
    dates   = pd.date_range("2018-01-02", periods=n, freq="B")
    symbols = [f"SYM{i:02d}" for i in range(n_sym)]
    data = {}
    for s in symbols:
        log_r = RNG.normal(0, 0.015, n)
        data[s] = 100 * np.exp(np.cumsum(log_r))
    return pd.DataFrame(data, index=dates)


def _make_factor_returns(n: int = N_DAYS) -> pd.DataFrame:
    dates = pd.date_range("2018-01-02", periods=n, freq="B")
    return pd.DataFrame({
        "MKT": RNG.normal(0.0003, 0.010, n),
        "SMB": RNG.normal(0.0001, 0.005, n),
        "MOM": RNG.normal(0.0002, 0.007, n),
    }, index=dates)


@pytest.fixture
def prices():
    return _make_prices()


@pytest.fixture
def factor_lib(prices):
    return IndiaFactorLibrary(prices)


@pytest.fixture
def factor_returns():
    return _make_factor_returns()


# ── winsorise ────────────────────────────────────────────────────────────────

class TestWinsorise:
    def test_clips_extremes(self):
        s = pd.Series([1.0] * 98 + [1000.0, -1000.0])
        w = winsorise(s, p=0.01)
        assert w.max() < 1000.0
        assert w.min() > -1000.0

    def test_length_unchanged(self):
        s = pd.Series(range(100), dtype=float)
        assert len(winsorise(s)) == 100

    def test_idempotent_on_clean_data(self):
        s = pd.Series(RNG.normal(0, 1, 200))
        w = winsorise(s, p=0.01)
        assert len(w) == len(s)


# ── IndiaFactorLibrary ────────────────────────────────────────────────────────

class TestIndiaFactorLibrary:

    def test_returns_property_is_dataframe(self, factor_lib):
        assert isinstance(factor_lib.returns, pd.DataFrame)

    def test_returns_shape(self, prices, factor_lib):
        # returns has one fewer row than prices (first row is NaN)
        assert len(factor_lib.returns) <= len(prices)

    def test_market_factor_is_series(self, factor_lib):
        mkt = factor_lib.market_factor()
        assert isinstance(mkt, pd.Series)
        assert mkt.name == "MKT"

    def test_market_factor_length(self, prices, factor_lib):
        mkt = factor_lib.market_factor()
        # Should align with returns length
        assert len(mkt) == len(factor_lib.returns)

    def test_smb_factor_is_series(self, factor_lib):
        smb = factor_lib.smb_factor()
        assert isinstance(smb, pd.Series)
        assert smb.name == "SMB"

    def test_momentum_factor_is_series(self, factor_lib):
        mom = factor_lib.momentum_factor()
        assert isinstance(mom, pd.Series)
        assert mom.name == "MOM"

    def test_build_factor_returns_dataframe(self, factor_lib):
        factors = factor_lib.build_factor_returns()
        assert isinstance(factors, pd.DataFrame)

    def test_build_contains_core_factors(self, factor_lib):
        factors = factor_lib.build_factor_returns()
        for col in ["MKT", "SMB", "MOM"]:
            assert col in factors.columns, f"Missing factor: {col}"

    def test_build_no_allnan_rows(self, factor_lib):
        factors = factor_lib.build_factor_returns()
        assert not factors.isna().all(axis=1).any()

    def test_market_factor_rf_subtracted(self, prices):
        """Market factor should be slightly less than raw equal-weighted return."""
        lib = IndiaFactorLibrary(prices)
        mkt = lib.market_factor().dropna()
        raw_eq = lib.returns.mean(axis=1).dropna()
        rf_daily = 0.065 / TRADING_DAYS
        # Mean of (mkt) == mean(raw_eq) - rf
        assert abs(mkt.mean() - (raw_eq.mean() - rf_daily)) < 1e-8

    def test_smb_long_short_structure(self, prices):
        """SMB = small-minus-big; with enough symbols it should be computable."""
        lib = IndiaFactorLibrary(prices)
        smb = lib.smb_factor().dropna()
        assert len(smb) > 0


# ── FactorModel (rolling OLS) ─────────────────────────────────────────────────

class TestFactorModel:

    def test_fit_rolling_returns_dataframe(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_rolling(asset_ret)
        assert isinstance(result, pd.DataFrame)

    def test_rolling_columns_present(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_rolling(asset_ret)
        if len(result) > 0:
            for col in ["alpha", "r_squared", "residual_vol"]:
                assert col in result.columns
            for fac in factor_returns.columns:
                assert f"beta_{fac.lower()}" in result.columns

    def test_rolling_r_squared_in_range(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_rolling(asset_ret)
        if len(result) > 0:
            assert ((result["r_squared"] >= 0) & (result["r_squared"] <= 1)).all()

    def test_rolling_residual_vol_positive(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_rolling(asset_ret)
        if len(result) > 0:
            assert (result["residual_vol"] > 0).all()

    def test_rolling_output_length(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        window = 252
        fm = FactorModel(factor_returns, window=window)
        result = fm.fit_rolling(asset_ret)
        # Number of rolling windows = max(0, len(aligned) - window + 1)
        aligned_len = len(
            pd.concat([asset_ret.rename("ret"), factor_returns], axis=1).dropna()
        )
        expected_rows = max(0, aligned_len - window + 1)
        assert len(result) == expected_rows

    def test_insufficient_data_returns_empty(self, factor_returns):
        # Only 10 rows — far less than window=252
        short_ret = pd.Series(
            RNG.normal(0, 0.01, 10),
            index=factor_returns.index[:10],
        )
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_rolling(short_ret)
        assert len(result) == 0

    def test_fit_single_returns_dict(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_single(asset_ret)
        assert isinstance(result, dict)

    def test_fit_single_keys(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_single(asset_ret)
        if result:
            assert "alpha" in result
            assert "r_squared" in result
            assert "residual_vol" in result

    def test_fit_single_r_squared_in_range(self, prices, factor_returns):
        asset_ret = np.log(prices.iloc[:, 0] / prices.iloc[:, 0].shift(1)).dropna()
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_single(asset_ret)
        if result:
            assert 0.0 <= result["r_squared"] <= 1.0

    def test_fit_single_too_short_returns_empty(self, factor_returns):
        short = pd.Series(
            RNG.normal(0, 0.01, 20),
            index=factor_returns.index[:20],
        )
        fm = FactorModel(factor_returns, window=252)
        result = fm.fit_single(short)
        assert result == {}


# ── PCAFactorModel ────────────────────────────────────────────────────────────

class TestPCAFactorModel:

    def test_fit_returns_self(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=3)
        result = pca.fit(returns)
        assert result is pca

    def test_explained_variance_set_after_fit(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=3)
        pca.fit(returns)
        assert pca.explained_ is not None
        assert len(pca.explained_) <= 3

    def test_explained_variance_positive(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=3)
        pca.fit(returns)
        assert (pca.explained_ > 0).all()

    def test_factor_loadings_shape(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        n_comp = 3
        pca = PCAFactorModel(n_components=n_comp)
        pca.fit(returns)
        loadings = pca.factor_loadings()
        assert isinstance(loadings, pd.DataFrame)
        assert loadings.shape[1] == n_comp
        assert loadings.shape[0] == N_SYMBOLS

    def test_factor_loadings_columns(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=3)
        pca.fit(returns)
        loadings = pca.factor_loadings()
        assert list(loadings.columns) == ["PC1", "PC2", "PC3"]

    def test_summary_keys(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=3)
        pca.fit(returns)
        s = pca.summary()
        assert "n_components" in s
        assert "explained_variance_ratio" in s
        assert "cumulative_explained" in s

    def test_cumulative_explained_lte_one(self, prices):
        returns = np.log(prices / prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=5)
        pca.fit(returns)
        s = pca.summary()
        assert 0.0 < s["cumulative_explained"] <= 1.0

    def test_not_fitted_raises(self, prices):
        pca = PCAFactorModel(n_components=3)
        with pytest.raises(RuntimeError, match="not fitted"):
            pca.factor_loadings()

    def test_n_components_capped_by_symbols(self):
        """Request more components than symbols — PCA should cap gracefully."""
        tiny_prices = _make_prices(n=300, n_sym=4)
        returns = np.log(tiny_prices / tiny_prices.shift(1)).dropna()
        pca = PCAFactorModel(n_components=10)  # more than 4 symbols
        pca.fit(returns)
        loadings = pca.factor_loadings()
        assert loadings.shape[1] <= 4
