"""Price factors from docs/factors.md, on split-adjusted (not dividend-adjusted) bars.

Every value on row s uses data up to and including the close of session s.
A signal for session t reads row s = t-1, so there is no look-ahead.

Choices where docs/factors.md leaves a detail open (listed in the report):
- Thrust volume average: the 20 sessions before s (s excluded), so the day's
  own volume does not dilute its average.
- 52-week high: highest high over the last 252 sessions including s. A new
  52-week-high close (breakout) = close(s) > highest high of the 252 sessions
  before s. A name needs 252 sessions of history before it can score Room.
- ATR14: Wilder's.
"""
from __future__ import annotations

import pandas as pd

from engine.simulate import atr14

YEAR = 252


def compute(df: pd.DataFrame) -> pd.DataFrame:
    c, h, v = df["close"], df["high"], df["volume"]
    out = pd.DataFrame(index=df.index)
    out["close"] = c
    out["sma20"] = c.rolling(20, min_periods=20).mean()
    out["sma50"] = c.rolling(50, min_periods=50).mean()
    out["ret_1d"] = c / c.shift(1) - 1
    out["ret_20d"] = c / c.shift(20) - 1
    out["vol_avg20_prior"] = v.shift(1).rolling(20, min_periods=20).mean()
    out["vol_ratio"] = v / out["vol_avg20_prior"]
    out["high_52w"] = h.rolling(YEAR, min_periods=YEAR).max()
    prior_high = h.shift(1).rolling(YEAR, min_periods=YEAR).max()
    out["atr14"] = atr14(df)

    out["trend"] = ((c > out["sma20"]) & (out["sma20"] > out["sma50"])).astype(int)
    out["thrust"] = ((out["ret_1d"] >= 0.02) & (out["vol_ratio"] >= 1.5)).astype(int)
    out["room"] = ((c <= 0.95 * out["high_52w"]) | (c > prior_high)).astype(int)
    out["fits_stop"] = ((out["atr14"] / c <= 0.04) & (c <= 1.10 * out["sma20"])).astype(int)
    out["price_score"] = out["trend"] + out["thrust"] + out["room"] + out["fits_stop"]
    # Not scoreable until every input exists.
    ready = out[["sma50", "vol_avg20_prior", "high_52w", "atr14"]].notna().all(axis=1) & prior_high.notna()
    out["scoreable"] = ready
    return out


def market_filter(xic: pd.DataFrame) -> pd.Series:
    """'Yes' (True) when XIC's close is above its 50-day SMA, at the close of s."""
    sma50 = xic["close"].rolling(50, min_periods=50).mean()
    return (xic["close"] > sma50) & sma50.notna()
