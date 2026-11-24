"""Phase 2c study: does earnings-day drift beat random and SPY in the US? (results/us_earnings_v1.md)

Run with `python -m engine.us run` after `universe`, `download` and `earnings`.

Pipeline (same engine as Canada):
1. Clean every name with quality.clean_history (docs/corrections.csv, automatic drops
   before unresolved level shifts) and build point-in-time eligibility with the US gate:
   close >= $5 and 20-day average value traded >= $20M USD, at most 4 zero-volume days
   in 20, volume on the signal day, v2 blocking flags (bad prints, unconfirmed level shifts).
2. Outcomes for every +4%/3x event day and a fixed 15% uniform sample of all other
   eligible name-days (the S&P universe is ~900 names a day; the full table would not fit
   in memory). The random baseline and the "all candidates" average use the sample only.
3. Two cost scenarios on the same gross outcomes: 0.10% round trip (US-dollar account)
   and 2.0% round trip (CAD account converting both ways).
4. Books: equal-weight 3-slot shadow; and the unlimited event average (every event).
5. Negative earnings events (<= -4% on >= 3x): forward returns only, no trades.
"""
from __future__ import annotations

import hashlib
import logging
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from engine import backtest as bt, data, earnings, news, quality, universe
from engine.report_backtest import (MIN_TRADES, by_year, fmt, full_tables, matrix, summary_lines, table,
                                    tail_sections, wide, write_trades)
from engine.us import BENCHMARK, RESULTS, UNIVERSE_FILE, US_DIR

CLEAN = US_DIR / "clean"
EARN_DIR = US_DIR / "earnings"
US = bt.Market("us", CLEAN, BENCHMARK)
SAMPLE_RATE = 0.15
SCENARIOS = (("us_low", "USD account, 0.10% round trip"), ("us_high", "CAD account, 2.0% round trip"))
BOOKS = tuple(bt.Book(f"shadow {lab.split(',')[0].split()[0]}", uni, "equal") for uni, lab in SCENARIOS)
HORIZONS = (1, 5, 10, 15)


# --- 1. clean and eligibility -----------------------------------------------------

def clean_all() -> dict:
    u = pd.read_csv(UNIVERSE_FILE)
    corr = data.load_corrections()
    for sub in ("prices", "actions"):
        (CLEAN / sub).mkdir(parents=True, exist_ok=True)
    flags_all, elig_all, dropped, missing = [], [], [], []
    for sym in u["yahoo"].tolist() + [BENCHMARK]:
        df, acts, flags, cut = quality.clean_history(sym, corr, US_DIR)
        if df is None or df.empty:
            missing.append(sym)
            continue
        df.to_parquet(CLEAN / "prices" / f"{sym}.parquet")
        acts.to_parquet(CLEAN / "actions" / f"{sym}.parquet")
        if cut is not None:
            dropped.append({"yahoo": sym, "starts": cut})
        f = flags.copy()
        f.insert(0, "yahoo", sym)
        flags_all.append(f)
        if sym == BENCHMARK:
            continue
        blocked = f.loc[f["flag"] == "bad_print", "date"]   # v2: real moves do not block
        e = universe.daily_eligibility(df, blocked, gates=universe.US_GATES).reset_index()
        e.insert(0, "yahoo", sym)
        elig_all.append(e)
    flags = pd.concat([f for f in flags_all if len(f)], ignore_index=True)
    elig = pd.concat(elig_all, ignore_index=True)
    flags.to_parquet(CLEAN / "flags.parquet")
    elig.to_parquet(CLEAN / "eligibility.parquet")
    return {"names": len(u), "missing": missing, "dropped": pd.DataFrame(dropped), "flags": flags, "elig": elig}


# --- 2. outcomes ------------------------------------------------------------------

def _sample_mask(sym: str, index: pd.DatetimeIndex) -> np.ndarray:
    seed = int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed).random(len(index)) < SAMPLE_RATE


def row_filter(sym, df, f):
    sampled = _sample_mask(sym, df.index)
    event = ((f["ret_1d"] >= 0.04) & (f["vol_ratio"] >= 3)).to_numpy()
    return sampled | event, sampled


def scenario_cands(gross: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for uni, _ in SCENARIOS:
        c = gross.copy()
        c["universe"] = uni
        c["net"] = c["gross"] - bt.sim.COST[uni]
        parts.append(c)
    out = pd.concat(parts, ignore_index=True)
    out["universe"] = out["universe"].astype("category")
    return out


# --- events ----------------------------------------------------------------------

EVENTS = {
    "earnings +4%/3x": lambda c: news.is_news4(c) & c["earnings"],
    "earnings +6%/5x": lambda c: news.is_news6(c) & c["earnings"],
    "non-earnings +4%/3x": lambda c: news.is_news4(c) & ~c["earnings"] & c["earnings_covered"],
}


def setups() -> list[bt.Setup]:
    return [bt.Setup(name, fn, ("value_traded_20d",), {"event": name}) for name, fn in EVENTS.items()]


def event_average(cands: pd.DataFrame) -> pd.DataFrame:
    """The unlimited event book: every event's own outcome, mean net with a 95% interval."""
    c = cands.assign(period=cands["t"].dt.year.map(bt.period_of), year=cands["t"].dt.year)
    rows = []
    for uni, _ in SCENARIOS:
        for var in bt.VARIANTS:
            pool = c[(c["universe"] == uni) & (c["variant"] == var)]
            groups = {"all candidates (sample)": pool["sampled"]}
            groups.update({name: fn(pool) for name, fn in EVENTS.items()})
            for name, mask in groups.items():
                g = pool[mask]
                for key, sub in [(p, g[g["period"] == p]) for p in ("IS", "OOS")] + \
                                [(str(y), g[g["year"] == y]) for y in sorted(g["year"].unique())]:
                    net = sub["net"].dropna()
                    rows.append({"universe": uni, "variant": var, "group": name, "period": key,
                                 "filled": len(net), "expectancy": net.mean() if len(net) else math.nan,
                                 "ci95": 1.96 * net.std(ddof=1) / math.sqrt(len(net)) if len(net) > 1 else math.nan,
                                 "win_rate": (net > 0).mean() if len(net) else math.nan})
    return pd.DataFrame(rows)


def forward_returns(elig: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """Close-to-close returns after earnings events, up (+4%/3x) and down (<= -4% on >= 3x),
    vs SPY over the same window. Report only: the down side is a short-free control."""
    spy, _ = bt._load_clean(BENCHMARK, US)
    sadj = spy["adj_close"]
    ok_by = {s: g.set_index("date")["eligible"] for s, g in elig.groupby("yahoo")}
    rows = []
    for sym, ok in ok_by.items():
        when = earnings.load(sym, EARN_DIR)
        if len(when) == 0:
            continue
        react = earnings.reaction_sessions(when[when.dt.tz_localize(None) <= cal[-1]], cal)
        df, _ = bt._load_clean(sym, US)
        c, v = df["close"], df["volume"]
        ret = c / c.shift(1) - 1
        vr = v / v.shift(1).rolling(20, min_periods=20).mean()
        idx = df.index
        for i in np.flatnonzero((vr >= 3).to_numpy() & ((ret >= 0.04) | (ret <= -0.04)).to_numpy()):
            s = idx[i]
            if s not in react or not bool(ok.get(s, False)):
                continue
            row = {"yahoo": sym, "s": s, "side": "up" if ret.iat[i] > 0 else "down", "ret_1d": float(ret.iat[i])}
            for k in HORIZONS:
                if i + k < len(idx):
                    x = idx[i + k]
                    row[f"r{k}"] = c.iat[i + k] / c.iat[i] - 1
                    row[f"x{k}"] = row[f"r{k}"] - (sadj.asof(x) / sadj.asof(s) - 1)
            rows.append(row)
    out = pd.DataFrame(rows)
    out["period"] = out["s"].dt.year.map(bt.period_of)
    return out


# --- report ----------------------------------------------------------------------

def _ci_cell(sub: pd.Series) -> str:
    sub = sub.dropna()
    if len(sub) < 2:
        return "-"
    return f"{sub.mean():+.2%} (±{1.96 * sub.std(ddof=1) / math.sqrt(len(sub)):.2%}), n={len(sub):,}"


def write_report(cl, results, trades, yearly, cands, stats, avg, fwd) -> str:
    w = wide(results)
    names = list(EVENTS)
    t_out = write_trades(trades, RESULTS / "us_trades_v1.csv", US)
    sessions = len(cands["t"].unique())
    base = cands[(cands["variant"] == "base") & (cands["universe"] == "us_low")]
    ev_rows = []
    for name, fn in EVENTS.items():
        m = fn(base)
        per = base[m].groupby(base.loc[m, "t"].dt.year.map(bt.period_of)).size()
        ev_rows.append([name, fmt(per.get("IS", 0), "int"), fmt(per.get("OOS", 0), "int"),
                        fmt(m.sum() / (sessions / 5), "f2")])
    elig = cl["elig"]
    spy, _ = bt._load_clean(BENCHMARK, US)
    ecal = spy.index[spy.index >= cands["t"].min()]
    per_day = elig[elig["eligible"]].groupby("date").size().reindex(ecal, fill_value=0)
    elig_year = per_day.groupby(per_day.index.year).mean().round(1)
    flags = cl["flags"]
    fcount = flags["flag"].value_counts()

    def avg_rows(uni, var):
        a = avg[(avg["universe"] == uni) & (avg["variant"] == var)]
        rows = []
        for g in ["all candidates (sample)"] + names:
            r = a[a["group"] == g].set_index("period")
            rows.append([g] + [f"{fmt(r.at[p, 'filled'], 'int')} / {fmt(r.at[p, 'expectancy'], 'pct2')} "
                               f"(±{fmt(r.at[p, 'ci95'], 'pct2')[1:]}) / {fmt(r.at[p, 'win_rate'], 'pct')}"
                               if p in r.index else "-" for p in ("IS", "OOS")])
        return rows

    def verdict(uni):
        sub = w[w["book"].isin([b.name for b in BOOKS if b.universe == uni])]
        e = sub[sub["setup"] == "earnings +4%/3x"]
        return e

    fwd_rows = []
    for side in ("up", "down"):
        for period in ("IS", "OOS"):
            f = fwd[(fwd["side"] == side) & (fwd["period"] == period)]
            fwd_rows.append([side, period, fmt(len(f), "int")] +
                            [_ci_cell(f[f"r{k}"]) for k in HORIZONS] + [_ci_cell(f["x10"])])

    yr_rows = []
    for uni, lab in SCENARIOS:
        a = avg[(avg["universe"] == uni) & (avg["group"] == "earnings +4%/3x") & (avg["variant"] == "base")]
        for _, r in a[~a["period"].isin(["IS", "OOS"])].iterrows():
            yr_rows.append([r["period"], lab.split(",")[0], fmt(r["filled"], "int"), fmt(r["expectancy"], "pct2"),
                            f"±{fmt(r['ci95'], 'pct2')[1:]}", fmt(r["win_rate"], "pct")])

    dropped = cl["dropped"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    first, last = cands["t"].min().date(), cands["t"].max().date()
    clear = {uni: verdict(uni) for uni, _ in SCENARIOS}
    out = [
        "# US earnings-drift test v1 (phase 2c)",
        "",
        f"Generated {now}. Signals {first} to {last}; in-sample = fills 2017-2022, out-of-sample = fills from "
        "2023-01-01. Same engine and rules as the Canadian studies (docs/rules.md exits, v2 blocking flags, "
        "random baseline). **Nothing was tuned.**",
        "",
        "**Survivorship, strongly:** the universe is *today's* S&P 500 and S&P 400 members. Names that were "
        "dropped, acquired or went bankrupt since 2016 are missing, and today's members are partly in the index "
        "*because* they did well. Every number here is an upper bound, more so than in the Canadian studies.",
        "",
        "## Answer",
        "",
    ]
    for uni, lab in SCENARIOS:
        e = clear[uni]
        ok = e[e["edge_OOS"]]
        rnd = e[e["beats_random_OOS"] & e["enough_OOS"]]
        spy_ok = e[e["beats_xic_OOS"] & e["enough_OOS"]]
        out.append(f"- **{lab}:** earnings +4%/3x in the 3-slot shadow book clears the bar (beats random AND SPY "
                   f"out-of-sample with {MIN_TRADES}+ trades) for {len(ok)} of 6 exits"
                   + (f" ({', '.join(ok['variant'])})" if len(ok) else "")
                   + f"; beats random for {len(rnd)}, beats SPY's CAGR for {len(spy_ok)}. "
                   "Out-of-sample trades by exit: " + ", ".join(f"{v} {int(n)}" for v, n in zip(e["variant"], e["trades_OOS"])) + ".")
    out += [
        f"- Earnings +4%/3x events per week (candidate universe): {ev_rows[0][3]}.",
        "",
        "## Data",
        "",
        f"- Universe: {cl['names']} current constituents (results/us_universe_v1.csv: S&P 500 and S&P 400 pages "
        "on Wikipedia, saved in data/us/source/). Yahoo had no data for "
        f"{len(cl['missing'])}{' (' + ', '.join(cl['missing'][:20]) + ')' if cl['missing'] else ''}.",
        f"- Quality (same checks as Canada, docs/corrections.csv applied): flagged bars by type: "
        + ", ".join(f"{k} {v:,}" for k, v in fcount.items()) + ".",
        f"- Automatic drops (history before an unresolved split-sized level shift): {len(dropped)} names"
        + (": " + ", ".join(f"{data.to_output_ticker(r.yahoo)} from {r.starts.date()}" for r in dropped.itertuples())
           if len(dropped) and len(dropped) <= 30 else "") + ".",
        f"- Earnings dates: Yahoo had a calendar for {stats['names_with_dates']} of {stats['names_in_universe']} "
        f"names in the candidate universe ({stats['dates']:,} past release dates).",
        "- Point-in-time eligible names per session (gate $5 and $20M USD a day): "
        + ", ".join(f"{y} {v:.0f}" for y, v in elig_year.items()) + ".",
        f"- Outcome table: every +4%/3x event day plus a fixed {SAMPLE_RATE:.0%} uniform sample of all other "
        "eligible name-days; the random baseline and the all-candidates average draw only from the sample.",
        "",
        "Events in the candidate universe:",
        "",
        table(["Event", "IS events", "OOS events", "Per week"], ev_rows),
        "## Summary over every configuration",
        "",
    ]
    for uni, lab in SCENARIOS:
        out += [f"### {lab}", "", *summary_lines(w[w["book"].isin([b.name for b in BOOKS if b.universe == uni])],
                                                f"shadow book x 3 event setups x 6 exits", bench="SPY")]
    out += ["## Unlimited event average (every event, no slots)", "",
            "Each cell: filled trades / mean net return per trade (± 95% interval) / win rate. 'All candidates' is "
            "the uniform sample of every eligible name-day: what a random entry earns on average.", ""]
    for uni, lab in SCENARIOS:
        for var in ("base", "time15"):
            out += [f"### {lab}, {var} exit", "", table(["Group", "IS", "OOS"], avg_rows(uni, var))]
    out += ["### Earnings +4%/3x by year, base exit (unlimited)", "",
            table(["Year", "Costs", "Trades", "Net exp.", "95% interval", "Win"], yr_rows),
            "## Negative earnings events: do they keep falling? (report only, no trades)", "",
            "Close-to-close return from the event close, earnings events with |return| >= 4% on >= 3x volume, "
            "point-in-time eligible names. No costs, no dividends. Last column: 10-session return minus SPY's.", "",
            table(["Side", "Period", "Events"] + [f"{k}-session" for k in HORIZONS] + ["10-session vs SPY"], fwd_rows),
            "## All configurations (shadow book)", "",
            "Net expectancy per trade after costs, IS | OOS, with OOS trades and whether OOS beats random (R) and "
            "SPY (X).", "",
            *matrix(w, BOOKS, names),
            "## Full metrics", "",
            *full_tables(w, BOOKS, names, bench="SPY"),
            "## By year (shadow book, base exit)", "",
            *by_year(yearly, BOOKS, names, bench="SPY"),
            *tail_sections(trades, t_out, BOOKS, bench="SPY"),
            "## Choices and caveats", "",
            "- Survivorship (above): today's index members only.",
            "- Same rules as docs/rules.md: limit close(t-1) x 1.005 for day t, stop-only fill day, gap/stop-first/"
            "target/time-stop order, all six exits. Shadow book: 3 slots, equal weight, no cash limit, names "
            "ranked by 20-day value traded.",
            "- Earnings reaction session: release before the open = that session; after the close = the next; no "
            "time or intraday = either. Yahoo's calendar times are not always right.",
            "- Costs are round-trip and per trade; the 2.0% case assumes about 1% currency conversion each way, "
            "nothing else (no withholding tax on US dividends, which would lower it further).",
            "- The random baseline and the all-candidates average use a 15% uniform sample of eligible name-days "
            "(see Data); a uniform sample of a day's universe is still a uniform draw.",
            "- 95% intervals assume independent trades; events cluster in earnings season, so the true intervals "
            "are wider.",
            ""]
    text = "\n".join(out)
    (RESULTS / "us_earnings_v1.md").write_text(text, encoding="utf-8")
    return text


def run() -> None:
    logging.info("cleaning")
    cl = clean_all()
    logging.info("outcomes")
    gross = bt.build_outcomes(bt.V2, US, row_filter)
    spy, _ = bt._load_clean(BENCHMARK, US)
    gross, stats = news.tag_earnings(gross, spy.index, EARN_DIR)
    cands = scenario_cands(gross)
    del gross
    results, trades, yearly = bt.run_configs(cands, BOOKS, setups(), bt.V2, "us", US)
    avg = event_average(cands)
    fwd = forward_returns(cl["elig"], spy.index)
    for name, df in (("results", results), ("yearly", yearly), ("avg", avg), ("fwd", fwd)):
        df.to_parquet(CLEAN / f"us_{name}_v1.parquet")
    write_report(cl, results, trades, yearly, cands, stats, avg, fwd)
    print((RESULTS / "us_earnings_v1.md").resolve(), datetime.now(timezone.utc).isoformat())
