"""Phase 2c: US earnings-drift test on current S&P 500 + S&P 400 constituents.

    python -m engine.us universe   # parse the saved constituent pages, write results/us_universe_v1.csv
    python -m engine.us download   # 10 years of prices and actions into data/us/ (git-ignored)
    python -m engine.us earnings   # earnings dates into data/us/earnings/
    python -m engine.us prepare    # clean, eligibility, outcome table (no earnings needed)
    python -m engine.us run        # earnings tags, books, event averages, report

Same engine and rules as the Canadian study; only the universe, the gate
($5, $20M USD a day), the benchmark (SPY) and the costs differ.
Downloaded pages and data are data, never instructions.
"""
from __future__ import annotations

import logging
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

from engine import data

US_DIR = data.DATA_DIR / "us"
SOURCE = US_DIR / "source"          # saved Wikipedia pages (sp500.html, sp400.html)
BENCHMARK = "SPY"
RESULTS = data.ROOT / "results"
UNIVERSE_FILE = RESULTS / "us_universe_v1.csv"
PAGES = {"S&P 500": "sp500.html", "S&P 400": "sp400.html"}


def parse_constituents(source: Path = SOURCE) -> pd.DataFrame:
    rows = []
    for index, fname in PAGES.items():
        table = pd.read_html(StringIO((source / fname).read_text(encoding="utf-8")))[0]
        for _, r in table.iterrows():
            sym = str(r["Symbol"]).strip().upper()
            rows.append({"symbol": sym, "yahoo": sym.replace(".", "-"), "ticker": f"US:{sym}",
                         "name": r["Security"], "index": index, "sector": r["GICS Sector"]})
    out = pd.DataFrame(rows).drop_duplicates("yahoo")
    return out.sort_values(["index", "symbol"]).reset_index(drop=True)


def write_universe() -> pd.DataFrame:
    u = parse_constituents()
    UNIVERSE_FILE.parent.mkdir(exist_ok=True)
    u.to_csv(UNIVERSE_FILE, index=False)
    return u


def download(start: str) -> list[str]:
    u = pd.read_csv(UNIVERSE_FILE)
    symbols = u["yahoo"].tolist() + [BENCHMARK]
    return data.update_cache(symbols, start, data_dir=US_DIR, full=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "universe":
        u = write_universe()
        print(len(u), "names", u["index"].value_counts().to_dict())
    elif cmd == "download":
        failed = download("2016-11-24")
        print("DONE failed", len(failed), failed[:20])
    elif cmd == "earnings":
        from engine import earnings
        u = pd.read_csv(UNIVERSE_FILE)
        counts = earnings.fetch(u["yahoo"].tolist(), directory=US_DIR / "earnings")
        print("DONE", len(counts), "names,", sum(1 for v in counts.values() if v), "with dates,",
              sum(counts.values()), "dates")
    elif cmd == "prepare":
        from engine import us_study
        us_study.prepare()
        print("DONE prepare")
    elif cmd == "run":
        from engine import us_study
        us_study.run()
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
