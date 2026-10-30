#!/usr/bin/env python3
"""Task 4 - Fetch from the API, preprocess, load the model, forecast.

(work in progress: steps 1-2 fetch daily sales and build the Task 1 features)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
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
# 2. Preprocess (mirrors the Task 1 notebook)
# --------------------------------------------------------------------------
def build_daily_frame(raw: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """Regular daily calendar ending at the origin; days with no sales become 0.

    Task 1 does the same: a zero means "no recorded sales", not verified zero demand.
    """
    raw = raw.copy()
    raw["date"] = pd.to_datetime(raw["sales_date"]).dt.normalize()
    raw["sales_value"] = pd.to_numeric(raw["daily_sales"], errors="coerce")
    raw["order_count"] = pd.to_numeric(raw["total_orders"], errors="coerce")
    raw = raw.dropna(subset=["date", "sales_value"]).drop_duplicates("date", keep="last")
    raw = raw[raw["date"] <= origin]
    if (raw["sales_value"] < 0).any():
        raise ForecastError("The API returned negative daily sales; refusing to forecast.")

    calendar = pd.date_range(origin - pd.Timedelta(days=HISTORY_DAYS + FETCH_DAYS), origin, freq="D", name="date")
    daily = raw.set_index("date")[["sales_value", "order_count"]].reindex(calendar)

    window = daily.iloc[-HISTORY_DAYS:]
    observed = window["sales_value"].notna().mean()
    if observed < MIN_OBSERVED_FRACTION:
        raise ForecastError(
            f"Only {observed:.0%} of the last {HISTORY_DAYS} days have data in the API "
            f"(need at least {MIN_OBSERVED_FRACTION:.0%}). Not enough history to forecast safely."
        )
    daily = daily.dropna(how="all").reindex(calendar).fillna(0.0)
    return daily.iloc[-HISTORY_DAYS:]


def make_features(daily: pd.DataFrame, window_start: pd.Timestamp, feature_order: list[str]) -> pd.DataFrame:
    """One row of features for the origin day (same definitions as notebook cell 25)."""
    y = daily["sales_value"]
    X = pd.DataFrame(index=daily.index)
    for lag in [0, 1, 6, 7, 13, 27]:
        X[f"sales_lag_{lag}"] = y.shift(lag)
    for window in [7, 28]:
        X[f"sales_mean_{window}"] = y.rolling(window).mean()
        X[f"sales_std_{window}"] = y.rolling(window).std()
        X[f"orders_mean_{window}"] = daily["order_count"].rolling(window).mean()
    X["origin_weekday"] = X.index.dayofweek
    X["next_day_weekday"] = (X.index + pd.Timedelta(days=1)).dayofweek
    X["next_day_month"] = (X.index + pd.Timedelta(days=1)).month
    # The notebook uses the row number from its first day; this is days since window_start.
    X["time_index"] = (X.index - window_start).days

    row = X.iloc[[-1]]
    missing = [c for c in feature_order if c not in row.columns]
    if missing:
        raise ForecastError(f"metadata.json lists features this script cannot build: {missing}")
    row = row[feature_order]
    if row.isna().any(axis=None):
        raise ForecastError("Not enough history to build every feature (need 28 consecutive days).")
    return row


# --------------------------------------------------------------------------
# Model metadata
# --------------------------------------------------------------------------
def load_metadata() -> dict:
    path = ARTIFACT_DIR / "metadata.json"
    if not path.exists():
        print(f"  note: {path} not found; assuming the tuned random forest and notebook defaults")
        return {}
    return json.loads(path.read_text())


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Forecast the next 7 days of Olist merchandise sales.")
    parser.add_argument("--db", choices=["mysql", "mongo"], default="mysql", help="API data source")
    parser.add_argument("--origin", help="Forecast the 7 days after this date (YYYY-MM-DD); default: latest in API")
    args = parser.parse_args()
    try:
        origin = pd.Timestamp(args.origin).normalize() if args.origin else None
        metadata = load_metadata()
        window_start = pd.Timestamp(metadata.get("window_start", DEFAULT_WINDOW_START))
        window_end = pd.Timestamp(metadata.get("window_end", DEFAULT_WINDOW_END))
        raw, origin = fetch_daily_history(args.db, origin, window_end)
        daily = build_daily_frame(raw, origin)
        features = make_features(daily, window_start, metadata.get("features", DEFAULT_FEATURES))
    except ForecastError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    print(f"Fetched {len(raw)} daily records up to {origin.date()}")
    print(features.T)
    return 0


if __name__ == "__main__":
    sys.exit(main())
