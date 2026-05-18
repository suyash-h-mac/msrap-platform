"""
Shared database utilities for MSRAP Python analytics workers.
"""
import os
import logging
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)

def get_engine():
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5432")
    dbname   = os.getenv("DB_NAME", "msrap")
    user     = os.getenv("DB_USER", "msrap")
    password = os.getenv("DB_PASSWORD", "msrap_secret")
    url      = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True, pool_size=5)


_engine = None

def engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def load_ohlcv(symbol: str, interval: str = "1d", days: int = 1825) -> pd.DataFrame:
    """Load OHLCV from TimescaleDB as a DataFrame indexed by ts."""
    sql = """
        SELECT ts, open, high, low, close, volume, adj_close
        FROM equity_ohlcv
        WHERE symbol = :symbol
          AND interval = :interval
          AND ts >= NOW() - INTERVAL ':days days'
        ORDER BY ts ASC
    """
    # Use text() with literal days substitution (not parameter, for interval syntax)
    sql = f"""
        SELECT ts, open, high, low, close, volume, adj_close
        FROM equity_ohlcv
        WHERE symbol = :symbol
          AND interval = :interval
          AND ts >= NOW() - INTERVAL '{days} days'
        ORDER BY ts ASC
    """
    df = pd.read_sql(text(sql), engine(), params={"symbol": symbol, "interval": interval})
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index()
    for col in ["open", "high", "low", "close", "adj_close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    return df.dropna(subset=["close"])


def save_analytics(symbol: str, module: str, records: list[dict]):
    """
    Upsert analytics results.
    records: list of {ts, metric, value, value_str}
    """
    if not records:
        return
    rows = []
    for r in records:
        rows.append({
            "symbol":    symbol,
            "ts":        r["ts"],
            "module":    module,
            "metric":    r["metric"],
            "value":     r.get("value"),
            "value_str": r.get("value_str"),
        })

    sql = text("""
        INSERT INTO analytics_results (symbol, ts, module, metric, value, value_str)
        VALUES (:symbol, :ts, :module, :metric, :value, :value_str)
        ON CONFLICT (symbol, ts, module, metric)
        DO UPDATE SET value = EXCLUDED.value, value_str = EXCLUDED.value_str
    """)
    with engine().begin() as conn:
        conn.execute(sql, rows)
    log.info("Saved %d analytics rows for %s/%s", len(rows), symbol, module)


def save_regime_states(symbol: str, records: list[dict]):
    """Upsert regime state rows."""
    if not records:
        return
    sql = text("""
        INSERT INTO regime_states
            (symbol, ts, state, state_label, prob_state0, prob_state1, prob_state2)
        VALUES
            (:symbol, :ts, :state, :state_label, :prob_state0, :prob_state1, :prob_state2)
        ON CONFLICT (symbol, ts)
        DO UPDATE SET state = EXCLUDED.state,
                      state_label = EXCLUDED.state_label,
                      prob_state0 = EXCLUDED.prob_state0,
                      prob_state1 = EXCLUDED.prob_state1,
                      prob_state2 = EXCLUDED.prob_state2
    """)
    rows = [{"symbol": symbol, **r} for r in records]
    with engine().begin() as conn:
        conn.execute(sql, rows)
    log.info("Saved %d regime states for %s", len(rows), symbol)


def save_factor_loadings(symbol: str, records: list[dict]):
    """Upsert factor loading rows."""
    if not records:
        return
    sql = text("""
        INSERT INTO factor_loadings
            (symbol, ts, window_days, beta_market, beta_size, beta_value,
             beta_momentum, beta_quality, alpha, r_squared, residual_vol)
        VALUES
            (:symbol, :ts, :window_days, :beta_market, :beta_size, :beta_value,
             :beta_momentum, :beta_quality, :alpha, :r_squared, :residual_vol)
        ON CONFLICT (symbol, ts, window_days)
        DO UPDATE SET
            beta_market   = EXCLUDED.beta_market,
            beta_size     = EXCLUDED.beta_size,
            beta_value    = EXCLUDED.beta_value,
            beta_momentum = EXCLUDED.beta_momentum,
            beta_quality  = EXCLUDED.beta_quality,
            alpha         = EXCLUDED.alpha,
            r_squared     = EXCLUDED.r_squared,
            residual_vol  = EXCLUDED.residual_vol
    """)
    rows = [{"symbol": symbol, **r} for r in records]
    with engine().begin() as conn:
        conn.execute(sql, rows)
    log.info("Saved %d factor loadings for %s", len(rows), symbol)
