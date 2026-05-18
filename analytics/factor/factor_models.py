"""
MSRAP Factor Risk Decomposition Module
----------------------------------------
Implements:
  - IndiaFactorLibrary : constructs SMB, HML, MOM, QMJ factor returns
  - FactorModel        : rolling OLS attribution per symbol
  - PCAFactorModel     : statistical factor extraction
  - FactorRiskDecomposer : full decomposition with factor + specific risk
"""

import logging
import warnings
import numpy as np
import pandas as pd
from typing import Optional

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

TRADING_DAYS = 252


# ─────────────────────────────────────────────────────────
# HELPER: WINSORIZE
# ─────────────────────────────────────────────────────────

def winsorise(series: pd.Series, p: float = 0.01) -> pd.Series:
    lo, hi = series.quantile(p), series.quantile(1 - p)
    return series.clip(lo, hi)


# ─────────────────────────────────────────────────────────
# INDIA FACTOR LIBRARY
# ─────────────────────────────────────────────────────────

class IndiaFactorLibrary:
    """
    Constructs Fama-French style factor returns from a universe of equities.

    Inputs:
      prices  : pd.DataFrame — daily close prices, symbols as columns
      market_cap : pd.Series — latest market cap per symbol (for size split)
      book_to_market : pd.Series — B/M ratio per symbol (for value split)

    Note: When fundamental data is unavailable, proxies are used:
      - Size proxy: 12-month trailing return (inverse)
      - Value proxy: 12-month return reversal
      - Momentum: 12-1 month return
      - Quality: Sharpe ratio proxy (mean/std of returns)
    """

    def __init__(self, prices: pd.DataFrame,
                 market_cap: Optional[pd.Series] = None,
                 book_to_market: Optional[pd.Series] = None):
        self.prices        = prices.sort_index()
        self.market_cap    = market_cap
        self.book_to_market = book_to_market
        self._returns      = None

    @property
    def returns(self) -> pd.DataFrame:
        if self._returns is None:
            self._returns = np.log(self.prices / self.prices.shift(1)).dropna(how="all")
        return self._returns

    def _cross_section_sort(self, signal: pd.Series,
                            returns_next: pd.Series,
                            n_groups: int = 3) -> tuple[float, float]:
        """
        Sort by signal into n groups, return (top - bottom) return spread.
        """
        combined = pd.concat([signal, returns_next], axis=1).dropna()
        if len(combined) < n_groups * 2:
            return np.nan
        combined.columns = ["signal", "ret"]
        combined["group"] = pd.qcut(combined["signal"], n_groups, labels=False)
        group_rets = combined.groupby("group")["ret"].mean()
        return float(group_rets.iloc[-1] - group_rets.iloc[0])

    def market_factor(self) -> pd.Series:
        """Market (Rm - Rf). Use equal-weighted universe return."""
        eq_ret = self.returns.mean(axis=1)
        rf_daily = 0.065 / TRADING_DAYS  # Approx Indian 91-day T-bill ~ 6.5%
        return (eq_ret - rf_daily).rename("MKT")

    def smb_factor(self) -> pd.Series:
        """
        SMB (Small Minus Big).
        Proxy: split universe by trailing 12m volatility (high vol = small cap proxy).
        """
        vol_12m = self.returns.rolling(252).std().iloc[-1]
        median_vol = vol_12m.median()
        small  = self.returns[vol_12m[vol_12m >= median_vol].index].mean(axis=1)
        big    = self.returns[vol_12m[vol_12m <  median_vol].index].mean(axis=1)
        return (small - big).rename("SMB")

    def hml_factor(self) -> pd.Series:
        """
        HML (High Minus Low value).
        Proxy: 36-month return reversal (low past returns = high B/M proxy).
        """
        ret_36m = self.prices.pct_change(756)   # ~3 years
        daily_hml = pd.Series(index=self.returns.index, dtype=float)

        for dt in self.returns.index:
            if dt not in ret_36m.index:
                continue
            signal = ret_36m.loc[dt].dropna()
            if len(signal) < 4:
                continue
            lo_q = signal.quantile(0.33)
            hi_q = signal.quantile(0.67)
            high_bm = self.returns.loc[dt, signal[signal <= lo_q].index]
            low_bm  = self.returns.loc[dt, signal[signal >= hi_q].index]
            daily_hml.loc[dt] = high_bm.mean() - low_bm.mean()

        return daily_hml.rename("HML")

    def momentum_factor(self) -> pd.Series:
        """
        MOM: 12-1 month momentum (skip 1 month to avoid short-term reversal).
        """
        ret_12m = self.prices.pct_change(252)
        ret_1m  = self.prices.pct_change(21)
        mom_signal = ret_12m - ret_1m

        daily_mom = pd.Series(index=self.returns.index, dtype=float)
        for dt in self.returns.index:
            if dt not in mom_signal.index:
                continue
            sig = mom_signal.loc[dt].dropna()
            if len(sig) < 4:
                continue
            winners = self.returns.loc[dt, sig.nlargest(max(1, len(sig)//3)).index]
            losers  = self.returns.loc[dt, sig.nsmallest(max(1, len(sig)//3)).index]
            daily_mom.loc[dt] = winners.mean() - losers.mean()

        return daily_mom.rename("MOM")

    def quality_factor(self) -> pd.Series:
        """
        QMJ (Quality Minus Junk): proxy via rolling Sharpe ratio.
        High Sharpe = high quality.
        """
        rolling_mean = self.returns.rolling(126).mean()
        rolling_std  = self.returns.rolling(126).std()
        sharpe       = (rolling_mean / rolling_std.replace(0, np.nan))

        daily_qmj = pd.Series(index=self.returns.index, dtype=float)
        for dt in self.returns.index:
            if dt not in sharpe.index:
                continue
            sig = sharpe.loc[dt].dropna()
            if len(sig) < 4:
                continue
            quality = self.returns.loc[dt, sig.nlargest(max(1, len(sig)//3)).index]
            junk    = self.returns.loc[dt, sig.nsmallest(max(1, len(sig)//3)).index]
            daily_qmj.loc[dt] = quality.mean() - junk.mean()

        return daily_qmj.rename("QMJ")

    def build_factor_returns(self) -> pd.DataFrame:
        """Build all factor returns and return as a DataFrame."""
        log.info("Building factor returns for %d symbols", len(self.prices.columns))
        factors = pd.concat([
            self.market_factor(),
            self.smb_factor(),
            self.momentum_factor(),
        ], axis=1).dropna()

        # HML and QMJ are expensive to compute per-day; compute on available data
        try:
            factors["HML"] = self.hml_factor()
        except Exception as e:
            log.warning("HML construction failed: %s", e)

        try:
            factors["QMJ"] = self.quality_factor()
        except Exception as e:
            log.warning("QMJ construction failed: %s", e)

        return factors.dropna(how="all")


# ─────────────────────────────────────────────────────────
# ROLLING OLS FACTOR MODEL
# ─────────────────────────────────────────────────────────

class FactorModel:
    """
    Rolling OLS regression of asset returns on factor returns.
    y = alpha + beta_MKT * MKT + beta_SMB * SMB + ... + epsilon
    """

    def __init__(self, factor_returns: pd.DataFrame, window: int = 252):
        self.factors = factor_returns
        self.window  = window

    def fit_rolling(self, asset_returns: pd.Series) -> pd.DataFrame:
        """
        Compute rolling factor loadings.
        Returns DataFrame with columns: alpha, beta_*, r_squared, residual_vol, ts
        """
        import statsmodels.api as sm

        aligned = pd.concat([asset_returns.rename("ret"), self.factors], axis=1).dropna()
        if len(aligned) < self.window:
            log.warning("Not enough data for rolling OLS (have %d, need %d)", len(aligned), self.window)
            return pd.DataFrame()

        factor_cols = self.factors.columns.tolist()
        results = []

        for i in range(self.window, len(aligned) + 1):
            window_data = aligned.iloc[i - self.window: i]
            y = window_data["ret"].values
            X = sm.add_constant(window_data[factor_cols].values)

            try:
                res = sm.OLS(y, X).fit()
                row = {"ts": aligned.index[i - 1], "alpha": float(res.params[0])}
                for j, fc in enumerate(factor_cols):
                    row[f"beta_{fc.lower()}"] = float(res.params[j + 1])
                row["r_squared"]    = float(res.rsquared)
                row["residual_vol"] = float(np.std(res.resid) * np.sqrt(TRADING_DAYS))
                results.append(row)
            except Exception as e:
                log.debug("OLS failed at %s: %s", aligned.index[i - 1], e)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results).set_index("ts")
        # Annualise alpha
        df["alpha"] = df["alpha"] * TRADING_DAYS
        return df

    def fit_single(self, asset_returns: pd.Series) -> dict:
        """Full-period OLS — single fit over all available data."""
        import statsmodels.api as sm
        aligned = pd.concat([asset_returns.rename("ret"), self.factors], axis=1).dropna()
        if len(aligned) < 30:
            return {}
        factor_cols = self.factors.columns.tolist()
        y = aligned["ret"].values
        X = sm.add_constant(aligned[factor_cols].values)
        try:
            res  = sm.OLS(y, X).fit()
            out  = {"alpha": float(res.params[0]) * TRADING_DAYS,
                    "r_squared": float(res.rsquared)}
            for j, fc in enumerate(factor_cols):
                out[f"beta_{fc.lower()}"] = float(res.params[j + 1])
            out["residual_vol"] = float(np.std(res.resid) * np.sqrt(TRADING_DAYS))
            return out
        except Exception as e:
            log.error("Full-period OLS failed: %s", e)
            return {}


# ─────────────────────────────────────────────────────────
# PCA STATISTICAL FACTOR MODEL
# ─────────────────────────────────────────────────────────

class PCAFactorModel:
    """
    Extracts statistical factors from returns covariance matrix via PCA.
    """

    def __init__(self, n_components: int = 5):
        self.n_components = n_components
        self.pca          = None
        self.explained_   = None

    def fit(self, returns: pd.DataFrame) -> "PCAFactorModel":
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        clean = returns.dropna(axis=1, thresh=int(len(returns) * 0.8))
        clean = clean.fillna(0)

        scaler = StandardScaler()
        X      = scaler.fit_transform(clean)

        self.pca = PCA(n_components=min(self.n_components, X.shape[1]))
        self.pca.fit(X)
        self.explained_ = self.pca.explained_variance_ratio_
        self._columns   = clean.columns
        self._scaler    = scaler
        log.info("PCA explained variance: %s", self.explained_.round(4))
        return self

    def factor_loadings(self) -> pd.DataFrame:
        """Return loadings matrix (n_symbols x n_factors)."""
        if self.pca is None:
            raise RuntimeError("Model not fitted")
        return pd.DataFrame(
            self.pca.components_.T,
            index=self._columns,
            columns=[f"PC{i+1}" for i in range(self.n_components)],
        )

    def summary(self) -> dict:
        return {
            "n_components": self.n_components,
            "explained_variance_ratio": self.explained_.tolist() if self.explained_ is not None else [],
            "cumulative_explained": float(np.cumsum(self.explained_)[-1]) if self.explained_ is not None else 0.0,
        }
