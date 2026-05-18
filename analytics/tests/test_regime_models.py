"""
Unit tests for analytics/regime/regime_models.py

Uses synthetic OHLCV data — no DB or network required.
Run with:  pytest analytics/tests/test_regime_models.py -v
"""

import numpy as np
import pandas as pd
import pytest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from analytics.regime.regime_models import (
    HMMRegimeClassifier,
    BreadthAnalyser,
    relative_strength,
    sector_momentum_rank,
    STATE_LABELS,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

RNG = np.random.default_rng(0)
N   = 600   # days — enough for HMM warm-up


def _make_ohlcv(n: int = N, sigma: float = 0.012) -> pd.DataFrame:
    dates  = pd.date_range("2019-01-02", periods=n, freq="B")
    log_r  = RNG.normal(0, sigma, n)
    close  = 500 * np.exp(np.cumsum(log_r))
    noise  = RNG.uniform(0.002, 0.008, n)
    high   = close * (1 + noise)
    low    = close * (1 - noise)
    open_  = np.roll(close, 1); open_[0] = close[0]
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=dates,
    )


def _make_universe(n_symbols: int = 8, n: int = N) -> dict[str, pd.Series]:
    dates = pd.date_range("2019-01-02", periods=n, freq="B")
    result = {}
    for i in range(n_symbols):
        log_r = RNG.normal(0, 0.015, n)
        result[f"SYM{i}"] = pd.Series(
            100 * np.exp(np.cumsum(log_r)), index=dates, name=f"SYM{i}"
        )
    return result


@pytest.fixture
def ohlcv():
    return _make_ohlcv()


@pytest.fixture
def universe():
    return _make_universe()


# ── HMMRegimeClassifier ───────────────────────────────────────────────────────

class TestHMMRegimeClassifier:

    def test_fit_returns_self(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        result = clf.fit(ohlcv)
        assert result is clf

    def test_model_fitted_after_fit(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        assert clf.model is not None

    def test_predict_returns_dataframe(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        assert isinstance(pred, pd.DataFrame)

    def test_predict_columns(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        for col in ["state", "state_label", "prob_state0", "prob_state1", "prob_state2"]:
            assert col in pred.columns, f"Missing column: {col}"

    def test_state_values_in_range(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        assert pred["state"].isin([0, 1, 2]).all()

    def test_state_labels_valid(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        valid_labels = set(STATE_LABELS.values())
        assert pred["state_label"].isin(valid_labels).all()

    def test_probabilities_sum_to_one(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        prob_sum = (
            pred["prob_state0"] + pred["prob_state1"] + pred["prob_state2"]
        )
        assert np.allclose(prob_sum.values, 1.0, atol=1e-4)

    def test_probabilities_between_zero_and_one(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        for col in ["prob_state0", "prob_state1", "prob_state2"]:
            assert (pred[col] >= 0).all() and (pred[col] <= 1).all()

    def test_fit_predict_equivalent(self, ohlcv):
        clf1 = HMMRegimeClassifier(n_states=3, n_iter=50, seed=42)
        out1 = clf1.fit_predict(ohlcv)

        clf2 = HMMRegimeClassifier(n_states=3, n_iter=50, seed=42)
        clf2.fit(ohlcv)
        out2 = clf2.predict(ohlcv)

        assert (out1["state"].values == out2["state"].values).all()

    def test_transition_matrix_shape(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        tm = clf.transition_matrix()
        assert tm.shape == (3, 3)

    def test_transition_matrix_rows_sum_to_one(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        tm = clf.transition_matrix()
        assert np.allclose(tm.values.sum(axis=1), 1.0, atol=1e-6)

    def test_predict_without_fit_raises(self, ohlcv):
        clf = HMMRegimeClassifier()
        with pytest.raises(RuntimeError, match="not fitted"):
            clf.predict(ohlcv)

    def test_state_map_covers_all_states(self, ohlcv):
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        # state_map values should be {0,1,2}
        assert set(clf.state_map.values()) == {0, 1, 2}

    def test_output_index_subset_of_input(self, ohlcv):
        """Output index is a subset of input (first ~21 rows dropped for feature warmup)."""
        clf = HMMRegimeClassifier(n_states=3, n_iter=50)
        clf.fit(ohlcv)
        pred = clf.predict(ohlcv)
        assert pred.index.isin(ohlcv.index).all()
        assert len(pred) < len(ohlcv)


# ── BreadthAnalyser ──────────────────────────────────────────────────────────

class TestBreadthAnalyser:

    def test_advance_decline_ratio_series(self, universe):
        ba = BreadthAnalyser(universe)
        result = ba.advance_decline_ratio()
        assert isinstance(result, pd.Series)

    def test_advance_decline_positive(self, universe):
        ba = BreadthAnalyser(universe)
        ad = ba.advance_decline_ratio().dropna()
        assert (ad >= 0).all()

    def test_pct_above_ma_range(self, universe):
        ba = BreadthAnalyser(universe)
        pct = ba.pct_above_ma(ma_period=50).dropna()
        assert ((pct >= 0) & (pct <= 100)).all()

    def test_new_highs_lows_columns(self, universe):
        ba = BreadthAnalyser(universe)
        result = ba.new_highs_lows(lookback=63)
        for col in ["new_highs", "new_lows", "hl_ratio"]:
            assert col in result.columns

    def test_hl_ratio_between_zero_and_one(self, universe):
        ba = BreadthAnalyser(universe)
        hl = ba.new_highs_lows(lookback=63)["hl_ratio"].dropna()
        assert ((hl >= 0) & (hl <= 1)).all()

    def test_all_metrics_returns_dataframe(self, universe):
        ba = BreadthAnalyser(universe)
        result = ba.all_metrics()
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) > 3


# ── Relative strength / sector rotation ──────────────────────────────────────

class TestRelativeStrength:

    @pytest.fixture
    def sector_data(self, universe):
        dates = pd.date_range("2019-01-02", periods=N, freq="B")
        prices = pd.DataFrame(universe, index=dates)
        benchmark = prices.mean(axis=1)
        return prices, benchmark

    def test_returns_dataframe(self, sector_data):
        prices, benchmark = sector_data
        result = relative_strength(prices, benchmark, window=63)
        assert isinstance(result, pd.DataFrame)

    def test_columns_match_input(self, sector_data):
        prices, benchmark = sector_data
        result = relative_strength(prices, benchmark, window=63)
        assert set(result.columns) == set(prices.columns)

    def test_no_all_nan_rows(self, sector_data):
        prices, benchmark = sector_data
        result = relative_strength(prices, benchmark, window=63)
        assert not result.isna().all(axis=1).any()


class TestSectorMomentumRank:

    def test_returns_series(self, universe):
        dates = pd.date_range("2019-01-02", periods=N, freq="B")
        prices = pd.DataFrame(universe, index=dates)
        benchmark = prices.mean(axis=1)
        rs = relative_strength(prices, benchmark, window=63)
        rank = sector_momentum_rank(rs)
        assert isinstance(rank, pd.Series)

    def test_descending_order(self, universe):
        dates = pd.date_range("2019-01-02", periods=N, freq="B")
        prices = pd.DataFrame(universe, index=dates)
        benchmark = prices.mean(axis=1)
        rs = relative_strength(prices, benchmark, window=63)
        rank = sector_momentum_rank(rs)
        assert list(rank.values) == sorted(rank.values, reverse=True)
