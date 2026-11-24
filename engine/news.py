"""Phase 2b: a price-and-volume stand-in for News 3, and post-earnings drift.

    python -m engine.news      # writes results/news_proxy_v1.md and results/news_trades_v1.csv

Event on session s (the order is for s+1 with the usual limit, close(s) x 1.005):
    news4          return(s) >= +4% on volume(s) >= 3x its 20-session average (sessions before s)
    news6          >= +6% on >= 5x
    news4 gap      news4 where the overnight gap (open(s) / close(s-1) - 1) made at least half the day's move
    news4 intraday news4 where the gap made less than half of it (the move came during the session)
    news4 reversal news4 after a negative 20-session return (close(s-1) / close(s-21) - 1 < 0)
    news4 continuation  news4 after a positive one
    news4 earnings      news4 on an earnings reaction session (engine/earnings)
    news4 non-earnings  news4 on any other session, for names whose earnings calendar covers that date

Same universe, gates, exits, books and random baseline as backtest v2. When more
events than free slots, names are ranked by 20-day value traded (no score here).
Nothing is tuned; the thresholds are the PM's.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

import pandas as pd

from engine import backtest as bt, data, earnings
from engine.report_backtest import (COMMON_CAVEATS, MIN_TRADES, by_year, fmt, full_tables, matrix, summary_lines,
                                    table, tail_sections, wide, write_trades)

RESULTS = bt.RESULTS


def is_news4(c):
    return (c["ret_1d"] >= 0.04) & (c["vol_ratio"] >= 3)


def is_news6(c):
    return (c["ret_1d"] >= 0.06) & (c["vol_ratio"] >= 5)


EVENTS = {
    "news4": is_news4,
    "news6": is_news6,
    "news4 gap": lambda c: is_news4(c) & (c["gap_1d"] >= c["ret_1d"] / 2),
    "news4 intraday": lambda c: is_news4(c) & (c["gap_1d"] < c["ret_1d"] / 2),
    "news4 reversal": lambda c: is_news4(c) & (c["ret_20d_prior"] < 0),
    "news4 continuation": lambda c: is_news4(c) & (c["ret_20d_prior"] > 0),
    "news4 earnings": lambda c: is_news4(c) & c["earnings"],
    "news4 non-earnings": lambda c: is_news4(c) & ~c["earnings"] & c["earnings_covered"],
}


def setups() -> list[bt.Setup]:
    return [bt.Setup(name, fn, ("value_traded_20d",), {"event": name}) for name, fn in EVENTS.items()]


def tag_earnings(cands: pd.DataFrame, cal: pd.DatetimeIndex, directory=None) -> tuple[pd.DataFrame, dict]:
    """Add earnings (s is a reaction session) and earnings_covered (s inside the name's calendar)."""
    react, covered_rng, n_dates, names_with = {}, {}, 0, 0
    for sym in cands["yahoo"].unique():
        when = earnings.load(sym, directory)
        if len(when) == 0:
            continue
        past = when[when.dt.tz_localize(None) <= cal[-1] + pd.Timedelta(days=1)]
        if len(past) == 0:
            continue
        names_with += 1
        n_dates += len(past)
        react[sym] = earnings.reaction_sessions(past, cal)
        covered_rng[sym] = (pd.Timestamp(past.min().date()), pd.Timestamp(past.max().date()))
    ys, ss = cands["yahoo"].astype(str).to_numpy(), cands["s"]
    cands = cands.copy()
    cands["earnings"] = [s in react.get(y, ()) for y, s in zip(ys, ss)]
    lo = pd.Series([covered_rng.get(y, (pd.NaT, pd.NaT))[0] for y in ys], index=cands.index)
    hi = pd.Series([covered_rng.get(y, (pd.NaT, pd.NaT))[1] for y in ys], index=cands.index)
    cands["earnings_covered"] = (ss >= lo) & (ss <= hi + pd.Timedelta(days=4))
    stats = {"names_in_universe": int(cands["yahoo"].nunique()), "names_with_dates": names_with, "dates": n_dates}
    return cands, stats


def event_study(cands: pd.DataFrame) -> pd.DataFrame:
    """Trade-level, no slot limit: every event's own outcome vs every candidate's (the unconditional pool)."""
    rows = []
    c = cands.assign(period=cands["t"].dt.year.map(bt.period_of))
    for uni, strict in (("regular", False), ("smallcap", False)):
        for var in bt.VARIANTS:
            pool = c[(c["universe"] == uni) & (c["strict"] == strict) & (c["variant"] == var)]
            groups = {"all candidates": pd.Series(True, index=pool.index)}
            groups.update({name: fn(pool) for name, fn in EVENTS.items()})
            for name, mask in groups.items():
                for period in ("IS", "OOS"):
                    g = pool[mask & (pool["period"] == period)]
                    net = g["net"].dropna()
                    rows.append({"universe": uni, "variant": var, "group": name, "period": period,
                                 "events": len(g), "filled": len(net), "expectancy": net.mean() if len(net) else math.nan,
                                 "win_rate": (net > 0).mean() if len(net) else math.nan,
                                 "se": net.std(ddof=1) / math.sqrt(len(net)) if len(net) > 1 else math.nan})
    return pd.DataFrame(rows)


def event_counts(cands: pd.DataFrame) -> pd.DataFrame:
    base = cands[(cands["variant"] == "base") & ~cands["strict"]]
    rows = []
    for name, fn in EVENTS.items():
        m = fn(base)
        cnt = base[m].groupby([base.loc[m, "t"].dt.year, base.loc[m, "universe"]], observed=True).size()
        for (y, u), n in cnt.items():
            rows.append({"event": name, "year": y, "universe": u, "events": n})
    return pd.DataFrame(rows)


def write_report(results, trades, yearly, cands, stats, study) -> str:
    w = wide(results)
    names = list(EVENTS)
    t_out = write_trades(trades, RESULTS / "news_trades_v1.csv")
    counts = event_counts(cands)
    cnt_rows = []
    for name in names:
        for uni in ("regular", "smallcap"):
            c = counts[(counts["event"] == name) & (counts["universe"] == uni)]
            per = c.assign(period=c["year"].map(bt.period_of)).groupby("period")["events"].sum()
            yrs = cands["t"].dt.year.nunique()
            cnt_rows.append([name, uni, fmt(per.get("IS", 0), "int"), fmt(per.get("OOS", 0), "int"),
                             fmt(c["events"].sum() / (len(cands["t"].unique()) / 5), "f2")])

    def study_rows(uni, var):
        s = study[(study["universe"] == uni) & (study["variant"] == var)]
        rows = []
        for g in ["all candidates"] + names:
            r = s[s["group"] == g].set_index("period")
            rows.append([g] + [f"{fmt(r.at[p, 'filled'], 'int')} / {fmt(r.at[p, 'expectancy'], 'pct2')} "
                               f"(±{fmt(1.96 * r.at[p, 'se'], 'pct2')[1:]}) / {fmt(r.at[p, 'win_rate'], 'pct')}"
                               for p in ("IS", "OOS")])
        return rows

    e_cov = cands[(cands["variant"] == "base") & ~cands["strict"]]
    ev4 = is_news4(e_cov)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    first, last = cands["t"].min().date(), cands["t"].max().date()
    out = [
        "# News proxy study v1 (phase 2b)",
        "",
        f"Generated {now}. Signals {first} to {last}; in-sample = fills 2016-2022, out-of-sample = fills from "
        "2023-01-01. Same universe, gates, exits, books, costs and random baseline as results/backtest_v2.md. "
        "**Nothing was tuned**: the event thresholds are the PM's.",
        "",
        "**Read first:** survivorship makes every number an upper bound; CSE is not covered. A big move on big "
        "volume is only a stand-in for News 3: it also catches index flows, takeover rumours and sector moves.",
        "",
        "## Events",
        "",
        "Event on session s; order for s+1 at close(s) x 1.005, good for that day only.",
        "",
        "- **news4**: return(s) >= +4% on volume(s) >= 3x its 20-session average (the sessions before s).",
        "- **news6**: >= +6% on >= 5x.",
        "- **gap / intraday**: news4 split by whether the overnight gap made at least half of the day's move.",
        "- **reversal / continuation**: news4 after a negative / positive 20-session return.",
        "- **earnings / non-earnings**: news4 on an earnings reaction session (release before the open = that "
        "session; after the close = the next session; no time or intraday = either), vs news4 on other sessions "
        "for names whose earnings calendar covers the date.",
        "",
        "When more events than free slots, names are ranked by 20-day value traded.",
        "",
        "Events in the candidate universe (eligible, clean lookback, scoreable):",
        "",
        table(["Event", "Universe", "IS events", "OOS events", "Per week"], cnt_rows),
        "### Earnings dates",
        "",
        f"Yahoo had earnings dates for {stats['names_with_dates']} of the {stats['names_in_universe']} names in "
        f"the candidate universe ({stats['dates']:,} past release dates). news4 events: {int(ev4.sum()):,}; on an "
        f"earnings reaction session: {int((ev4 & e_cov['earnings']).sum()):,}; elsewhere inside a covered "
        f"calendar: {int((ev4 & ~e_cov['earnings'] & e_cov['earnings_covered']).sum()):,}; for names or dates with "
        f"no calendar: {int((ev4 & ~e_cov['earnings_covered']).sum()):,}.",
        "",
        "## Summary",
        "",
        *summary_lines(w, "4 books x 8 event setups x 6 exits"),
        "## Event study: every event, no slot limit",
        "",
        "Each cell: filled trades / mean net return per trade after costs (± 95% interval) / win rate, IS | OOS. "
        "'All candidates' is every eligible name-day in the same universe, the unconditional comparison. This "
        "answers whether events do better on average before the 3-slot limit picks among them.",
        "",
    ]
    for uni in ("regular", "smallcap"):
        for var in ("base", "time15"):
            out += [f"### {uni}, {var} exit", "", table(["Group", "IS", "OOS"], study_rows(uni, var))]
    out += ["### Post-earnings drift", "",
            "news4 earnings vs news4 non-earnings, every exit, mean net per trade OOS (IS):", ""]
    pe_rows = []
    for uni in ("regular", "smallcap"):
        for var in bt.VARIANTS:
            s = study[(study["universe"] == uni) & (study["variant"] == var)].set_index(["group", "period"])
            cell = lambda g: (f"{fmt(s.at[(g, 'OOS'), 'expectancy'], 'pct2')} ({fmt(s.at[(g, 'IS'), 'expectancy'], 'pct2')}), "
                              f"n={fmt(s.at[(g, 'OOS'), 'filled'], 'int')}")
            pe_rows.append([uni, var, cell("news4 earnings"), cell("news4 non-earnings")])
    out += [table(["Universe", "Exit", "Earnings", "Non-earnings"], pe_rows),
            "## All configurations", "",
            "Net expectancy per trade after costs, in-sample | out-of-sample, with out-of-sample trades and whether "
            "out-of-sample beats random (R) and XIC (X).", "",
            *matrix(w, bt.BOOKS, names),
            "## Full metrics", "",
            "Rows: each exit, then the random baseline (trade-level) and XIC buy-and-hold. Columns: IS / OOS.", "",
            *full_tables(w, bt.BOOKS, names),
            "## By year", "", "Base exit, news4 and news6.", "",
            *by_year(yearly, bt.BOOKS, ["news4", "news6"]),
            *tail_sections(trades, t_out, bt.BOOKS),
            "## Choices and caveats", "",
            *COMMON_CAVEATS,
            "- Event volume ratio uses the 20 sessions before the event day, like Thrust.",
            "- Gap vs intraday split at half the day's move; reversal vs continuation at a 20-session return of 0.",
            "- Earnings dates come from Yahoo's calendar, which is patchy for small names; events for names or dates "
            "it does not cover are in news4 but in neither earnings group.",
            "- The event study counts every event, so its trades overlap in time and are not independent; the books "
            "are the tradeable version.",
            ""]
    text = "\n".join(out)
    (RESULTS / "news_proxy_v1.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cands = bt.load_outcomes(bt.V2)
    xic, _ = bt._load_clean(data.BENCHMARK)
    cands, stats = tag_earnings(cands, xic.index)
    results, trades, yearly = bt.run_configs(cands, bt.BOOKS, setups(), bt.V2, "news")
    study = event_study(cands)
    for name, df in (("results", results), ("trades", trades), ("yearly", yearly), ("study", study)):
        df.to_parquet(bt.CLEAN / f"news_{name}_v1.parquet")
    write_report(results, trades, yearly, cands, stats, study)
    print((RESULTS / "news_proxy_v1.md").resolve(), datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
