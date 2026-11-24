"""Data-quality checks on cached daily bars.

Bar-level flags (later phases must never trade on a flagged bar):
    jump          |close / previous close - 1| > 40%
    gap_jump      |open / previous close - 1| > 40%
    zero_volume   volume == 0
    bad_ohlc      high < low, open or close outside [low, high], or a price <= 0
    split_unadjusted  a recorded split whose ratio still shows up as a price jump
    level_shift       a split-sized jump (ratio near 2, 3, 4, 5, 10, 20 or the
                      inverse) with no split recorded, where the new price level
                      holds. Either an unrecorded split (history before it is on
                      the wrong scale) or a real crash or spike: price alone
                      cannot tell them apart, so each one needs a hand check
    bad_print         a split-sized jump that reverts: the level does not hold, or
                      an opposite jump follows within FLIP_WINDOW sessions
                      (thin names flipping between two ticks)

Ticker-level checks: coverage (first/last date, sessions, years) and missing
days measured against the benchmark (XIC.TO) trading calendar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

JUMP = 0.40
SPLIT_RATIOS = (2, 3, 4, 5, 10, 20, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20)
SPLIT_TOL = 0.08  # relative tolerance when matching a jump to a split ratio
LEVEL_WINDOW = 5  # sessions after the jump used to tell a level shift from a bad print
FLIP_WINDOW = 20  # an opposite split-sized jump this close means price flip-flopping
# Yahoo also records stock dividends and REIT distribution consolidations as
# tiny "splits" (0.97, 1.02 ...). Those are too small to check against a jump.
MINOR_SPLIT = (0.8, 1.25)


def is_minor_split(ratio: float) -> bool:
    return MINOR_SPLIT[0] < ratio < MINOR_SPLIT[1]


LEVEL_TOL = 0.15  # looser: the price keeps moving in the sessions around the split


def _near_ratio(r: float, target: float, tol: float = SPLIT_TOL) -> bool:
    return abs(r / target - 1) <= tol


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

    jumps = ret[ret.abs() > JUMP]
    for d, r in jumps.items():
        out.append({"date": d, "flag": "jump", "detail": f"close {r:+.1%}"})
    sized = [(df.index.get_loc(d), d, 1 + r) for d, r in jumps.items()
             if d not in split_dates and any(_near_ratio(1 + r, 1 / s) for s in SPLIT_RATIOS)]
    for i, d, ratio in sized:
        flip = any(j != i and abs(j - i) <= FLIP_WINDOW and _near_ratio(ratio * rj, 1.0, LEVEL_TOL)
                   for j, _, rj in sized)
        level = df["close"].iloc[i : i + LEVEL_WINDOW].median() / df["close"].iloc[i - 1]
        if not flip and _near_ratio(level, ratio, LEVEL_TOL):
            out.append({"date": d, "flag": "level_shift",
                        "detail": f"price level x{level:.3f} and holds; no split recorded"})
        else:
            why = "opposite jump within %d sessions" % FLIP_WINDOW if flip else f"level x{level:.3f}"
            out.append({"date": d, "flag": "bad_print", "detail": f"close ratio {ratio:.3f}, reverts ({why})"})
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
        if d not in df.index or is_minor_split(ratio):
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
    rec = splits[splits.fillna(0) > 0] if splits is not None else pd.Series(dtype=float)
    n_splits = int((~rec.map(is_minor_split)).sum()) if len(rec) else 0
    n_minor = int(rec.map(is_minor_split).sum()) if len(rec) else 0
    first = df.index.min() if len(df) else pd.NaT
    summary = {
        "yahoo": sym,
        "first_date": first,
        "last_date": df.index.max() if len(df) else pd.NaT,
        "sessions": len(df),
        "years": round((df.index.max() - first).days / 365.25, 2) if len(df) else 0.0,
        "full_history": bool(len(df) and first <= start + pd.Timedelta(days=7)),
        "missing_days": len(miss),
        "missing_pct": len(miss) / max(len(miss) + len(df), 1),
        "zero_volume_days": int((df["volume"] == 0).sum()) if len(df) else 0,
        "jumps": int((flags["flag"] == "jump").sum()),
        "gap_jumps": int((flags["flag"] == "gap_jump").sum()),
        "bad_ohlc": int((flags["flag"] == "bad_ohlc").sum()),
        "splits_recorded": n_splits,
        "minor_adjustments": n_minor,
        "split_unadjusted": int((flags["flag"] == "split_unadjusted").sum()),
        "level_shift": int((flags["flag"] == "level_shift").sum()),
        "bad_print": int((flags["flag"] == "bad_print").sum()),
    }
    flags.insert(0, "yahoo", sym)
    if len(miss):
        flags = pd.concat([flags, pd.DataFrame({"yahoo": sym, "date": miss, "flag": "missing_day", "detail": ""})],
                          ignore_index=True)
    return summary, flags


def flagged_bar_share(flags: pd.DataFrame, total_bars: int) -> float:
    real = flags[flags["flag"] != "missing_day"]
    return len(real.drop_duplicates(["yahoo", "date"])) / total_bars if total_bars else np.nan
