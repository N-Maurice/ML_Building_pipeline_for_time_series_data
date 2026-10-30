#!/usr/bin/env python3
"""Task 4 - Fetch from the API, preprocess, load the model, forecast.

(work in progress: step 1 fetches daily sales from the Task 3 API)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
ARTIFACT_DIR = Path(os.environ.get("MODEL_DIR", Path(__file__).resolve().parent / "models"))

HORIZON = 7
HISTORY_DAYS = 28   # longest look-back in the Task 1 features (lag 27, 28-day windows)
FETCH_DAYS = 35     # request a little extra so a short gap cannot starve the features
MIN_OBSERVED_FRACTION = 0.75  # refuse to forecast from a history that is mostly filler zeros
REQUEST_TIMEOUT = 30

# Fallbacks when metadata.json is missing. Must match the notebook (cell 25).
DEFAULT_WINDOW_START = "2017-01-01"
DEFAULT_WINDOW_END = "2018-08-31"
DEFAULT_FEATURES = [
    "sales_lag_0", "sales_lag_1", "sales_lag_6", "sales_lag_7", "sales_lag_13", "sales_lag_27",
    "sales_mean_7", "sales_std_7", "orders_mean_7",
    "sales_mean_28", "sales_std_28", "orders_mean_28",
    "origin_weekday", "next_day_weekday", "next_day_month", "time_index",
]


class ForecastError(Exception):
    """A problem the user can fix (API down, too little history, missing model)."""


# --------------------------------------------------------------------------
# 1. Fetch
# --------------------------------------------------------------------------
def api_get(path: str, **params) -> dict:
    url = f"{API_BASE}{path}"
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise ForecastError(
            f"Could not reach the API at {API_BASE} ({exc.__class__.__name__}). "
            "Start it with: uvicorn api.main:app --port 8000"
        ) from exc
    if response.status_code == 404:
        raise ForecastError(f"{path} returned 404: {response.json().get('detail', 'no data found')}")
    if response.status_code == 503:
        raise ForecastError(f"{path} returned 503: that database is down (check /health).")
    response.raise_for_status()
    return response.json()


def fetch_daily_history(
    db: str, origin: pd.Timestamp | None, last_reliable_day: pd.Timestamp | None = None
) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Return raw daily rows from the API and the forecast origin date.

    Without an explicit origin we use the API's latest day, but not past the end of the
    Task 1 analysis window: Olist's final weeks are sparsely recorded (see the notebook).
    """
    if origin is None:
        latest = api_get(f"/{db}/sales/daily/latest")
        origin = pd.Timestamp(latest["sales_date"]).normalize()
        if last_reliable_day is not None and origin > last_reliable_day:
            print(f"      latest API day is {origin.date()}; using {last_reliable_day.date()}, "
                  "the end of the Task 1 analysis window (later days are sparsely recorded)")
            origin = last_reliable_day
    start = origin - pd.Timedelta(days=FETCH_DAYS - 1)
    payload = api_get(
        f"/{db}/sales/daily",
        start_date=start.date().isoformat(),
        end_date=origin.date().isoformat(),
        limit=FETCH_DAYS + 5,
    )
    rows = payload.get("records", [])
    if not rows:
        raise ForecastError(
            f"The {db} API returned no daily sales between {start.date()} and {origin.date()}. "
            "Load the Olist data into the database first (POST /demo/seed only adds one demo order)."
        )
    return pd.DataFrame(rows), origin


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Forecast the next 7 days of Olist merchandise sales.")
    parser.add_argument("--db", choices=["mysql", "mongo"], default="mysql", help="API data source")
    parser.add_argument("--origin", help="Forecast the 7 days after this date (YYYY-MM-DD); default: latest in API")
    args = parser.parse_args()
    try:
        origin = pd.Timestamp(args.origin).normalize() if args.origin else None
        raw, origin = fetch_daily_history(args.db, origin, pd.Timestamp(DEFAULT_WINDOW_END))
    except ForecastError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    print(f"Fetched {len(raw)} daily records up to {origin.date()}")
    print(raw.tail())
    return 0


if __name__ == "__main__":
    sys.exit(main())
