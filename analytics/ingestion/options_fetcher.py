"""
analytics/ingestion/options_fetcher.py
---------------------------------------
Fetches NSE options chain data via yfinance and persists to the
`options_chain` TimescaleDB hypertable.

Schema (from docker/init.sql):
  (symbol, ts, expiry, strike, option_type, last_price, bid, ask,
   volume, open_interest, iv, delta, gamma, theta, vega)

Usage (standalone):
    python analytics/ingestion/options_fetcher.py --symbol RELIANCE.NS
    python analytics/ingestion/options_fetcher.py --symbol ^NSEI --expiries 2
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import text

# ── Make package importable from repo root ───────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.utils.db import engine

log = logging.getLogger(__name__)

# ── Greeks placeholder (yfinance doesn't supply live greeks) ─────────────────
# Options greeks are not available from yfinance; columns are inserted as NULL.
# A future enhancement can compute Black-Scholes greeks from IV + spot price.

_UPSERT_SQL = text("""
    INSERT INTO options_chain
        (symbol, ts, expiry, strike, option_type,
         last_price, bid, ask, volume, open_interest,
         iv, delta, gamma, theta, vega)
    VALUES
        (:symbol, :ts, :expiry, :strike, :option_type,
         :last_price, :bid, :ask, :volume, :open_interest,
         :iv, :delta, :gamma, :theta, :vega)
    ON CONFLICT (symbol, ts, expiry, strike, option_type)
    DO UPDATE SET
        last_price    = EXCLUDED.last_price,
        bid           = EXCLUDED.bid,
        ask           = EXCLUDED.ask,
        volume        = EXCLUDED.volume,
        open_interest = EXCLUDED.open_interest,
        iv            = EXCLUDED.iv,
        delta         = EXCLUDED.delta,
        gamma         = EXCLUDED.gamma,
        theta         = EXCLUDED.theta,
        vega          = EXCLUDED.vega
""")


# ── Core fetch logic ─────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    """Coerce a value to float, returning None on failure."""
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    try:
        f = float(val)
        return None if pd.isna(f) else int(f)
    except (TypeError, ValueError):
        return None


def _build_rows(
    symbol: str,
    expiry_date: str,
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    snapshot_ts: datetime,
) -> list[dict]:
    """Convert yfinance option chain DataFrames into DB row dicts."""
    rows = []
    for opt_type, df in [("CE", calls), ("PE", puts)]:
        for _, row in df.iterrows():
            rows.append({
                "symbol":        symbol,
                "ts":            snapshot_ts,
                "expiry":        expiry_date,
                "strike":        _safe_float(row.get("strike")),
                "option_type":   opt_type,
                "last_price":    _safe_float(row.get("lastPrice")),
                "bid":           _safe_float(row.get("bid")),
                "ask":           _safe_float(row.get("ask")),
                "volume":        _safe_int(row.get("volume")),
                "open_interest": _safe_int(row.get("openInterest")),
                "iv":            _safe_float(row.get("impliedVolatility")),
                # Greeks not supplied by yfinance — stored as NULL
                "delta": None,
                "gamma": None,
                "theta": None,
                "vega":  None,
            })
    return rows


def fetch_options_chain(
    symbol: str,
    n_expiries: int = 4,
    dry_run: bool = False,
) -> dict:
    """
    Fetch the options chain for ``symbol`` across the nearest ``n_expiries``
    expiry dates and upsert into the options_chain table.

    Returns a summary dict:
      {symbol, expiries_fetched, rows_upserted, status}
    """
    log.info("Fetching options chain for %s (n_expiries=%d)", symbol, n_expiries)
    snapshot_ts = datetime.now(tz=timezone.utc)

    try:
        ticker = yf.Ticker(symbol)
        all_expiries = ticker.options  # tuple of date strings "YYYY-MM-DD"
    except Exception as e:
        log.error("yfinance Ticker init failed for %s: %s", symbol, e)
        return {"symbol": symbol, "status": "error", "expiries_fetched": 0,
                "rows_upserted": 0, "error": str(e)}

    if not all_expiries:
        log.warning("No options expiries available for %s", symbol)
        return {"symbol": symbol, "status": "no_options", "expiries_fetched": 0,
                "rows_upserted": 0}

    expiries_to_fetch = list(all_expiries[:n_expiries])
    log.info("Expiries to fetch: %s", expiries_to_fetch)

    all_rows: list[dict] = []

    for expiry in expiries_to_fetch:
        try:
            chain = ticker.option_chain(expiry)
            calls = chain.calls if hasattr(chain, "calls") else pd.DataFrame()
            puts  = chain.puts  if hasattr(chain, "puts")  else pd.DataFrame()

            if calls.empty and puts.empty:
                log.warning("Empty chain for %s expiry=%s", symbol, expiry)
                continue

            rows = _build_rows(symbol, expiry, calls, puts, snapshot_ts)
            all_rows.extend(rows)
            log.info("  %s: %d calls, %d puts → %d rows",
                     expiry, len(calls), len(puts), len(rows))

        except Exception as e:
            log.error("Failed fetching expiry %s for %s: %s", expiry, symbol, e)
            continue

    if not all_rows:
        log.warning("No rows to insert for %s", symbol)
        return {"symbol": symbol, "status": "empty", "expiries_fetched": len(expiries_to_fetch),
                "rows_upserted": 0}

    if dry_run:
        log.info("[DRY RUN] Would upsert %d rows for %s", len(all_rows), symbol)
        return {"symbol": symbol, "status": "dry_run",
                "expiries_fetched": len(expiries_to_fetch), "rows_upserted": len(all_rows)}

    # Filter out rows with NULL strike (can't insert without PK field)
    valid_rows = [r for r in all_rows if r["strike"] is not None]
    if len(valid_rows) < len(all_rows):
        log.warning("Dropped %d rows with null strike", len(all_rows) - len(valid_rows))

    with engine().begin() as conn:
        conn.execute(_UPSERT_SQL, valid_rows)

    log.info("Upserted %d options rows for %s", len(valid_rows), symbol)
    return {
        "symbol":           symbol,
        "status":           "ok",
        "expiries_fetched": len(expiries_to_fetch),
        "rows_upserted":    len(valid_rows),
    }


# ── Load latest snapshot from DB ────────────────────────────────────────────

def load_options_chain(
    symbol: str,
    expiry: Optional[str] = None,
    latest_only: bool = True,
) -> pd.DataFrame:
    """
    Read options chain from DB for the given symbol.

    Args:
        symbol:      Ticker symbol
        expiry:      Filter to a specific expiry date (YYYY-MM-DD). None = all.
        latest_only: If True, return only the most recent snapshot ts.
    """
    expiry_clause = "AND expiry = :expiry" if expiry else ""
    ts_clause = """
        AND ts = (
            SELECT MAX(ts) FROM options_chain
            WHERE symbol = :symbol
        )
    """ if latest_only else ""

    sql = text(f"""
        SELECT symbol, ts, expiry, strike, option_type,
               last_price, bid, ask, volume, open_interest, iv
        FROM options_chain
        WHERE symbol = :symbol
          {expiry_clause}
          {ts_clause}
        ORDER BY expiry, strike, option_type
    """)

    params: dict = {"symbol": symbol}
    if expiry:
        params["expiry"] = expiry

    df = pd.read_sql(sql, engine(), params=params)
    for col in ["last_price", "bid", "ask", "iv"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="MSRAP options chain fetcher")
    parser.add_argument("--symbol",   required=True, help="Ticker (e.g. RELIANCE.NS)")
    parser.add_argument("--expiries", type=int, default=4,
                        help="Number of near-term expiries to fetch (default: 4)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Fetch but do not write to DB")
    args = parser.parse_args()

    result = fetch_options_chain(
        symbol=args.symbol,
        n_expiries=args.expiries,
        dry_run=args.dry_run,
    )

    print(f"\nResult: {result}")
    sys.exit(0 if result["status"] in ("ok", "dry_run") else 1)


if __name__ == "__main__":
    main()
