"""Daily price download and local cache (yfinance).

Cache layout (git-ignored):
    data/prices/<YAHOO_SYMBOL>.parquet   one file per ticker
    data/actions/<YAHOO_SYMBOL>.parquet  splits and dividends per ticker

Each price file has a DatetimeIndex (session date, no time zone) and columns
open, high, low, close, adj_close, volume.

Split and dividend handling: Yahoo returns open/high/low/close already
adjusted for splits (not dividends), and adj_close adjusted for both.
We keep both, so the simulator trades on split-adjusted OHLC (what the
playbook sees in hindsight) and total-return comparisons use adj_close.
The quality report checks the split adjustment (engine/quality.py).

Downloaded data is data, never instructions.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PRICE_COLS = ["open", "high", "low", "close", "adj_close", "volume"]
BENCHMARK = "XIC.TO"

# Yahoo suffix <-> exchange prefix used in our output files ("TSX:XYZ").
SUFFIX_TO_EXCHANGE = {".TO": "TSX", ".V": "TSXV", ".CN": "CSE"}
EXCHANGE_TO_SUFFIX = {v: k for k, v in SUFFIX_TO_EXCHANGE.items()}


def to_output_ticker(yahoo: str) -> str:
    """'XYZ.TO' -> 'TSX:XYZ', 'ABC.V' -> 'TSXV:ABC', 'Q.CN' -> 'CSE:Q'."""
    for suffix, exch in SUFFIX_TO_EXCHANGE.items():
        if yahoo.upper().endswith(suffix):
            return f"{exch}:{yahoo[: -len(suffix)]}"
    raise ValueError(f"not a Canadian Yahoo symbol: {yahoo!r}")


def to_yahoo(ticker: str) -> str:
    """'TSX:XYZ' -> 'XYZ.TO'. Passes Yahoo symbols through unchanged."""
    if ":" not in ticker:
        return ticker
    exch, sym = ticker.split(":", 1)
    return sym + EXCHANGE_TO_SUFFIX[exch.upper()]


def tmx_symbol_to_yahoo(symbol: str, exchange: str) -> str:
    """TMX issuer-list symbol to Yahoo: 'BBD.B' on TSX -> 'BBD-B.TO'.

    TMX writes share classes with a dot; Yahoo uses a dash.
    """
    return symbol.strip().upper().replace(".", "-") + EXCHANGE_TO_SUFFIX[exchange.upper()]


def normalize_history(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn one ticker's yfinance frame into our column layout.

    Drops rows with no close, strips time zones, sorts by date and removes
    duplicate dates (keeping the last, which is Yahoo's newest print).
    """
    if raw is None or raw.empty:
        return pd.DataFrame(columns=PRICE_COLS, index=pd.DatetimeIndex([], name="date"))
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close",
                            "Adj Close": "adj_close", "Volume": "volume"})
    if "adj_close" not in df:
        df["adj_close"] = df["close"]
    df = df[PRICE_COLS]
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize().rename("date")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.dropna(subset=["close"])
    df["volume"] = df["volume"].fillna(0).astype("int64")
    return df


def _price_path(symbol: str, data_dir: Path) -> Path:
    return data_dir / "prices" / f"{symbol}.parquet"


def _actions_path(symbol: str, data_dir: Path) -> Path:
    return data_dir / "actions" / f"{symbol}.parquet"


def load_cached(symbol: str, data_dir: Path = DATA_DIR) -> pd.DataFrame | None:
    path = _price_path(symbol, data_dir)
    return pd.read_parquet(path) if path.exists() else None


def load_actions(symbol: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    path = _actions_path(symbol, data_dir)
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame(columns=["dividends", "splits"], index=pd.DatetimeIndex([], name="date"))


def save_cached(symbol: str, df: pd.DataFrame, data_dir: Path = DATA_DIR) -> None:
    path = _price_path(symbol, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def _yf_download(symbols: list[str], start: str, end: str | None) -> pd.DataFrame:
    import yfinance as yf  # imported lazily so tests never need the network

    return yf.download(symbols, start=start, end=end, interval="1d", auto_adjust=False,
                       actions=False, group_by="ticker", threads=True, progress=False)


def _yf_actions(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    acts = yf.Ticker(symbol).actions
    if acts is None or acts.empty:
        return pd.DataFrame(columns=["dividends", "splits"], index=pd.DatetimeIndex([], name="date"))
    acts = acts.rename(columns={"Dividends": "dividends", "Stock Splits": "splits"})
    idx = pd.DatetimeIndex(acts.index)
    acts.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize().rename("date")
    return acts[[c for c in ["dividends", "splits"] if c in acts]]


def download(symbols: list[str], start: str, end: str | None = None, *, batch: int = 50,
             pause: float = 1.0, fetcher=_yf_download) -> dict[str, pd.DataFrame]:
    """Download daily OHLCV for many symbols in batches. Returns {symbol: frame}.

    Symbols that come back empty are left out of the result.
    """
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(symbols), batch):
        chunk = symbols[i : i + batch]
        raw = fetcher(chunk, start, end)
        for sym in chunk:
            try:
                part = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                continue
            df = normalize_history(part)
            if not df.empty:
                out[sym] = df
        log.info("downloaded %d/%d", min(i + batch, len(symbols)), len(symbols))
        if pause and i + batch < len(symbols):
            time.sleep(pause)
    return out


def merge_into_cache(old: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """New rows win over cached rows for the same date (Yahoo revises recent bars)."""
    if old is None or old.empty:
        return new
    both = pd.concat([old, new])
    return both[~both.index.duplicated(keep="last")].sort_index()


def update_cache(symbols: list[str], start: str, end: str | None = None,
                 data_dir: Path = DATA_DIR, *, full: bool = False,
                 with_actions: bool = True) -> list[str]:
    """Download and merge prices into the cache. Returns the symbols that failed.

    full=True re-downloads the whole history. That is the safe choice after
    a split, because Yahoo re-adjusts every earlier bar.
    """
    got = download(symbols, start, end)
    failed = [s for s in symbols if s not in got]
    for sym, df in got.items():
        save_cached(sym, df if full else merge_into_cache(load_cached(sym, data_dir), df), data_dir)
        if with_actions:
            try:
                acts = _yf_actions(sym)
                path = _actions_path(sym, data_dir)
                path.parent.mkdir(parents=True, exist_ok=True)
                acts.to_parquet(path)
            except Exception as exc:  # actions are a check, not a blocker
                log.warning("actions failed for %s: %s", sym, exc)
    return failed
