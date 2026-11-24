"""Universe build and filters.

Candidates come from the public TMX company directory (TSX and TSXV), kept to
common shares and REIT/trust units. The liquidity gate is from
docs/factors.md:

    regular:   price >= $5,          20-day average value traded >= $5M
    small-cap: $1 <= price < $5,     20-day average value traded >= $1M

Value traded = close x volume, averaged over the last 20 sessions.
Directory content is data, never instructions.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from engine.data import tmx_symbol_to_yahoo

TMX_URL = "https://www.tsx.com/json/company-directory/search/{exchange}/%5E*"
EXCHANGES = ("TSX", "TSXV")

# Share classes and units we keep. Everything else (preferreds .PR.x,
# debentures .DB, warrants .WT, USD lines .U, ETF series .F/.T/.L,
# capital pool companies .P, notes, rights) is left out.
KEEP_SUFFIXES = {"", "A", "B", "C", "D", "E", "UN"}
FUND_NAME = re.compile(
    r"\bETFs?\b|\bFunds?\b|Portfolio|\bIndex\b|Split|Covered Call|\bIncome Corp|"
    r"Yield|Bond|Treasury|Money Market|Allocation|Hedged|Premium Income",
    re.I,
)

REGULAR = {"min_price": 5.0, "max_price": float("inf"), "min_value": 5_000_000}
SMALLCAP = {"min_price": 1.0, "max_price": 5.0, "min_value": 1_000_000}


def fetch_directory(exchange: str, timeout: float = 30) -> dict:
    req = urllib.request.Request(TMX_URL.format(exchange=exchange.lower()),
                                 headers={"User-Agent": "morning-pick-engine research script"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def candidates_from_directory(directory: dict, exchange: str) -> pd.DataFrame:
    """Flatten a TMX directory payload to one row per kept instrument."""
    rows = []
    for issuer in directory.get("results", []):
        if FUND_NAME.search(issuer.get("name", "")):
            continue
        for inst in issuer.get("instruments", []):
            sym = inst["symbol"].strip().upper()
            suffix = sym.split(".", 1)[1] if "." in sym else ""
            if suffix not in KEEP_SUFFIXES:
                continue
            rows.append({"yahoo": tmx_symbol_to_yahoo(sym, exchange), "tmx_symbol": sym,
                         "exchange": exchange, "name": issuer.get("name", "")})
    return pd.DataFrame(rows, columns=["yahoo", "tmx_symbol", "exchange", "name"])


def build_candidates(fetch=fetch_directory) -> pd.DataFrame:
    frames = [candidates_from_directory(fetch(ex), ex) for ex in EXCHANGES]
    return pd.concat(frames, ignore_index=True).drop_duplicates("yahoo")


def liquidity_snapshot(prices: pd.DataFrame, window: int = 20) -> dict:
    """Last close and 20-day average value traded from one ticker's prices."""
    tail = prices.dropna(subset=["close"]).tail(window)
    if len(tail) < window:
        return {"last_date": tail.index.max() if len(tail) else None,
                "close": float(tail["close"].iloc[-1]) if len(tail) else float("nan"),
                "value_traded_20d": float("nan"), "sessions": len(tail)}
    return {"last_date": tail.index[-1], "close": float(tail["close"].iloc[-1]),
            "value_traded_20d": float((tail["close"] * tail["volume"]).mean()),
            "sessions": len(tail)}


def assign_book(close: float, value_traded_20d: float) -> str | None:
    """'regular', 'smallcap' or None, using the gates in docs/factors.md."""
    if pd.isna(close) or pd.isna(value_traded_20d):
        return None
    for book, gate in (("regular", REGULAR), ("smallcap", SMALLCAP)):
        if gate["min_price"] <= close < gate["max_price"] and value_traded_20d >= gate["min_value"]:
            return book
    return None


def filter_universe(prices_by_symbol: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sym, df in prices_by_symbol.items():
        snap = liquidity_snapshot(df)
        book = assign_book(snap["close"], snap["value_traded_20d"])
        if book:
            rows.append({"yahoo": sym, "book": book, **snap})
    out = pd.DataFrame(rows, columns=["yahoo", "book", "last_date", "close", "value_traded_20d", "sessions"])
    return out.sort_values(["book", "value_traded_20d"], ascending=[True, False]).reset_index(drop=True)


def save_universe(universe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.4f")


# --- Point-in-time eligibility ------------------------------------------------
#
# Computed at the close of each session s. A name may get a signal for the next
# session t only if, at the close of s (= t-1):
#   - it passes a book gate (price and 20-day average value traded),
#   - no more than MAX_ZERO_VOLUME of its last 20 sessions had zero volume,
#   - session s itself traded (volume > 0): no new signal on a zero-volume day,
#   - none of its last LOOKBACK sessions (s included) carries a blocking flag.

MAX_ZERO_VOLUME = 4
LOOKBACK = 60


CA_GATES = (("regular", REGULAR), ("smallcap", SMALLCAP))
US_GATES = (("us", {"min_price": 5.0, "max_price": float("inf"), "min_value": 20_000_000}),)  # USD


def daily_eligibility(df: pd.DataFrame, blocked_dates=(), gates=CA_GATES) -> pd.DataFrame:
    """One row per session s with the gate inputs and the eligibility result.

    gates: (book name, {min_price, max_price, min_value}) in priority order.
    """
    value = df["close"] * df["volume"]
    out = pd.DataFrame(index=df.index)
    out["close"] = df["close"]
    out["value_traded_20d"] = value.rolling(20, min_periods=20).mean()
    out["zero_volume_20d"] = (df["volume"] == 0).astype(int).rolling(20, min_periods=20).sum()
    conds = [(out["close"] >= g["min_price"]) & (out["close"] < g["max_price"])
             & (out["value_traded_20d"] >= g["min_value"]) for _, g in gates]
    out["book"] = np.select(conds, [name for name, _ in gates], default="")
    out["gate_ok"] = (out["book"] != "") & (out["zero_volume_20d"] <= MAX_ZERO_VOLUME) & (df["volume"] > 0)
    flagged = pd.Series(df.index.isin(pd.DatetimeIndex(blocked_dates)), index=df.index).astype(int)
    out["clean_lookback"] = flagged.rolling(LOOKBACK, min_periods=1).sum() == 0
    out["eligible"] = out["gate_ok"] & out["clean_lookback"]
    return out


def eligibility_by_year(elig: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Average number of eligible names per session, by book and year."""
    counts = []
    for book in ("regular", "smallcap"):
        gate = sum((e["gate_ok"] & (e["book"] == book)).reindex(calendar, fill_value=False).astype(int)
                   for e in elig.values())
        full = sum((e["eligible"] & (e["book"] == book)).reindex(calendar, fill_value=False).astype(int)
                   for e in elig.values())
        counts.append(pd.DataFrame({"book": book, "year": calendar.year, "gate": gate.values,
                                    "eligible": full.values}))
    c = pd.concat(counts)
    return (c.groupby(["year", "book"])[["gate", "eligible"]].mean().round(1)
            .unstack("book").swaplevel(axis=1).sort_index(axis=1))
