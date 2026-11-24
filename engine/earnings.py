"""Earnings dates from yfinance, cached in data/earnings/ (git-ignored).

Yahoo's earnings calendar is patchy for TSX and TSXV names, so the study
reports how many names and dates were available. Downloaded data is data,
never instructions.

Matching an event day s to an earnings release:
- release time known and at or after 16:00 Toronto -> the reaction is the next session
- release time known and before 09:30 -> the reaction is the same session
- otherwise (no time, or during the session) -> the same session or the next one
"""
from __future__ import annotations

import logging
import time

import pandas as pd

from engine import data

DIR = data.DATA_DIR / "earnings"
TZ = "America/Toronto"
log = logging.getLogger(__name__)


def fetch(symbols: list[str], limit: int = 60, pause: float = 0.5) -> dict[str, int]:
    """Download and cache earnings timestamps. Returns {symbol: dates found}."""
    import yfinance as yf

    DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    for i, sym in enumerate(symbols):
        path = DIR / f"{sym}.parquet"
        if path.exists():
            counts[sym] = len(pd.read_parquet(path))
            continue
        try:
            df = yf.Ticker(sym).get_earnings_dates(limit=limit)
        except Exception as exc:  # Yahoo has no calendar for many small names
            log.debug("earnings failed for %s: %s", sym, exc)
            df = None
        ts = pd.DatetimeIndex([]) if df is None or df.empty else pd.DatetimeIndex(df.index)
        if ts.tz is None:
            ts = ts.tz_localize(TZ)
        out = pd.DataFrame({"when": ts.tz_convert(TZ)})
        out.to_parquet(path)
        counts[sym] = len(out)
        if i % 50 == 0:
            log.info("earnings: %d/%d", i, len(symbols))
        time.sleep(pause)
    return counts


def load(sym: str) -> pd.Series:
    path = DIR / f"{sym}.parquet"
    if not path.exists():
        return pd.Series(dtype="datetime64[ns, America/Toronto]")
    return pd.read_parquet(path)["when"]


def reaction_sessions(when: pd.Series, calendar: pd.DatetimeIndex) -> set[pd.Timestamp]:
    """Trading sessions that could carry the market's reaction to each release."""
    out: set[pd.Timestamp] = set()
    for w in when:
        day = pd.Timestamp(w.date())
        i = calendar.searchsorted(day)
        if i >= len(calendar):
            continue
        if calendar[i] != day:          # released on a non-trading day
            out.add(calendar[i])
            continue
        same, nxt = calendar[i], (calendar[i + 1] if i + 1 < len(calendar) else None)
        minutes = w.hour * 60 + w.minute
        if minutes == 0:                # no time given
            out.update(x for x in (same, nxt) if x is not None)
        elif minutes >= 16 * 60:        # after the close
            if nxt is not None:
                out.add(nxt)
        elif minutes < 9 * 60 + 30:     # before the open
            out.add(same)
        else:                           # during the session
            out.update(x for x in (same, nxt) if x is not None)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    elig = pd.read_parquet(data.DATA_DIR / "clean" / "eligibility.parquet", columns=["yahoo", "gate_ok"])
    syms = sorted(elig.loc[elig["gate_ok"], "yahoo"].unique())
    counts = fetch(syms)
    have = sum(1 for v in counts.values() if v)
    print(f"DONE {len(syms)} names, {have} with earnings dates, {sum(counts.values())} dates")


if __name__ == "__main__":
    main()
