"""Report helpers and the backtest v2 report (results/backtest_v2.md, results/trades_v2.csv).

The v1 files (results/backtest_v1.md, results/trades_v1.csv) are kept as reviewed;
the code that wrote them is in git history (commit 2b6ed05).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd

from engine import backtest as bt, data, files

MIN_TRADES = 100  # the spec's bar for a result to mean something

METRIC_COLS = [  # (column, label, kind)
    ("trades", "Trades", "int"), ("trades_per_week", "Per week", "f2"), ("win_rate", "Win", "pct"),
    ("avg_win", "Avg win", "pct"), ("avg_loss", "Avg loss", "pct"), ("expectancy", "Net exp.", "pct2"),
    ("profit_factor", "PF", "f2"), ("max_drawdown", "Max DD", "pct"), ("exit_Stop", "Stop", "pct"),
    ("exit_Gap stop", "Gap stop", "pct"), ("exit_Target", "Target", "pct"), ("exit_Gap target", "Gap tgt", "pct"),
    ("exit_Time stop", "Time", "pct"), ("avg_hold", "Hold", "f1"), ("pct_days_invested", "Invested", "pct"),
    ("cagr", "CAGR", "pct"), ("cagr_vs_xic", "vs XIC", "pct"),
]
KEY = ["book", "setup", "variant"]
TRADE_COLS = ["book", "setup", "variant", "period", "ticker", "type", "universe", "strict", "s", "fill_date",
              "exit_date", "price_score", "trend", "thrust", "room", "fits_stop", "ret_1d", "vol_ratio", "gap_1d",
              "ret_20d_prior", "limit", "fill", "exit_price", "reason", "sessions", "skipped", "dividends", "gross",
              "net", "shares", "xic_window_return"]


def fmt(v, kind: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    if isinstance(v, float) and math.isinf(v):
        return "inf"
    return {"int": lambda x: f"{int(x):,}", "f1": lambda x: f"{x:.1f}", "f2": lambda x: f"{x:.2f}",
            "pct": lambda x: f"{x:.1%}", "pct2": lambda x: f"{x:+.2%}"}[kind](v)


def table(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_none_\n"
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(r) + " |" for r in rows]) + "\n"


def wide(results: pd.DataFrame) -> pd.DataFrame:
    """One row per configuration with <metric>_IS and <metric>_OOS columns and verdicts."""
    labels = [c for c in results.columns if c in ("threshold", "market_filter", "event")]
    w = results.pivot_table(index=KEY + labels, columns="period", aggfunc="first")
    w.columns = [f"{m}_{p}" for m, p in w.columns]
    w = w.reset_index()
    w["beats_random_OOS"] = w["expectancy_OOS"] > w["rand_p95_OOS"]
    w["beats_xic_OOS"] = w["cagr_OOS"] > w["xic_cagr_OOS"]
    w["enough_OOS"] = w["trades_OOS"] >= MIN_TRADES
    w["edge_OOS"] = w["beats_random_OOS"] & w["beats_xic_OOS"] & w["enough_OOS"]
    w["beats_random_IS"] = w["expectancy_IS"] > w["rand_p95_IS"]
    return w


def config_name(r) -> str:
    return f"{r['book']} / {r['setup']} / {r['variant']}"


def head_cols(bench: str = "XIC") -> list[str]:
    return ["Config", "OOS trades", "OOS net exp.", "OOS win", "OOS PF", "OOS CAGR", f"{bench} CAGR",
            "Random p95", "Pctile vs random", "IS net exp.", "IS trades"]


HEAD_COLS = head_cols()


def head_rows(df: pd.DataFrame) -> list[list[str]]:
    return [[config_name(r), fmt(r["trades_OOS"], "int"), fmt(r["expectancy_OOS"], "pct2"),
             fmt(r["win_rate_OOS"], "pct"), fmt(r["profit_factor_OOS"], "f2"), fmt(r["cagr_OOS"], "pct"),
             fmt(r["xic_cagr_OOS"], "pct"), fmt(r["rand_p95_OOS"], "pct2"), fmt(r["rand_pctile_OOS"], "pct"),
             fmt(r["expectancy_IS"], "pct2"), fmt(r["trades_IS"], "int")] for _, r in df.iterrows()]


def summary_lines(w: pd.DataFrame, what: str, bench: str = "XIC") -> list[str]:
    n_enough = int(w["enough_OOS"].sum())
    e = w[w["enough_OOS"]]
    both = w[w["enough_OOS"] & (w["trades_IS"] >= MIN_TRADES) & w["beats_random_IS"] & w["beats_random_OOS"]]
    ranked = e.sort_values("expectancy_OOS", ascending=False)
    edge = w[w["edge_OOS"]]
    out = [
        f"- {len(w)} configurations ({what}). {n_enough} have at least {MIN_TRADES} out-of-sample trades.",
        f"- Out-of-sample, among those {n_enough}: {int((e['expectancy_OOS'] > 0).sum())} have positive net "
        f"expectancy after costs, {int(e['beats_random_OOS'].sum())} beat the random-entry baseline (net expectancy "
        f"above the 95th percentile of {bt.RANDOM_RUNS} random runs), {int(e['beats_xic_OOS'].sum())} beat {bench}'s "
        f"CAGR, and **{len(edge)} do both** (the spec's bar for a playbook proposal).",
        f"- Configurations that beat random in both periods with {MIN_TRADES}+ trades each: {len(both)}.",
        "",
    ]
    if len(edge):
        out += ["### Configurations that clear the bar out-of-sample", "", table(head_cols(bench), head_rows(edge)), ""]
    out += [f"### Best out-of-sample configurations ({MIN_TRADES}+ OOS trades, by net expectancy)", "",
            table(head_cols(bench), head_rows(ranked.head(10))),
            "### Worst out-of-sample configurations", "",
            table(head_cols(bench), head_rows(ranked.tail(5).iloc[::-1])),
            "Ranking on out-of-sample results is descriptive only. Picking the top row and calling it the rule "
            "would be tuning on the out-of-sample period; any change goes through the playbook's proposal process.",
            ""]
    return out


def matrix(w: pd.DataFrame, books, setups) -> list[str]:
    out = []
    for book in books:
        rows = []
        for setup in setups:
            cells = [setup]
            for var in bt.VARIANTS:
                r = w[(w["book"] == book.name) & (w["setup"] == setup) & (w["variant"] == var)]
                if r.empty:
                    cells.append("-")
                    continue
                r = r.iloc[0]
                mark = ("R" if r["beats_random_OOS"] else "") + ("X" if r["beats_xic_OOS"] else "")
                cells.append(f"{fmt(r['expectancy_IS'], 'pct2')} \\| {fmt(r['expectancy_OOS'], 'pct2')} "
                             f"({fmt(r['trades_OOS'], 'int')}{', ' + mark if mark else ''})")
            rows.append(cells)
        fill = ", strict fill" if book.strict else ""
        out += [f"### {book.name} ({book.universe} universe, cost {book.cost:.1%} round trip{fill})", "",
                table(["Setup"] + bt.VARIANTS, rows)]
    return out


def full_tables(w: pd.DataFrame, books, setups, bench: str = "XIC") -> list[str]:
    hdr = ["Exit"] + [f"{lab} IS / OOS" for _, lab, _ in METRIC_COLS]
    out = []
    for book in books:
        for setup in setups:
            sub = w[(w["book"] == book.name) & (w["setup"] == setup)]
            if sub.empty:
                continue
            rows = [[r["variant"]] + [f"{fmt(r[c + '_IS'], k)} / {fmt(r[c + '_OOS'], k)}" for c, _, k in METRIC_COLS]
                    for _, r in sub.iterrows()]
            base = sub[sub["variant"] == "base"].iloc[0]
            rand_cells = {"trades": ("rand_trades", "f1"), "win_rate": ("rand_win_rate", "pct"),
                          "expectancy": ("rand_expectancy", "pct2"), "profit_factor": ("rand_pf", "f2")}
            rows.append(["random (base exit)"] + [
                (f"{fmt(base[rand_cells[c][0] + '_IS'], rand_cells[c][1])} / "
                 f"{fmt(base[rand_cells[c][0] + '_OOS'], rand_cells[c][1])}") if c in rand_cells else "-"
                for c, _, _ in METRIC_COLS])
            rows.append([f"{bench} buy and hold"] + [
                f"{fmt(base['xic_cagr_IS'], 'pct')} / {fmt(base['xic_cagr_OOS'], 'pct')}" if c == "cagr" else "-"
                for c, _, _ in METRIC_COLS])
            rr = sub.set_index("variant")
            out += [f"### {book.name}, {setup}", "", table(hdr, rows),
                    "Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): "
                    + "; ".join(f"{v} {fmt(rr.at[v, 'rand_expectancy_IS'], 'pct2')} / "
                                f"{fmt(rr.at[v, 'rand_expectancy_OOS'], 'pct2')} "
                                f"({fmt(rr.at[v, 'rand_p5_OOS'], 'pct2')} to {fmt(rr.at[v, 'rand_p95_OOS'], 'pct2')})"
                                for v in bt.VARIANTS if v in rr.index), ""]
    return out


def by_year(yearly: pd.DataFrame, books, setups, variant: str = "base", bench: str = "XIC") -> list[str]:
    out = []
    for book in books:
        rows = []
        for setup in setups:
            y = yearly[(yearly["book"] == book.name) & (yearly["setup"] == setup) & (yearly["variant"] == variant)]
            for _, r in y.iterrows():
                rows.append([str(r["year"]), setup, fmt(r["trades"], "int"), fmt(r["win_rate"], "pct"),
                             fmt(r["expectancy"], "pct2"), fmt(r["rand_expectancy"], "pct2"),
                             fmt(r["book_return"], "pct"), fmt(r["xic_return"], "pct")])
        out += [f"### {book.name}", "", table(["Year", "Setup", "Trades", "Win", "Net exp.", "Random exp.",
                                                 "Book return", f"{bench} return"], rows)]
    return out


def write_trades(trades: pd.DataFrame, path, market: "bt.Market" = bt.CA) -> pd.DataFrame:
    xic, _ = bt._load_clean(market.benchmark, market)
    adj = xic["adj_close"]
    t = trades.copy()
    t["ticker"] = t["yahoo"].map(data.to_output_ticker)
    t["xic_window_return"] = [adj.asof(x) / adj.asof(s) - 1 for s, x in zip(t["s"], t["exit_date"])]
    t["period"] = t["fill_date"].map(lambda d: bt.period_of(d.year))
    extra = [c for c in ("threshold", "market_filter", "event", "earnings") if c in t.columns]
    cols = TRADE_COLS[:2] + extra + [c for c in TRADE_COLS[2:] if c in t.columns]
    t = t[cols].rename(columns={"s": "signal_date", "skipped": "skipped_bars"})
    files.write_csv_gz(t, path, index=False, date_format="%Y-%m-%d", float_format="%.6g")
    return t


def tail_sections(trades: pd.DataFrame, t_out: pd.DataFrame, books, bench: str = "XIC") -> list[str]:
    skipped = trades.groupby("book").agg(trades=("net", "size"), with_skip=("skipped", lambda s: int((s > 0).sum())),
                                         bars_skipped=("skipped", "sum"))
    excess = (t_out["net"] - t_out["xic_window_return"]).groupby([t_out["book"], t_out["period"]]).mean()
    return ["## Flagged bars inside trades", "",
            "A flagged bar inside an open trade is skipped and its checks move to the next clean bar. "
            "Counts over every configuration:", "",
            table(["Book", "Trades", "Trades with a skipped bar", "Bars skipped"],
                  [[b, fmt(r["trades"], "int"), fmt(r["with_skip"], "int"), fmt(r["bars_skipped"], "int")]
                   for b, r in skipped.iterrows()]),
            f"## {bench} over each trade's own window (secondary benchmark)", "",
            f"Average of (trade net return - {bench} total return from the signal close to the exit date), all "
            "configurations pooled:", "",
            table(["Book", "IS", "OOS"], [[b.name, fmt(excess.get((b.name, "IS")), "pct2"),
                                          fmt(excess.get((b.name, "OOS")), "pct2")] for b in books])]


COMMON_CAVEATS = [
    "- Survivorship: Yahoo only has names listed today; delisted and acquired names are missing, so every "
    "number is an upper bound. CSE is not covered (known gap; the live trial still covers CSE).",
    "- Prices: split-adjusted, not dividend-adjusted; dividends with an ex-date after the fill day and up to the "
    "exit day are added to gross return. XIC uses adj_close (total return).",
    "- Main account: starts at $1,000 CAD; position size = min(cash, equity at the prior close / 3), whole shares "
    "at the limit price; a name whose one share costs more than equity / 3 is skipped for the next-ranked name "
    "(counted as skipped for price; skipped for cash when only the cash left is short). Shadow and small-cap: "
    "equity / 3, no cash limit.",
    "- Blocking flags (v2): only bad prints and unconfirmed level shifts block a signal's 60-session lookback "
    "and are skipped inside a trade. Real large moves (jumps over 40%, bad OHLC bars) no longer block.",
    "- A slot frees up the session after an exit (orders are placed before the open). A missed order does not "
    "hold a slot.",
    "- Random baseline: trade-level; on each day a book placed orders it draws the same number of names from that "
    "day's candidates in the same universe (any setup; for the main book only names it could afford), same exit; "
    "a missed random order counts as no trade.",
    "- Small-cap strict fill (sensitivity): no fill unless the day's low reached limit x 0.995.",
    "- Factor details docs/factors.md leaves open (PM confirmed): Thrust compares volume with the 20 sessions "
    "before the signal day; Room's breakout = close above the highest high of the prior 252 sessions; ATR14 = "
    "Wilder's; a name needs 252 sessions of history before it can be scored or traded.",
    "- Zero-volume days inside an open trade still count for exits; trades still open at the end are left out.",
]


def write_v2(results: pd.DataFrame, trades: pd.DataFrame, yearly: pd.DataFrame, cands: pd.DataFrame) -> str:
    w = wide(results)
    setups = [s.name for s in bt.price_score_setups()]
    t_out = write_trades(trades, bt.RESULTS / "trades_v2.csv")

    # Effect of each correction.
    v1 = pd.read_parquet(bt.CLEAN / "backtest_results_v1.parquet")
    v1["setup"] = v1.apply(lambda r: f"score>={r['threshold']} filter {r['market_filter']}", axis=1)
    cmp_rows = []
    for book in ("main", "shadow", "smallcap"):
        for period in ("IS", "OOS"):
            a = v1[(v1["book"] == book) & (v1["period"] == period)]["trades"].sum()
            b = results[(results["book"] == book) & (results["period"] == period)]["trades"].sum()
            cmp_rows.append([book, period, fmt(a, "int"), fmt(b, "int"), fmt(b - a, "int"),
                             fmt((b - a) / a if a else math.nan, "pct")])
    v1_cands = pd.read_parquet(bt.CLEAN / "outcomes.parquet", columns=["variant", "universe", "t"]) \
        if (bt.CLEAN / "outcomes.parquet").exists() else None
    namedays = []
    if v1_cands is not None:
        for uni in ("regular", "smallcap"):
            a = int(((v1_cands["variant"] == "base") & (v1_cands["universe"] == uni)).sum())
            b = int(((cands["variant"] == "base") & (cands["universe"] == uni) & ~cands["strict"]).sum())
            namedays.append([uni, fmt(a, "int"), fmt(b, "int"), fmt(b - a, "int")])

    main_r = results[(results["book"] == "main") & (results["period"] == "OOS")]
    skip_rows = [[r["setup"], r["variant"], fmt(r["skipped_price"], "int"), fmt(r["skipped_cash"], "int")]
                 for _, r in main_r.iterrows() if r["variant"] == "base"]
    total_price = int(main_r["skipped_price"].sum())
    total_cash = int(main_r["skipped_cash"].sum())

    strict_rows = []
    for setup in setups:
        for var in ("base", "time15"):
            a = w[(w["book"] == "smallcap") & (w["setup"] == setup) & (w["variant"] == var)].iloc[0]
            b = w[(w["book"] == "smallcap_strict") & (w["setup"] == setup) & (w["variant"] == var)].iloc[0]
            strict_rows.append([setup, var, f"{fmt(a['trades_IS'], 'int')} / {fmt(a['trades_OOS'], 'int')}",
                                f"{fmt(b['trades_IS'], 'int')} / {fmt(b['trades_OOS'], 'int')}",
                                f"{fmt(a['expectancy_IS'], 'pct2')} / {fmt(a['expectancy_OOS'], 'pct2')}",
                                f"{fmt(b['expectancy_IS'], 'pct2')} / {fmt(b['expectancy_OOS'], 'pct2')}"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    first, last = cands["t"].min().date(), cands["t"].max().date()
    out = [
        "# Backtest v2",
        "",
        f"Generated {now}. Rules: docs/rules.md (playbook v2.4); factors: docs/factors.md. Signals {first} to "
        f"{last}. In-sample = fills 2016-2022 (from {first}, after the one-year warm-up); out-of-sample = fills from "
        "2023-01-01. **Nothing was tuned.** v1 (results/backtest_v1.md) is kept for comparison.",
        "",
        "Changes from v1 (PM review of phase 2):",
        "1. Only bad prints and unconfirmed level shifts block signals; real large moves no longer do.",
        "2. Main account starts at $1,000 CAD, whole shares at the limit, skip for price and take the next name.",
        "3. Small-cap adds a strict-fill sensitivity (fill only if low <= limit x 0.995).",
        "",
        "**Read first:** survivorship makes every number an upper bound; CSE is not covered.",
        "",
        "## Summary",
        "",
        *summary_lines(w, "4 books x score thresholds 2/3/4 x market filter on/off x 6 exits"),
        "## What each correction changed",
        "",
        "### 1. Blocking flags",
        "",
        "Candidate name-days (eligible, clean lookback, scoreable) before and after:",
        "",
        table(["Universe", "v1", "v2", "Added"], namedays),
        "Trades summed over all 36 configurations of each book (main also changes size, so shadow and small-cap "
        "show the flag effect alone):",
        "",
        table(["Book", "Period", "v1 trades", "v2 trades", "Extra", "Change"], cmp_rows),
        "### 2. Main account at $1,000",
        "",
        f"Signals the main book skipped because one share cost more than the position size: {total_price:,} "
        f"summed over its 36 configurations and the whole run (both periods); skipped because only the cash "
        f"left was short: {total_cash:,}. Base exit by setup:",
        "",
        table(["Setup", "Exit", "Skipped for price", "Skipped for cash"], skip_rows),
        "### 3. Small-cap strict fill",
        "",
        "Trades and net expectancy, IS / OOS, normal fill vs strict fill:",
        "",
        table(["Setup", "Exit", "Trades normal", "Trades strict", "Net exp. normal", "Net exp. strict"], strict_rows),
        "## All configurations",
        "",
        "Net expectancy per trade after costs, in-sample | out-of-sample, with out-of-sample trades and whether "
        "out-of-sample beats random (R) and XIC (X).",
        "",
        *matrix(w, bt.BOOKS, setups),
        "## Full metrics",
        "",
        "Rows: each exit, then the random baseline (trade-level) and XIC buy-and-hold. Columns: in-sample / "
        "out-of-sample.",
        "",
        *full_tables(w, bt.BOOKS, setups),
        "## By year",
        "",
        "Base exit, score >= 3, with and without the market filter.",
        "",
        *by_year(yearly, bt.BOOKS, ["score>=3 filter Yes", "score>=3 filter No"]),
        *tail_sections(trades, t_out, bt.BOOKS),
        "## Choices and caveats",
        "",
        *COMMON_CAVEATS,
        "",
    ]
    text = "\n".join(out)
    (bt.RESULTS / "backtest_v2.md").write_text(text, encoding="utf-8")
    return text
