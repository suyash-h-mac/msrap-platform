#!/usr/bin/env python3
"""
scripts/run_analytics.py — Manually trigger all analytics workers for a symbol list.

Runs volatility, regime, and factor workers in sequence (or selectively).

Usage:
    python scripts/run_analytics.py --symbols RELIANCE.NS TCS.NS
    python scripts/run_analytics.py --all --workers vol regime
    python scripts/run_analytics.py --symbols ^NSEI --workers factor
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYTICS_DIR = ROOT / "analytics"
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("run_analytics")

NSE_DEFAULT_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "BAJFINANCE.NS", "HINDUNILVR.NS", "WIPRO.NS", "MARUTI.NS",
    "^NSEI", "^NSEBANK",
]

WORKER_SCRIPTS = {
    "vol":    ANALYTICS_DIR / "volatility" / "vol_worker.py",
    "regime": ANALYTICS_DIR / "regime"     / "regime_worker.py",
    "factor": ANALYTICS_DIR / "factor"     / "factor_worker.py",
}


def run_worker(worker_name: str, symbol: str, timeout: int = 300) -> dict:
    """Run a single analytics worker subprocess for the given symbol."""
    script = WORKER_SCRIPTS[worker_name]
    cmd = [sys.executable, str(script), "--symbol", symbol]
    log.info("Running %s worker for %s ...", worker_name, symbol)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            log.info("  ✓ %s/%s OK", worker_name, symbol)
            return {"worker": worker_name, "symbol": symbol, "status": "ok"}
        else:
            stderr = result.stderr.strip()
            log.error("  ✗ %s/%s FAILED:\n%s", worker_name, symbol, stderr)
            return {"worker": worker_name, "symbol": symbol, "status": "error", "detail": stderr}
    except subprocess.TimeoutExpired:
        log.error("  ✗ %s/%s TIMEOUT after %ds", worker_name, symbol, timeout)
        return {"worker": worker_name, "symbol": symbol, "status": "timeout"}
    except Exception as e:
        log.error("  ✗ %s/%s EXCEPTION: %s", worker_name, symbol, e)
        return {"worker": worker_name, "symbol": symbol, "status": "error", "detail": str(e)}


def main():
    parser = argparse.ArgumentParser(description="MSRAP analytics runner")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--symbols", nargs="+", metavar="SYM")
    grp.add_argument("--all", action="store_true")
    parser.add_argument(
        "--workers", nargs="+",
        choices=list(WORKER_SCRIPTS.keys()),
        default=list(WORKER_SCRIPTS.keys()),
        help="Workers to run (default: all)",
    )
    parser.add_argument("--timeout", type=int, default=300,
                        help="Per-worker timeout in seconds (default: 300)")
    args = parser.parse_args()

    symbols = NSE_DEFAULT_SYMBOLS if args.all else args.symbols
    workers = args.workers

    log.info("Running workers %s for %d symbol(s)", workers, len(symbols))

    results = []
    for sym in symbols:
        for worker in workers:
            r = run_worker(worker, sym, args.timeout)
            results.append(r)

    ok      = [r for r in results if r["status"] == "ok"]
    errors  = [r for r in results if r["status"] in ("error", "timeout")]

    print("\n── Analytics Run Summary ─────────────────────────────")
    print(f"  Tasks    : {len(results)}")
    print(f"  OK       : {len(ok)}")
    print(f"  Failed   : {len(errors)}")
    if errors:
        print("\n  Failures:")
        for r in errors:
            print(f"    [{r['status']}] {r['worker']}/{r['symbol']}: {r.get('detail', '')[:120]}")
    print("──────────────────────────────────────────────────────")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
