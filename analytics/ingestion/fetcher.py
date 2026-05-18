#!/usr/bin/env python3
"""
MSRAP Data Fetcher
Called by Spring Boot IngestionService as a subprocess.
Outputs JSON array of OHLCV bars to stdout.
"""

import sys
import json
import logging
import argparse
from datetime import datetime, timedelta, timezone

import yfinance as yf
import pandas as pd
import numpy as np

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [fetcher] %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol",   required=True)
    p.add_argument("--interval", default="1d")
    p.add_argument("--from",     dest="from_date", default=None)
    p.add_argument("--to",       dest="to_date",   default=None)
    return p.parse_args()


def fetch(symbol: str, interval: str, from_date: str, to_date: str) -> pd.DataFrame:
    log.info("Fetching %s interval=%s from=%s to=%s", symbol, interval, from_date, to_date)

    ticker = yf.Ticker(symbol)

    kwargs = {"interval": interval, "auto_adjust": False, "progress": False}
    if from_date:
        kwargs["start"] = from_date
    if to_date:
        kwargs["end"] = to_date

    df = ticker.history(**kwargs)

    if df is None or df.empty:
        log.warning("No data returned for %s", symbol)
        return pd.DataFrame()

    return df


def clean(df: pd.DataFrame, symbol: str) -> list[dict]:
    if df.empty:
        return []

    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Standardise column names from yfinance
    rename = {
        "adj_close": "adj_close",
        "dividends":  None,
        "stock_splits": None,
        "capital_gains": None,
    }
    df = df[[c for c in df.columns if c not in ("dividends", "stock_splits", "capital_gains")]]

    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    # Drop rows where OHLC is null or non-positive
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[df["close"] > 0]
    df = df[df["high"] >= df["low"]]

    records = []
    for ts, row in df.iterrows():
        records.append({
            "ts":        ts.isoformat(),
            "open":      round(float(row["open"]),  4),
            "high":      round(float(row["high"]),  4),
            "low":       round(float(row["low"]),   4),
            "close":     round(float(row["close"]), 4),
            "volume":    int(row.get("volume", 0) or 0),
            "adj_close": round(float(row["adj_close"]), 4) if "adj_close" in row else None,
        })

    log.info("Cleaned %d bars for %s", len(records), symbol)
    return records


def main():
    args = parse_args()

    # Default from_date: 5 years back
    if not args.from_date:
        args.from_date = (datetime.now(timezone.utc) - timedelta(days=1825)).strftime("%Y-%m-%d")

    df = fetch(args.symbol, args.interval, args.from_date, args.to_date)
    records = clean(df, args.symbol)

    # Output JSON to stdout — Spring Boot reads this
    print(json.dumps(records))


if __name__ == "__main__":
    main()
