#!/usr/bin/env python3
"""
scripts/health_check.py — Verify DB connectivity and data freshness.

Checks:
  1. TimescaleDB connection
  2. Hypertable existence
  3. Row counts per table
  4. Data freshness (latest ts per symbol in equity_ohlcv)
  5. Analytics coverage (symbols with recent analytics results)

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --verbose
    python scripts/health_check.py --staleness-days 3
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics.utils.db import engine
from sqlalchemy import text

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("health_check")

HYPERTABLES = [
    "equity_ohlcv",
    "options_chain",
    "futures_oi",
    "analytics_results",
    "regime_states",
    "factor_loadings",
]

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD  = "\033[1m"

ok   = lambda s: f"{GREEN}✓ {s}{RESET}"
fail = lambda s: f"{RED}✗ {s}{RESET}"
warn = lambda s: f"{YELLOW}⚠ {s}{RESET}"


def check_connection(conn) -> bool:
    try:
        conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(fail(f"DB connection failed: {e}"))
        return False


def check_hypertables(conn, verbose: bool) -> list[str]:
    missing = []
    rows = conn.execute(text("""
        SELECT hypertable_name
        FROM timescaledb_information.hypertables
    """)).fetchall()
    existing = {r[0] for r in rows}

    for ht in HYPERTABLES:
        if ht in existing:
            if verbose:
                print(ok(f"Hypertable exists: {ht}"))
        else:
            print(fail(f"Hypertable MISSING: {ht}"))
            missing.append(ht)
    return missing


def check_row_counts(conn, verbose: bool):
    for table in ["equity_ohlcv", "analytics_results", "regime_states", "factor_loadings"]:
        try:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            msg = f"{table}: {count:,} rows"
            if count == 0:
                print(warn(msg + "  (empty)"))
            elif verbose:
                print(ok(msg))
            else:
                print(f"  {msg}")
        except Exception as e:
            print(fail(f"{table}: query error — {e}"))


def check_freshness(conn, staleness_days: int, verbose: bool) -> list[str]:
    stale = []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=staleness_days)

    rows = conn.execute(text("""
        SELECT symbol, MAX(ts) AS latest_ts
        FROM equity_ohlcv
        WHERE interval = '1d'
        GROUP BY symbol
        ORDER BY symbol
    """)).fetchall()

    if not rows:
        print(warn("No OHLCV data found at all"))
        return []

    for symbol, latest_ts in rows:
        if latest_ts is None:
            continue
        # Make timezone-aware if naive
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(tz=timezone.utc) - latest_ts).days
        if latest_ts < cutoff:
            msg = f"{symbol}: last data {latest_ts.date()} ({days_old}d ago) — STALE"
            print(warn(msg))
            stale.append(symbol)
        elif verbose:
            print(ok(f"{symbol}: last data {latest_ts.date()} ({days_old}d ago)"))

    return stale


def check_analytics_coverage(conn, verbose: bool):
    rows = conn.execute(text("""
        SELECT module, COUNT(DISTINCT symbol) AS sym_count, MAX(ts) AS latest_ts
        FROM analytics_results
        GROUP BY module
        ORDER BY module
    """)).fetchall()

    if not rows:
        print(warn("No analytics_results rows found"))
        return

    for module, sym_count, latest_ts in rows:
        msg = f"analytics_results[{module}]: {sym_count} symbols, latest={latest_ts}"
        if verbose or True:
            print(f"  {msg}")

    # Regime states
    rs = conn.execute(text(
        "SELECT COUNT(DISTINCT symbol) FROM regime_states"
    )).scalar()
    print(f"  regime_states: {rs} symbols")

    # Factor loadings
    fl = conn.execute(text(
        "SELECT COUNT(DISTINCT symbol) FROM factor_loadings"
    )).scalar()
    print(f"  factor_loadings: {fl} symbols")


def main():
    parser = argparse.ArgumentParser(description="MSRAP health check")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--staleness-days", type=int, default=5,
                        help="Days before OHLCV data is considered stale (default: 5)")
    args = parser.parse_args()

    print(f"\n{BOLD}── MSRAP Health Check ─────────────────────────────────{RESET}")
    print(f"  Timestamp : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    issues = 0

    try:
        with engine().connect() as conn:
            print(ok("TimescaleDB connected"))

            # Hypertables
            print(f"\n{BOLD}Hypertables:{RESET}")
            missing_ht = check_hypertables(conn, args.verbose)
            issues += len(missing_ht)

            # Row counts
            print(f"\n{BOLD}Row counts:{RESET}")
            check_row_counts(conn, args.verbose)

            # Data freshness
            print(f"\n{BOLD}Data freshness (stale threshold: {args.staleness_days}d):{RESET}")
            stale = check_freshness(conn, args.staleness_days, args.verbose)
            if not stale and not args.verbose:
                print(ok("All symbols up-to-date"))
            issues += len(stale)

            # Analytics coverage
            print(f"\n{BOLD}Analytics coverage:{RESET}")
            check_analytics_coverage(conn, args.verbose)

    except Exception as e:
        print(fail(f"Could not connect to database: {e}"))
        print("\nCheck DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD env vars.")
        sys.exit(2)

    print(f"\n{BOLD}── Result ─────────────────────────────────────────────{RESET}")
    if issues == 0:
        print(ok("All checks passed"))
        sys.exit(0)
    else:
        print(warn(f"{issues} issue(s) found — review output above"))
        sys.exit(1)


if __name__ == "__main__":
    main()
