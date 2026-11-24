"""Write results/backtest_v1.md and results/trades_v1.csv (formats in docs/outputs.md)."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd

from engine import backtest as bt, data

MIN_TRADES = 100  # the spec's bar for a result to mean something

METRIC_COLS = [  # (column, label, kind)
    ("trades", "Trades", "int"), ("trades_per_week", "Per week", "f2"), ("win_rate", "Win", "pct"),
    ("avg_win", "Avg win", "pct"), ("avg_loss", "Avg loss", "pct"), ("expectancy", "Net exp.", "pct2"),
    ("profit_factor", "PF", "f2"), ("max_drawdown", "Max DD", "pct"), ("exit_Stop", "Stop", "pct"),
    ("exit_Gap stop", "Gap stop", "pct"), ("exit_Target", "Target", "pct"), ("exit_Gap target", "Gap tgt", "pct"),
    ("exit_Time stop", "Time", "pct"), ("avg_hold", "Hold", "f1"), ("pct_days_invested", "Invested", "pct"),
    ("cagr", "CAGR", "pct"), ("cagr_vs_xic", "vs XIC", "pct"),
]


def fmt(v, kind: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    if isinstance(v, float) and math.isinf(v):
        return "inf"
    return {"int": lambda x: f"{int(x):,}", "f1": lambda x: f"{x:.1f}", "f2": lambda x: f"{x:.2f}",
            "pct": lambda x: f"{x:.1%}", "pct2": lambda x: f"{x:+.2%}"}[kind](v)


def table(header: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(r) + " |" for r in rows]) + "\n"


def _wide(results: pd.DataFrame) -> pd.DataFrame:
    key = ["book", "threshold", "market_filter", "variant"]
    w = results.pivot_table(index=key, columns="period", aggfunc="first")
    w.columns = [f"{m}_{p}" for m, p in w.columns]
    return w.reset_index()


def config_name(r) -> str:
    return f"{r['book']} / score>={r['threshold']} / filter {r['market_filter']} / {r['variant']}"


def write(results: pd.DataFrame, trades: pd.DataFrame, yearly: pd.DataFrame, cands: pd.DataFrame) -> str:
    xic, _ = bt._load_clean(data.BENCHMARK)
    adj = xic["adj_close"]
    w = _wide(results)
    w["beats_random_OOS"] = w["expectancy_OOS"] > w["rand_p95_OOS"]
    w["beats_xic_OOS"] = w["cagr_OOS"] > w["xic_cagr_OOS"]
    w["positive_OOS"] = w["expectancy_OOS"] > 0
    w["enough_OOS"] = w["trades_OOS"] >= MIN_TRADES
    w["edge_OOS"] = w["beats_random_OOS"] & w["beats_xic_OOS"] & w["enough_OOS"]

    # --- trades_v1.csv
    t = trades.copy()
    t["ticker"] = t["yahoo"].map(data.to_output_ticker)
    t["xic_window_return"] = [adj.asof(x) / adj.asof(s) - 1 for s, x in zip(t["s"], t["exit_date"])]
    t["period"] = t["fill_date"].map(lambda d: bt.period_of(d.year))
    cols = ["book", "threshold", "market_filter", "variant", "period", "ticker", "type", "universe", "s",
            "fill_date", "exit_date", "price_score", "trend", "thrust", "room", "fits_stop", "limit", "fill",
            "exit_price", "reason", "sessions", "skipped", "dividends", "gross", "net", "shares",
            "xic_window_return"]
    t = t[cols].rename(columns={"s": "signal_date", "skipped": "skipped_bars"})
    t.to_csv(bt.RESULTS / "trades_v1.csv", index=False, date_format="%Y-%m-%d", float_format="%.6g")
    xic_excess = (t["net"] - t["xic_window_return"]).groupby([t["book"], t["period"]]).mean()

    # --- headline
    ranked = w[w["enough_OOS"]].sort_values("expectancy_OOS", ascending=False)
    head_cols = ["Config", "OOS trades", "OOS net exp.", "OOS win", "OOS PF", "OOS CAGR", "XIC CAGR",
                 "Random p95", "Pctile vs random", "IS net exp.", "IS trades"]

    def head_rows(df):
        return [[config_name(r), fmt(r["trades_OOS"], "int"), fmt(r["expectancy_OOS"], "pct2"),
                 fmt(r["win_rate_OOS"], "pct"), fmt(r["profit_factor_OOS"], "f2"), fmt(r["cagr_OOS"], "pct"),
                 fmt(r["xic_cagr_OOS"], "pct"), fmt(r["rand_p95_OOS"], "pct2"), fmt(r["rand_pctile_OOS"], "pct"),
                 fmt(r["expectancy_IS"], "pct2"), fmt(r["trades_IS"], "int")] for _, r in df.iterrows()]

    n_cfg, n_enough = len(w), int(w["enough_OOS"].sum())
    n_rand, n_xic, n_edge = (int((w["beats_random_OOS"] & w["enough_OOS"]).sum()),
                             int((w["beats_xic_OOS"] & w["enough_OOS"]).sum()), int(w["edge_OOS"].sum()))
    n_pos = int((w["positive_OOS"] & w["enough_OOS"]).sum())
    both_periods = w[w["enough_OOS"] & (w["trades_IS"] >= MIN_TRADES) & (w["expectancy_IS"] > w["rand_p95_IS"])
                     & w["beats_random_OOS"]]

    # --- setup frequency (question 3)
    freq = cands[cands["variant"] == "base"].copy()
    freq["year"] = freq["t"].dt.year
    sessions = pd.Series(xic.index[xic.index >= freq["t"].min()].year).value_counts().sort_index()
    freq_rows = []
    for uni in ("regular", "smallcap"):
        f = freq[freq["universe"] == uni]
        row = [uni]
        for thr in bt.THRESHOLDS:
            per_day = (f["price_score"] >= thr).groupby(f["t"]).sum().reindex(
                xic.index[xic.index >= freq["t"].min()], fill_value=0)
            row.append(fmt(per_day.mean(), "f1"))
        row.append(fmt(freq[(freq["universe"] == uni) & (freq["price_score"] == 4)].shape[0] / sessions.sum() * 5, "f2"))
        freq_rows.append(row)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    first, last = cands["t"].min().date(), cands["t"].max().date()
    out = [
        "# Backtest v1",
        "",
        f"Generated {now}. Rules: docs/rules.md (playbook v2.4); factors: docs/factors.md. "
        f"Signals {first} to {last}. In-sample = fills in 2016-2022 (effectively from {first}, after the "
        "one-year warm-up the 52-week high needs); out-of-sample = fills from 2023-01-01. **Nothing was tuned**: "
        "every setting comes from the playbook and the spec, and both periods are shown only for comparison.",
        "",
        "**Read first:** survivorship. Yahoo only has names listed today; delisted and acquired names are "
        "missing, so every number here is an upper bound. CSE names are not in the backtest (known gap; the "
        "live trial still covers CSE).",
        "",
        "## Summary",
        "",
        f"- {n_cfg} configurations: 3 books x score thresholds 2/3/4 x market filter on/off x 6 exits. "
        f"{n_enough} have at least {MIN_TRADES} out-of-sample trades.",
        f"- Out-of-sample, among those {n_enough}: {n_pos} have positive net expectancy after costs, "
        f"{n_rand} beat the random-entry baseline (net expectancy above the 95th percentile of 200 random runs), "
        f"{n_xic} beat XIC's CAGR, and **{n_edge} do both** (the spec's bar for a playbook proposal).",
        f"- Configurations that beat random in both periods with {MIN_TRADES}+ trades each: {len(both_periods)}.",
        "",
        f"### Best out-of-sample configurations ({MIN_TRADES}+ OOS trades, by net expectancy)",
        "",
        table(head_cols, head_rows(ranked.head(10))),
        "### Worst out-of-sample configurations",
        "",
        table(head_cols, head_rows(ranked.tail(5).iloc[::-1])),
        "Ranking on out-of-sample results is descriptive only. Picking the top row and calling it the rule "
        "would be tuning on the out-of-sample period; any change goes through the playbook's proposal process.",
        "",
        "## How often setups appear (question 3)",
        "",
        "Average names per session that are eligible and reach each price score (before the 3-slot limit, "
        "market filter off). Last column: score-4 setups per week.",
        "",
        table(["Universe", "Score >= 2", "Score >= 3", "Score = 4", "Score 4 per week"], freq_rows),
        "## All configurations",
        "",
        "Net expectancy per trade after costs, in-sample | out-of-sample, with out-of-sample trades and "
        "whether out-of-sample beats random (R) and XIC (X).",
        "",
    ]
    for book in bt.BOOKS:
        rows = []
        for thr in bt.THRESHOLDS:
            for filt in ("Yes", "No"):
                cells = [f"score>={thr}, filter {filt}"]
                for var in bt.VARIANTS:
                    r = w[(w["book"] == book.name) & (w["threshold"] == thr) & (w["market_filter"] == filt)
                          & (w["variant"] == var)].iloc[0]
                    mark = ("R" if r["beats_random_OOS"] else "") + ("X" if r["beats_xic_OOS"] else "")
                    cells.append(f"{fmt(r['expectancy_IS'], 'pct2')} \\| {fmt(r['expectancy_OOS'], 'pct2')} "
                                 f"({fmt(r['trades_OOS'], 'int')}{', ' + mark if mark else ''})")
                rows.append(cells)
        out += [f"### {book.name} ({book.universe} universe, cost {book.cost:.1%} round trip)", "",
                table(["Config"] + bt.VARIANTS, rows)]

    out += ["## Full metrics", "",
            "One table per book and entry setting. Rows: each exit, then the random baseline (trade-level: "
            "expectancy, win rate, profit factor, average trades) and XIC buy-and-hold (total return, adj_close). "
            "Columns: in-sample / out-of-sample.", ""]
    hdr = ["Exit"] + [f"{lab} IS / OOS" for _, lab, _ in METRIC_COLS]
    for book in bt.BOOKS:
        for thr in bt.THRESHOLDS:
            for filt in ("Yes", "No"):
                sub = w[(w["book"] == book.name) & (w["threshold"] == thr) & (w["market_filter"] == filt)]
                rows = []
                for _, r in sub.iterrows():
                    rows.append([r["variant"]] + [f"{fmt(r[c + '_IS'], k)} / {fmt(r[c + '_OOS'], k)}"
                                                  for c, _, k in METRIC_COLS])
                base = sub[sub["variant"] == "base"].iloc[0]
                rand_cells = {"trades": ("rand_trades", "f1"), "win_rate": ("rand_win_rate", "pct"),
                              "expectancy": ("rand_expectancy", "pct2"), "profit_factor": ("rand_pf", "f2")}
                rows.append(["random (base exit)"] + [
                    (f"{fmt(base[rand_cells[c][0] + '_IS'], rand_cells[c][1])} / "
                     f"{fmt(base[rand_cells[c][0] + '_OOS'], rand_cells[c][1])}") if c in rand_cells else "-"
                    for c, _, _ in METRIC_COLS])
                rows.append(["XIC buy and hold"] + [
                    f"{fmt(base['xic_cagr_IS'], 'pct')} / {fmt(base['xic_cagr_OOS'], 'pct')}" if c == "cagr" else "-"
                    for c, _, _ in METRIC_COLS])
                out += [f"### {book.name}, score >= {thr}, market filter {filt}", "", table(hdr, rows)]
                rr = sub.set_index("variant")
                out += ["Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th "
                        "percentile OOS): " + "; ".join(
                            f"{v} {fmt(rr.at[v, 'rand_expectancy_IS'], 'pct2')} / "
                            f"{fmt(rr.at[v, 'rand_expectancy_OOS'], 'pct2')} "
                            f"({fmt(rr.at[v, 'rand_p5_OOS'], 'pct2')} to {fmt(rr.at[v, 'rand_p95_OOS'], 'pct2')})"
                            for v in bt.VARIANTS), ""]

    out += ["## By year", "",
            "Base exit, score >= 3. Book return is the year's change in book equity; random is the mean "
            "net expectancy of 200 random-entry runs on the same days.", ""]
    for book in bt.BOOKS:
        rows = []
        for filt in ("Yes", "No"):
            y = yearly[(yearly["book"] == book.name) & (yearly["threshold"] == 3) & (yearly["market_filter"] == filt)
                       & (yearly["variant"] == "base")]
            for _, r in y.iterrows():
                rows.append([str(r["year"]), filt, fmt(r["trades"], "int"), fmt(r["win_rate"], "pct"),
                             fmt(r["expectancy"], "pct2"), fmt(r["rand_expectancy"], "pct2"),
                             fmt(r["book_return"], "pct"), fmt(r["xic_return"], "pct")])
        out += [f"### {book.name}", "", table(["Year", "Filter", "Trades", "Win", "Net exp.", "Random exp.",
                                                 "Book return", "XIC return"], rows)]

    skipped = trades.groupby("book").agg(trades=("net", "size"), with_skip=("skipped", lambda s: int((s > 0).sum())),
                                         bars_skipped=("skipped", "sum"))
    out += ["## Flagged bars inside trades", "",
            "A flagged bar inside an open trade is skipped and its checks move to the next clean bar. "
            "Counts over every configuration:", "",
            table(["Book", "Trades", "Trades with a skipped bar", "Bars skipped"],
                  [[b, fmt(r["trades"], "int"), fmt(r["with_skip"], "int"), fmt(r["bars_skipped"], "int")]
                   for b, r in skipped.iterrows()]),
            "## XIC over each trade's own window (secondary benchmark)", "",
            "Average of (trade net return - XIC total return from the signal close to the exit date), all "
            "configurations pooled:", "",
            table(["Book", "IS", "OOS"], [[b, fmt(xic_excess.get((b, "IS")), "pct2"),
                                          fmt(xic_excess.get((b, "OOS")), "pct2")] for b in ("main", "shadow", "smallcap")]),
            "## Choices and caveats", "",
            "- Survivorship (above): an upper bound. CSE not covered.",
            "- Fill optimism: daily bars cannot show whether a limit really traded. Fills require volume on the "
            "fill day; the stricter small-cap check from the spec's bias table (fill only if the low is 0.5% "
            "below the limit) is not applied, because docs/rules.md does not include it.",
            "- Prices: split-adjusted, not dividend-adjusted; dividends with an ex-date after the fill day and "
            "up to the exit day are added to gross return. XIC uses adj_close (total return).",
            f"- Main account starts at ${bt.START_EQUITY:,.0f}; position size = min(cash, equity at the prior "
            "close / 3), whole shares. Shadow and small-cap: equity at the prior close / 3, no cash limit.",
            "- A slot frees up the session after an exit (orders are placed before the open). A missed order "
            "does not hold a slot.",
            "- The random baseline is trade-level: on each day a book placed orders it draws the same number of "
            "names from that day's eligible, scoreable universe (any score, ignoring which names the book "
            "already held) and applies the same exit; a missed random order counts as no trade.",
            "- Flagged bars: no signal whose 60-session lookback holds a blocking flag (jumps over 40%, bad "
            "prints, bad OHLC, level shifts); a flagged fill day is a miss; inside a trade the bar is skipped "
            "and does not count as a session.",
            "- Factor details docs/factors.md leaves open: Thrust compares volume with the 20 sessions before "
            "the signal day; Room's breakout = close above the highest high of the prior 252 sessions; "
            "ATR14 = Wilder's. A name needs 252 sessions of history before it can be scored.",
            "- Trades still open at the end of the data are left out.",
            "- Regime: see the by-year tables; 2016-today has few long bear markets.",
            ""]
    text = "\n".join(out)
    (bt.RESULTS / "backtest_v1.md").write_text(text, encoding="utf-8")
    return text
