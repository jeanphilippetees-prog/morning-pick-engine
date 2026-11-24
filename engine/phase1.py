"""Phase 1 run: candidates, 10 years of prices, corrections, eligibility, quality report.

    python -m engine.phase1            # download everything, then clean and report
    python -m engine.phase1 --report   # clean and report from the cache only

Writes (git-ignored):
    data/candidates.csv, data/prices/, data/actions/      raw Yahoo cache
    data/clean/prices/, data/clean/actions/               after docs/corrections.csv
    data/clean/eligibility.parquet                        daily point-in-time eligibility
    data/clean/flags.parquet                              every flagged bar
Writes (committed):
    results/universe_v2.csv, results/data_quality_flags_v2.csv, results/data_quality_v2.md
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone

import pandas as pd

from engine import data, quality, universe

RESULTS = data.ROOT / "results"
CLEAN = data.DATA_DIR / "clean"
YEARS = 10
RUN_STATS = data.DATA_DIR / "phase1_run.json"
VERSION = "v2"


def _start(today: date) -> str:
    return today.replace(year=today.year - YEARS).isoformat()


def build(today: date) -> dict:
    data.DATA_DIR.mkdir(exist_ok=True)
    cands = universe.build_candidates()
    cands.to_csv(data.DATA_DIR / "candidates.csv", index=False)
    logging.info("candidates: %d", len(cands))
    symbols = cands["yahoo"].tolist() + [data.BENCHMARK]
    failed = data.update_cache(symbols, _start(today), full=True)
    stats = {"date": today.isoformat(), "candidates": len(cands), "failed": failed}
    RUN_STATS.write_text(json.dumps(stats, indent=1))
    return stats


def clean_all(cands: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict, list]:
    """Clean every candidate; store cleaned bars, flags and eligibility."""
    corr = data.load_corrections()
    (CLEAN / "prices").mkdir(parents=True, exist_ok=True)
    (CLEAN / "actions").mkdir(parents=True, exist_ok=True)
    flags_all, elig_all, eligibility, dropped = [], [], {}, []
    for sym in cands["yahoo"].tolist() + [data.BENCHMARK]:
        df, acts, flags, cut = quality.clean_history(sym, corr)
        if df is None or df.empty:
            continue
        df.to_parquet(CLEAN / "prices" / f"{sym}.parquet")
        acts.to_parquet(CLEAN / "actions" / f"{sym}.parquet")
        if cut is not None:
            dropped.append({"yahoo": sym, "starts": cut})
        f = flags.copy()
        f.insert(0, "yahoo", sym)
        flags_all.append(f)
        if sym == data.BENCHMARK:
            continue
        blocked = f.loc[f["flag"].isin(quality.BLOCKING), "date"]
        e = universe.daily_eligibility(df, blocked)
        eligibility[sym] = e
        e = e.reset_index()
        e.insert(0, "yahoo", sym)
        elig_all.append(e)
    flags = pd.concat([f for f in flags_all if len(f)], ignore_index=True)
    elig = pd.concat(elig_all, ignore_index=True)
    flags.to_parquet(CLEAN / "flags.parquet")
    elig.to_parquet(CLEAN / "eligibility.parquet")
    return flags, elig, eligibility, dropped


def _md_table(df: pd.DataFrame, index: bool = False) -> str:
    if index:
        df = df.reset_index()
    if df.empty:
        return "_none_\n"
    cols = [" ".join(str(x) for x in c if str(x)) if isinstance(c, tuple) else str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.astype(object).iterrows():
        cells = []
        for v in row:
            if isinstance(v, pd.Timestamp):
                cells.append(v.strftime("%Y-%m-%d"))
            elif isinstance(v, float):
                cells.append(f"{v:,.2f}" if abs(v) >= 1000 else f"{v:.2f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def report(today: date) -> str:
    cands = pd.read_csv(data.DATA_DIR / "candidates.csv")
    stats = json.loads(RUN_STATS.read_text()) if RUN_STATS.exists() else {}
    corr = data.load_corrections()
    flags, elig, eligibility, dropped = clean_all(cands)
    start = pd.Timestamp(_start(today))
    xic = pd.read_parquet(CLEAN / "prices" / f"{data.BENCHMARK}.parquet")
    cal = xic.index

    # Today's snapshot: names eligible at the last close, with their book and type.
    last = elig[elig["date"] == cal[-1]]
    snap = last[last["gate_ok"]].merge(cands[["yahoo", "exchange", "name"]], on="yahoo", how="left")
    snap.insert(1, "ticker", snap["yahoo"].map(data.to_output_ticker))
    snap.insert(3, "type", snap["yahoo"].map(data.security_type))
    snap = snap[["yahoo", "ticker", "book", "type", "date", "close", "value_traded_20d", "zero_volume_20d",
                 "clean_lookback", "exchange", "name"]].rename(columns={"date": "last_date"})
    snap = snap.sort_values(["book", "value_traded_20d"], ascending=[True, False])
    snap.to_csv(RESULTS / f"universe_{VERSION}.csv", index=False, date_format="%Y-%m-%d", float_format="%.4f")

    flags_out = flags.copy()
    flags_out.insert(1, "ticker", flags_out["yahoo"].map(data.to_output_ticker))
    flags_out.sort_values(["ticker", "date", "flag"]).drop(columns="yahoo").to_csv(
        RESULTS / f"data_quality_flags_{VERSION}.csv", index=False, date_format="%Y-%m-%d")

    # Per-ticker summaries on the cleaned data.
    summaries = []
    for sym in list(eligibility) + [data.BENCHMARK]:
        df = pd.read_parquet(CLEAN / "prices" / f"{sym}.parquet")
        acts = pd.read_parquet(CLEAN / "actions" / f"{sym}.parquet")
        s, _ = quality.ticker_summary(sym, df, cal, acts.get("splits"), start)
        e = eligibility.get(sym)
        s["ever_eligible"] = bool(e is not None and e["eligible"].any())
        s["eligible_days"] = int(e["eligible"].sum()) if e is not None else 0
        summaries.append(s)
    summ = pd.DataFrame(summaries)
    summ["ticker"] = summ["yahoo"].map(data.to_output_ticker)
    summ["type"] = summ["yahoo"].map(data.security_type)
    stocks = summ[summ["yahoo"] != data.BENCHMARK]
    xs = summ[summ["yahoo"] == data.BENCHMARK].iloc[0]
    no_data = sorted(set(cands["yahoo"]) - set(summ["yahoo"]))

    def group_table(frame, by):
        return (frame.groupby(by)
                .agg(names=("yahoo", "size"), full_10y=("full_history", "sum"), median_years=("years", "median"),
                     bars=("sessions", "sum"), missing_days=("missing_days", "sum"),
                     zero_volume_days=("zero_volume_days", "sum"), jumps=("jumps", "sum"),
                     gap_jumps=("gap_jumps", "sum"), bad_ohlc=("bad_ohlc", "sum"), bad_print=("bad_print", "sum"),
                     level_shift=("level_shift", "sum"), split_unadjusted=("split_unadjusted", "sum"))
                .reset_index())

    stocks = stocks.assign(group=stocks["ever_eligible"].map({True: "ever eligible", False: "never eligible"}))
    by_group = group_table(stocks, "group")
    by_type = (stocks[stocks["ever_eligible"]].groupby("type")
               .agg(names=("yahoo", "size"), eligible_days=("eligible_days", "sum")).reset_index())
    elig_year = universe.eligibility_by_year(eligibility, cal[cal >= start])
    elig_year.columns = [f"{b} {k}" for b, k in elig_year.columns]
    elig_year = elig_year[["regular gate", "regular eligible", "smallcap gate", "smallcap eligible"]]

    # Corrections: confirm the split jumps disappear and list what was dropped.
    corr_rows = []
    for _, r in corr.iterrows():
        f = flags[(flags["yahoo"] == r["yahoo"]) & (flags["date"] == r["date"])]
        kinds = ", ".join(sorted(set(f["flag"]))) or "none"
        action = {0: "drop history before", 1: "verified real move"}.get(r["ratio"], f"split ratio {r['ratio']:g}")
        corr_rows.append({"ticker": r["ticker"], "date": r["date"], "action": action,
                          "flags on that date after cleaning": kinds})
    corr_tbl = pd.DataFrame(corr_rows)
    splits_clean = corr_tbl[corr_tbl["action"].str.startswith("split")]
    jump_left = splits_clean[splits_clean["flags on that date after cleaning"] != "none"]
    auto = pd.DataFrame(dropped)
    if len(auto):
        auto = auto[~auto["yahoo"].isin(corr["yahoo"])]
        auto = auto.merge(summ[["yahoo", "ticker", "ever_eligible", "eligible_days"]], on="yahoo")
        auto = auto.sort_values("eligible_days", ascending=False)[["ticker", "starts", "ever_eligible", "eligible_days"]]

    def top(col, n=15):
        t = stocks[stocks["ever_eligible"] & (stocks[col] > 0)].sort_values(col, ascending=False).head(n)
        return t[["ticker", col, "sessions", "eligible_days"]]

    jumps = flags[flags["flag"].isin(["jump", "gap_jump"])].merge(summ[["yahoo", "ticker", "ever_eligible"]], on="yahoo")
    jumps_elig = jumps[jumps["ever_eligible"]]
    blocked_share = 1 - elig.loc[elig["gate_ok"], "clean_lookback"].mean()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = [
        "# Data quality report v2",
        "",
        f"As of {today.isoformat()} (generated {now}). Source: Yahoo Finance via yfinance, daily bars "
        f"from {start.date()}; candidates from the public TMX company directory (TSX and TSXV). "
        "Changes from v1 follow the PM review of 2026-11-24: history for every candidate, "
        "docs/corrections.csv applied on load, point-in-time eligibility.",
        "",
        "**Known gaps:** CSE names are not covered (no TMX directory, patchy Yahoo .CN data); the live "
        "trial still covers CSE. Survivorship: Yahoo only has names listed today, so delisted and acquired "
        "names are missing and every backtest on this data is an upper bound.",
        "",
        "## Candidates and download",
        "",
        f"- Candidates after dropping ETFs, funds, split corps, preferreds, debentures, warrants, USD lines and "
        f"capital pool companies: {len(cands)} (REIT and trust units kept, type = unit).",
        f"- Candidates with any Yahoo data: {len(stocks)}; without: {len(no_data)}"
        + (f" ({', '.join(data.to_output_ticker(s) for s in no_data[:40])}{' ...' if len(no_data) > 40 else ''})"
           if no_data else "") + ".",
        f"- Candidates ever eligible (point-in-time, any day since {start.date()}): "
        f"{int(stocks['ever_eligible'].sum())}. Eligible at the last close: "
        f"{int(snap['book'].eq('regular').sum())} regular, {int(snap['book'].eq('smallcap').sum())} small-cap "
        f"(results/universe_{VERSION}.csv).",
        "",
        "Ever-eligible names by type:",
        "",
        _md_table(by_type),
        "## Point-in-time eligibility",
        "",
        "A name can get a signal for session t only if, at the close of t-1: it passes a book gate "
        "(regular: close >= $5 and 20-day average close x volume >= $5M; small-cap: $1 <= close < $5 and "
        ">= $1M), at most 4 of its last 20 sessions had zero volume, t-1 itself traded, and none of its last "
        f"60 sessions carries a blocking flag ({', '.join(sorted(quality.BLOCKING))}).",
        "",
        "Average number of names per session. *gate* = book gate and zero-volume rules; *eligible* = gate "
        "plus a clean 60-session lookback.",
        "",
        _md_table(elig_year, index=True),
        f"The 60-session flag lookback removes {blocked_share:.1%} of name-days that pass the gate.",
        "",
        "## Corrections (docs/corrections.csv)",
        "",
        _md_table(corr_tbl),
        ("All split corrections remove the jump on the split date." if jump_left.empty
         else f"**Split corrections that still show a flag on the split date: {len(jump_left)}.**"),
        "",
        "### Automatic drops",
        "",
        "Level shifts outside corrections.csv are unconfirmed by default: the history before the latest one "
        "is dropped (the name's data starts at the shift). Sorted by eligible days after the drop.",
        "",
        _md_table(auto.head(40) if len(auto) else pd.DataFrame()),
        (f"{len(auto)} names in total; the full list is in results/data_quality_flags_{VERSION}.csv as the "
         "level shift dates." if len(auto) else ""),
        "",
        "## Summary after cleaning",
        "",
        _md_table(by_group),
        f"**XIC.TO benchmark:** {xs['first_date'].date()} to {xs['last_date'].date()}, {xs['sessions']} sessions, "
        f"{xs['zero_volume_days']} zero-volume days, {xs['jumps']} jumps over 40%.",
        "",
        "## Ever-eligible names: missing days",
        "",
        _md_table(top("missing_days")),
        "## Ever-eligible names: zero-volume days",
        "",
        _md_table(top("zero_volume_days")),
        "## Ever-eligible names: jumps over 40%",
        "",
        f"{len(jumps_elig)} flagged bars across {jumps_elig['yahoo'].nunique()} ever-eligible names. "
        "Most recent 20:",
        "",
        _md_table(jumps_elig.sort_values("date", ascending=False).head(20)[["date", "ticker", "flag", "detail"]]),
        "## Ever-eligible names: bad prints and bad OHLC",
        "",
        _md_table(top("bad_print")),
        _md_table(top("bad_ohlc")),
        "## Caveats",
        "",
        "- Survivorship (above). The point-in-time universe reduces, but does not remove, the bias.",
        "- CSE not covered (above).",
        "- Prices are Yahoo's split-adjusted (not dividend-adjusted) bars, so limits, stops and targets "
        "match real quotes; dividends come from Yahoo's dividend history. adj_close is used only for XIC.",
        "- Missed splits are found only when the jump is near a common ratio and the new level holds; "
        "a missed split hidden inside a normal-looking move would not be caught.",
        "",
    ]
    text = "\n".join(out)
    (RESULTS / f"data_quality_{VERSION}.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", action="store_true", help="clean and report from the cache only")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    today = date.today()
    if not args.report:
        build(today)
    report(today)
    print((RESULTS / f"data_quality_{VERSION}.md").resolve())


if __name__ == "__main__":
    main()
