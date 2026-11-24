"""Fills, exits and costs for one trade, exactly as in docs/rules.md (playbook v2.4).

Prices are Yahoo's split-adjusted (not dividend-adjusted) bars, so limits,
stops and targets match real quotes. Dividends with an ex-date after the fill
day and up to the exit day are added to gross return.

Session counting: the fill day is session 1. A flagged bar (see
engine/quality.BLOCKING) inside a trade is skipped as if it did not exist: it
triggers nothing, is not counted as a session, and its checks move to the next
clean bar. A zero-volume day gives no fill.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

COST = {"regular": 0.003, "smallcap": 0.01}
LIMIT_MULT = 1.005
STOP_MULT, TARGET_MULT = 0.95, 1.08
TRAIL_MULT = 0.94
BREAKEVEN_TRIGGER = 1.04
ATR_STOP, ATR_TARGET = 2.0, 3.0

VARIANTS = {
    "base": {"kind": "base", "sessions": 10},
    "trail": {"kind": "trail", "sessions": 10},
    "breakeven": {"kind": "breakeven", "sessions": 10},
    "atr": {"kind": "atr", "sessions": 10},
    "time5": {"kind": "base", "sessions": 5},
    "time15": {"kind": "base", "sessions": 15},
}


def buy_limit(prior_close: float) -> float:
    return prior_close * LIMIT_MULT


def fill_price(limit: float, open_: float, low: float, volume: float) -> float | None:
    """open <= limit -> open; else low <= limit -> limit; else None (Missed)."""
    if not volume or volume <= 0:
        return None
    if open_ <= limit:
        return open_
    if low <= limit:
        return limit
    return None


def atr14(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ATR. The first value is the mean of the first n true ranges."""
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()],
                   axis=1).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    out = np.full(len(tr), np.nan)
    vals = tr.to_numpy()
    if len(vals) >= n:
        out[n - 1] = vals[:n].mean()
        for i in range(n, len(vals)):
            out[i] = (out[i - 1] * (n - 1) + vals[i]) / n
    return pd.Series(out, index=df.index)


def run(o, h, l, c, v, flagged, cumdiv, i, limit, variant="base", atr=None, cost=0.0):
    """Core loop on plain sequences. i = index of the fill day (session 1).

    cumdiv[k] = total dividends with ex-date on or before bar k.
    Returns a dict with filled, fill, exit_index, exit_price, reason, sessions,
    skipped, dividends, gross, net.
    """
    spec = VARIANTS[variant]
    kind, max_sessions = spec["kind"], spec["sessions"]
    miss = {"filled": False, "fill": math.nan, "exit_index": i, "exit_price": math.nan, "sessions": 0,
            "skipped": 0, "dividends": 0.0, "gross": math.nan, "net": math.nan}
    if flagged[i]:
        return {**miss, "reason": "Missed (flagged)"}
    fill = fill_price(limit, o[i], l[i], v[i])
    if fill is None:
        return {**miss, "reason": "Missed"}

    if kind == "atr":
        if atr is None or not atr > 0:
            raise ValueError("ATR variant needs a positive atr")
        stop, target = fill - ATR_STOP * atr, fill + ATR_TARGET * atr
    else:
        stop, target = fill * STOP_MULT, fill * TARGET_MULT
    floor = stop
    if kind == "trail":
        target = math.inf
    highest = h[i]
    be_armed = kind == "breakeven" and h[i] >= fill * BREAKEVEN_TRIGGER

    def done(k, price, reason, sessions, skipped):
        div = cumdiv[k] - cumdiv[i]
        gross = (price + div) / fill - 1
        return {"filled": True, "fill": fill, "exit_index": k, "exit_price": price, "reason": reason,
                "sessions": sessions, "skipped": skipped, "dividends": div, "gross": gross, "net": gross - cost}

    # Session 1 (fill day): only the stop counts.
    if l[i] <= stop:
        return done(i, stop, "Stop", 1, 0)
    if max_sessions == 1:
        return done(i, c[i], "Time stop", 1, 0)

    sessions, skipped, last = 1, 0, i
    for k in range(i + 1, len(o)):
        if flagged[k]:
            skipped += 1
            continue
        sessions += 1
        last = k
        if kind == "trail":
            stop = max(floor, highest * TRAIL_MULT)
        elif be_armed:
            stop = fill
        if o[k] <= stop:
            return done(k, o[k], "Gap stop", sessions, skipped)
        if o[k] >= target:
            return done(k, o[k], "Gap target", sessions, skipped)
        if l[k] <= stop:
            return done(k, stop, "Stop", sessions, skipped)
        if h[k] >= target:
            return done(k, target, "Target", sessions, skipped)
        if sessions == max_sessions:
            return done(k, c[k], "Time stop", sessions, skipped)
        highest = max(highest, h[k])
        if kind == "breakeven" and h[k] >= fill * BREAKEVEN_TRIGGER:
            be_armed = True
    out = done(last, c[last], "Open", sessions, skipped)
    out["net"] = math.nan  # not closed: excluded from results
    return out


def cumulative_dividends(index: pd.DatetimeIndex, dividends: pd.Series | None) -> np.ndarray:
    """cumdiv[k] = dividends with ex-date <= index[k]. An ex-date on a day with no
    bar counts from the next bar."""
    if dividends is None or len(dividends) == 0:
        return np.zeros(len(index))
    d = dividends[dividends.fillna(0) > 0]
    pos = index.searchsorted(pd.DatetimeIndex(d.index))
    add = np.zeros(len(index) + 1)
    np.add.at(add, pos, d.to_numpy(dtype=float))
    return np.cumsum(add)[: len(index)]


def simulate_trade(df: pd.DataFrame, limit: float, variant: str = "base", atr: float | None = None,
                   cost: float = 0.0, dividends: pd.Series | None = None, flagged=None) -> dict:
    """One trade on a frame whose first row is the fill day (session 1)."""
    n = len(df)
    flagged = np.zeros(n, bool) if flagged is None else np.asarray(flagged, bool)
    res = run(df["open"].tolist(), df["high"].tolist(), df["low"].tolist(), df["close"].tolist(),
              df["volume"].tolist() if "volume" in df else [1] * n, flagged.tolist(),
              cumulative_dividends(df.index, dividends).tolist(), 0, limit, variant, atr, cost)
    res["exit_date"] = df.index[res["exit_index"]]
    return res
