"""Phase 1 run: build the universe, download 10 years of prices, report data quality.

    python -m engine.phase1            # full run
    python -m engine.phase1 --report   # rebuild the report from the cache only

Writes:
    data/candidates.csv, data/prices/*.parquet, data/actions/*.parquet  (git-ignored)
    results/universe_v1.csv
    results/data_quality_flags_v1.csv
    results/data_quality_v1.md
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timezone

import pandas as pd

from engine import data, quality, universe

RESULTS = data.ROOT / "results"
YEARS = 10


def _start(today: date) -> str:
    return today.replace(year=today.year - YEARS).isoformat()


def build(today: date) -> tuple[pd.DataFrame, list[str], list[str]]:
    data.DATA_DIR.mkdir(exist_ok=True)
    cands = universe.build_candidates()
    cands.to_csv(data.DATA_DIR / "candidates.csv", index=False)
    logging.info("candidates: %d", len(cands))

    screen_start = (pd.Timestamp(today) - pd.Timedelta(days=60)).date().isoformat()
    recent = data.download(cands["yahoo"].tolist(), screen_start)
    uni = universe.filter_universe(recent)
    uni = uni.merge(cands[["yahoo", "exchange", "name"]], on="yahoo", how="left")
    uni.insert(1, "ticker", uni["yahoo"].map(data.to_output_ticker))
    universe.save_universe(uni, RESULTS / "universe_v1.csv")
    no_recent = sorted(set(cands["yahoo"]) - set(recent))
    logging.info("universe: %d (%d candidates had no recent data)", len(uni), len(no_recent))

    symbols = uni["yahoo"].tolist() + [data.BENCHMARK]
    failed = data.update_cache(symbols, _start(today), full=True)
    return uni, failed, no_recent


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_none_\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if isinstance(v, pd.Timestamp):
                cells.append(v.strftime("%Y-%m-%d"))
            elif isinstance(v, float):
                cells.append(f"{v:.2f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def report(today: date, failed: list[str] | None = None, no_recent: list[str] | None = None) -> str:
    uni = pd.read_csv(RESULTS / "universe_v1.csv")
    start = pd.Timestamp(_start(today))
    xic = data.load_cached(data.BENCHMARK)
    if xic is None:
        raise SystemExit("XIC.TO is not in the cache; run without --report first")
    cal = xic.index

    summaries, all_flags, total_bars = [], [], 0
    for sym in [data.BENCHMARK] + uni["yahoo"].tolist():
        df = data.load_cached(sym)
        if df is None:
            continue
        acts = data.load_actions(sym)
        s, f = quality.ticker_summary(sym, df, cal, acts.get("splits"), start)
        summaries.append(s)
        all_flags.append(f)
        total_bars += len(df)
    summ = pd.DataFrame(summaries).merge(uni[["yahoo", "ticker", "book"]], on="yahoo", how="left")
    summ["book"] = summ["book"].fillna("benchmark")
    flags = pd.concat(all_flags, ignore_index=True)
    flags.sort_values(["yahoo", "date", "flag"]).to_csv(
        RESULTS / "data_quality_flags_v1.csv", index=False, date_format="%Y-%m-%d")

    failed = failed if failed is not None else sorted(set(uni["yahoo"]) - set(summ["yahoo"]))
    stocks = summ[summ["book"] != "benchmark"]
    xs = summ[summ["book"] == "benchmark"].iloc[0]
    by_book = (stocks.groupby("book")
               .agg(names=("yahoo", "size"), full_10y=("full_history", "sum"),
                    median_years=("years", "median"), sessions=("sessions", "sum"),
                    missing_days=("missing_days", "sum"), zero_volume_days=("zero_volume_days", "sum"),
                    jumps=("jumps", "sum"), gap_jumps=("gap_jumps", "sum"), bad_ohlc=("bad_ohlc", "sum"),
                    splits_recorded=("splits_recorded", "sum"), split_unadjusted=("split_unadjusted", "sum"),
                    possible_split=("possible_split", "sum"))
               .reset_index())
    exch = uni.groupby(["book", "exchange"]).size().unstack(fill_value=0).reset_index()

    def top(col, n=15, extra=()):
        t = stocks[stocks[col] > 0].sort_values(col, ascending=False).head(n)
        return t[["ticker", "book", col, *extra]]

    jump_rows = (flags[flags["flag"].isin(["jump", "gap_jump"])]
                 .merge(summ[["yahoo", "ticker", "book"]], on="yahoo")
                 .sort_values("date", ascending=False))
    split_issue = (flags[flags["flag"].isin(["split_unadjusted", "possible_split"])]
                   .merge(summ[["yahoo", "ticker"]], on="yahoo"))
    bars_flagged = quality.flagged_bar_share(flags, total_bars)

    yrs_bins = pd.cut(stocks["years"], [-0.01, 1, 3, 5, 9.9, 99], labels=["<1y", "1-3y", "3-5y", "5-9.9y", "10y"])
    coverage = yrs_bins.value_counts().reindex(["10y", "5-9.9y", "3-5y", "1-3y", "<1y"]).rename_axis("history").reset_index(name="names")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = [
        "# Data quality report v1",
        "",
        f"As of {today.isoformat()} (generated {now}). Source: Yahoo Finance via yfinance, daily bars "
        f"from {start.date()} to the last session. Candidates: public TMX company directory (TSX and TSXV).",
        "",
        "## Universe",
        "",
        "Gates from docs/factors.md on the last 20 sessions: regular = close >= $5 and average "
        "close x volume >= $5M; small-cap = $1 <= close < $5 and >= $1M.",
        "",
        _md_table(exch),
        f"- Candidates in the directory after dropping ETFs, funds, preferreds, debentures, warrants, "
        f"USD lines and capital pool companies: see data/candidates.csv.",
        f"- Candidates with no recent Yahoo data: {len(no_recent) if no_recent is not None else 'n/a (report-only run)'}.",
        f"- Universe names whose 10-year download failed: {len(failed)}"
        + (f" ({', '.join(failed[:30])}{' ...' if len(failed) > 30 else ''})" if failed else "") + ".",
        "",
        "## Summary by book",
        "",
        _md_table(by_book),
        f"Flagged bars (any flag except missing days): {bars_flagged:.3%} of {total_bars:,} bars.",
        "",
        "## Coverage",
        "",
        "Names with less than 10 years listed later (IPOs, spin-offs, moves from TSXV) or have a gap at Yahoo.",
        "",
        _md_table(coverage),
        "**XIC.TO benchmark:** "
        f"{xs['first_date'].date()} to {xs['last_date'].date()}, {xs['sessions']} sessions, "
        f"{xs['zero_volume_days']} zero-volume days, {xs['jumps']} jumps over 40%. "
        "Missing days are measured against XIC's own calendar, so XIC shows 0 by construction.",
        "",
        "## Missing days",
        "",
        "XIC sessions inside each name's own first-to-last range with no bar for that name.",
        "",
        _md_table(top("missing_days", extra=("sessions",))),
        "## Zero-volume days",
        "",
        "These bars cannot be filled (docs: require volume on the fill day).",
        "",
        _md_table(top("zero_volume_days", extra=("sessions",))),
        "## Suspicious jumps (over 40%)",
        "",
        f"{len(jump_rows)} flagged bars across {jump_rows['yahoo'].nunique()} names. Most recent 25:",
        "",
        _md_table(jump_rows.head(25)[["date", "ticker", "book", "flag", "detail"]]),
        "## Split checks",
        "",
        f"- Splits recorded by Yahoo across the universe: {int(stocks['splits_recorded'].sum())}.",
        f"- Recorded splits still visible as a price jump (adjustment failed): {int(stocks['split_unadjusted'].sum())}.",
        f"- Split-sized jumps (ratio near 2, 3, 4, 5, 10, 20 or their inverse) with no recorded split: "
        f"{int(stocks['possible_split'].sum())}.",
        "",
        _md_table(split_issue[["date", "ticker", "flag", "detail"]].head(30)),
        "## Bad OHLC bars",
        "",
        "High below low, open or close outside the day's range, or a price <= 0.",
        "",
        _md_table(top("bad_ohlc", extra=("sessions",))),
        "## Caveats",
        "",
        "- Survivorship: the universe is today's listed, liquid names. Delisted and acquired names are "
        "missing, and names are picked on today's liquidity, so any backtest on it is an upper bound.",
        "- CSE names are not in this universe: the TMX directory covers TSX and TSXV only.",
        "- Yahoo's OHLC is split-adjusted but not dividend-adjusted; adj_close covers both. Yahoo "
        "re-adjusts history after each split, so the cache is re-downloaded in full on each phase 1 run.",
        "- Every flagged bar is listed in results/data_quality_flags_v1.csv; later phases must not trade on them.",
        "",
    ]
    text = "\n".join(out)
    (RESULTS / "data_quality_v1.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", action="store_true", help="rebuild the report from the cache only")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    today = date.today()
    if args.report:
        report(today)
    else:
        _, failed, no_recent = build(today)
        report(today, failed, no_recent)
    print((RESULTS / "data_quality_v1.md").resolve())


if __name__ == "__main__":
    main()
