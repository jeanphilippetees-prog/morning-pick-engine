"""Data-quality checks on cached daily bars.

Bar-level flags (later phases must never trade on a flagged bar):
    jump          |close / previous close - 1| > 40%
    gap_jump      |open / previous close - 1| > 40%
    zero_volume   volume == 0
    bad_ohlc      high < low, open or close outside [low, high], or a price <= 0
    split_unadjusted  a recorded split whose ratio still shows up as a price jump
    possible_split    a jump close to a common split ratio with no split recorded

Ticker-level checks: coverage (first/last date, sessions, years) and missing
days measured against the benchmark (XIC.TO) trading calendar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

JUMP = 0.40
SPLIT_RATIOS = (2, 3, 4, 5, 10, 20, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20)
SPLIT_TOL = 0.08  # relative tolerance when matching a jump to a split ratio


def _near_ratio(r: float, target: float) -> bool:
    return abs(r / target - 1) <= SPLIT_TOL


def bar_flags(df: pd.DataFrame, splits: pd.Series | None = None) -> pd.DataFrame:
    """Return one row per flagged bar: date, flag, detail."""
    out: list[dict] = []
    if df.empty:
        return pd.DataFrame(out, columns=["date", "flag", "detail"])
    prev = df["close"].shift(1)
    ret = df["close"] / prev - 1
    gap = df["open"] / prev - 1
    split_dates = set()
    if splits is not None:
        splits = splits[splits.fillna(0) > 0]
        split_dates = set(splits.index)

    for d, r in ret[ret.abs() > JUMP].items():
        out.append({"date": d, "flag": "jump", "detail": f"close {r:+.1%}"})
        ratio = 1 + r
        if d not in split_dates and any(_near_ratio(ratio, 1 / s) for s in SPLIT_RATIOS):
            out.append({"date": d, "flag": "possible_split",
                        "detail": f"close ratio {ratio:.3f} looks like a split; none recorded"})
    for d, g in gap[gap.abs() > JUMP].items():
        out.append({"date": d, "flag": "gap_jump", "detail": f"open {g:+.1%} vs prior close"})
    for d in df.index[df["volume"] == 0]:
        out.append({"date": d, "flag": "zero_volume", "detail": ""})

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    eps = 1e-4 * c.abs()  # tolerate Yahoo float noise
    bad = ((h < l - eps) | (o > h + eps) | (o < l - eps) | (c > h + eps) | (c < l - eps)
           | (df[["open", "high", "low", "close"]] <= 0).any(axis=1))
    for d in df.index[bad.fillna(False)]:
        out.append({"date": d, "flag": "bad_ohlc",
                    "detail": f"o={o[d]:.4f} h={h[d]:.4f} l={l[d]:.4f} c={c[d]:.4f}"})

    for d, ratio in (splits.items() if splits is not None else []):
        if d not in df.index:
            continue
        i = df.index.get_loc(d)
        if i == 0:
            continue
        r = df["close"].iloc[i] / df["close"].iloc[i - 1]
        if _near_ratio(r, 1 / ratio):
            out.append({"date": d, "flag": "split_unadjusted",
                        "detail": f"split {ratio:g}:1 but close ratio {r:.3f}"})
    res = pd.DataFrame(out, columns=["date", "flag", "detail"])
    return res.sort_values(["date", "flag"]).reset_index(drop=True)


def missing_days(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Benchmark sessions inside the ticker's own date range with no bar."""
    if df.empty:
        return pd.DatetimeIndex([])
    cal = calendar[(calendar >= df.index.min()) & (calendar <= df.index.max())]
    return cal.difference(df.index)


def ticker_summary(sym: str, df: pd.DataFrame, calendar: pd.DatetimeIndex,
                   splits: pd.Series | None, start: pd.Timestamp) -> tuple[dict, pd.DataFrame]:
    flags = bar_flags(df, splits)
    miss = missing_days(df, calendar)
    n_splits = int((splits.fillna(0) > 0).sum()) if splits is not None else 0
    first = df.index.min() if len(df) else pd.NaT
    summary = {
        "yahoo": sym,
        "first_date": first,
        "last_date": df.index.max() if len(df) else pd.NaT,
        "sessions": len(df),
        "years": round((df.index.max() - first).days / 365.25, 2) if len(df) else 0.0,
        "full_history": bool(len(df)) and first <= start + pd.Timedelta(days=7),
        "missing_days": len(miss),
        "missing_pct": len(miss) / max(len(miss) + len(df), 1),
        "zero_volume_days": int((df["volume"] == 0).sum()) if len(df) else 0,
        "jumps": int((flags["flag"] == "jump").sum()),
        "gap_jumps": int((flags["flag"] == "gap_jump").sum()),
        "bad_ohlc": int((flags["flag"] == "bad_ohlc").sum()),
        "splits_recorded": n_splits,
        "split_unadjusted": int((flags["flag"] == "split_unadjusted").sum()),
        "possible_split": int((flags["flag"] == "possible_split").sum()),
    }
    flags.insert(0, "yahoo", sym)
    if len(miss):
        flags = pd.concat([flags, pd.DataFrame({"yahoo": sym, "date": miss, "flag": "missing_day", "detail": ""})],
                          ignore_index=True)
    return summary, flags


def flagged_bar_share(flags: pd.DataFrame, total_bars: int) -> float:
    real = flags[flags["flag"] != "missing_day"]
    return len(real.drop_duplicates(["yahoo", "date"])) / total_bars if total_bars else np.nan
