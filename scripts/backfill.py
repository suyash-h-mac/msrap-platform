#!/usr/bin/env python3
"""
scripts/backfill.py — Standalone OHLCV backfill script.

Run outside Docker to seed or refresh historical data for a list of symbols.

Usage:
    python scripts/backfill.py --symbols RELIANCE.NS TCS.NS --days 365
    python scripts/backfill.py --all --days 1825
    python scripts/backfill.py --symbols ^NSEI --interval 1d --days 730
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── Make project root importable ────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
ANALYTICS_DIR = ROOT / "analytics"
sys.path.insert(0, str(ROOT))

from analytics.utils.db import engine, load_ohlcv, save_analytics
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backfill")

NSE_DEFAULT_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "BAJFINANCE.NS", "HINDUNILVR.NS", "WIPRO.NS", "MARUTI.NS",
    "^NSEI", "^NSEBANK",
]


def fetch_symbol(symbol: str, interval: str, from_date: str) -> list[dict]:
    """Call the Python fetcher subprocess and return parsed JSON rows."""
    fetcher = ANALYTICS_DIR / "ingestion" / "fetcher.py"
    cmd = [
        sys.executable, str(fetcher),
        "--symbol", symbol,
        "--interval", interval,
        "--from", from_date,
    ]
    log.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("Fetcher failed for %s: %s", symbol, result.stderr.strip())
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        log.error("JSON parse error for %s: %s", symbol, e)
        return []


def upsert_ohlcv(rows: list[dict], symbol: str, interval: str) -> int:
    """Upsert a batch of OHLCV rows into TimescaleDB."""
    if not rows:
        return 0
    sql = text("""
        INSERT INTO equity_ohlcv (symbol, ts, interval, open, high, low, close, volume, adj_close)
        VALUES (:symbol, :ts, :interval, :open, :high, :low, :close, :volume, :adj_close)
        ON CONFLICT (symbol, ts, interval)
        DO UPDATE SET
            open      = EXCLUDED.open,
            high      = EXCLUDED.high,
            low       = EXCLUDED.low,
            close     = EXCLUDED.close,
            volume    = EXCLUDED.volume,
            adj_close = EXCLUDED.adj_close
    """)
    params = [
        {
            "symbol": symbol,
            "ts": r["ts"],
            "interval": interval,
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r.get("volume", 0),
            "adj_close": r.get("adj_close"),
        }
        for r in rows
    ]
    with engine().begin() as conn:
        conn.execute(sql, params)
    return len(params)


def backfill_symbol(symbol: str, interval: str, days: int, dry_run: bool) -> dict:
    from_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    log.info("Backfilling %s | interval=%s | from=%s", symbol, interval, from_date)

    rows = fetch_symbol(symbol, interval, from_date)
    if not rows:
        log.warning("No data returned for %s", symbol)
        return {"symbol": symbol, "status": "empty", "rows": 0}

    if dry_run:
        log.info("[DRY RUN] Would insert %d rows for %s", len(rows), symbol)
        return {"symbol": symbol, "status": "dry_run", "rows": len(rows)}

    inserted = upsert_ohlcv(rows, symbol, interval)
    log.info("Upserted %d rows for %s", inserted, symbol)
    return {"symbol": symbol, "status": "ok", "rows": inserted}


def main():
    parser = argparse.ArgumentParser(description="MSRAP OHLCV backfill")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--symbols", nargs="+", metavar="SYM", help="Symbols to backfill")
    grp.add_argument("--all", action="store_true", help="Backfill all default NSE symbols")
    parser.add_argument("--interval", default="1d", help="OHLCV interval (default: 1d)")
    parser.add_argument("--days", type=int, default=1825, help="History window in days (default: 1825)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write to DB")
    args = parser.parse_args()

    symbols = NSE_DEFAULT_SYMBOLS if args.all else args.symbols

    log.info("Starting backfill for %d symbol(s) | days=%d | interval=%s",
             len(symbols), args.days, args.interval)

    results = []
    for sym in symbols:
        try:
            r = backfill_symbol(sym, args.interval, args.days, args.dry_run)
        except Exception as e:
            log.error("Error backfilling %s: %s", sym, e, exc_info=True)
            r = {"symbol": sym, "status": "error", "rows": 0, "error": str(e)}
        results.append(r)

    # Summary
    ok    = [r for r in results if r["status"] in ("ok", "dry_run")]
    empty = [r for r in results if r["status"] == "empty"]
    err   = [r for r in results if r["status"] == "error"]
    total = sum(r["rows"] for r in results)

    print("\n── Backfill Summary ──────────────────────────────────")
    print(f"  Symbols  : {len(symbols)}")
    print(f"  OK       : {len(ok)}")
    print(f"  Empty    : {len(empty)}")
    print(f"  Errors   : {len(err)}")
    print(f"  Rows     : {total:,}")
    if err:
        print("\n  Failures:")
        for r in err:
            print(f"    {r['symbol']}: {r.get('error', 'unknown')}")
    print("──────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
