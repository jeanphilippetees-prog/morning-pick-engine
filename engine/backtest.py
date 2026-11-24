"""Walk-forward backtest of docs/rules.md on the cleaned phase 1 data.

    python -m engine.backtest          # writes results/backtest_v1.md and results/trades_v1.csv

Nothing here is tuned. Every parameter comes from docs/rules.md and
docs/factors.md; in-sample (2016-2022) and out-of-sample (2023-today) are only
reported side by side.

Steps:
1. Candidates: every name-day that is eligible at the close of s (engine/universe)
   and scoreable (engine/factors). The order is for the next XIC session t.
2. Outcomes: each candidate is simulated once per exit variant (engine/simulate),
   so the books and the random baseline read the same table.
3. Books: main (regular, cash-limited, whole shares), shadow (regular, equal
   weight, no cash limit) and small-cap (equal weight, 1% cost); up to 3
   positions; ranked by price score, then 20-day value traded.
4. Random baseline: on every day a book placed orders, the same number of names
   drawn at random from that day's eligible universe, same exits; 200 runs.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from engine import data, factors, quality, simulate as sim

CLEAN = data.DATA_DIR / "clean"
RESULTS = data.ROOT / "results"
OUTCOMES = CLEAN / "outcomes.parquet"

SLOTS = 3
START_EQUITY = 30_000.0
IN_SAMPLE = (2016, 2022)
OUT_SAMPLE_START = 2023
THRESHOLDS = (2, 3, 4)
FILTERS = (True, False)
VARIANTS = list(sim.VARIANTS)
RANDOM_RUNS = 200
SEED = 20261124


@dataclass(frozen=True)
class Book:
    name: str
    universe: str
    sizing: str  # "cash" (main) or "equal" (shadow, small-cap)

    @property
    def cost(self) -> float:
        return sim.COST[self.universe]


BOOKS = (Book("main", "regular", "cash"), Book("shadow", "regular", "equal"),
         Book("smallcap", "smallcap", "equal"))


# --- 1 and 2: candidates and outcomes -----------------------------------------

def _load_clean(sym: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (pd.read_parquet(CLEAN / "prices" / f"{sym}.parquet"),
            pd.read_parquet(CLEAN / "actions" / f"{sym}.parquet"))


def build_outcomes() -> pd.DataFrame:
    elig = pd.read_parquet(CLEAN / "eligibility.parquet")
    flags = pd.read_parquet(CLEAN / "flags.parquet")
    blocking = flags[flags["flag"].isin(quality.BLOCKING)].groupby("yahoo")["date"].apply(set).to_dict()
    xic, _ = _load_clean(data.BENCHMARK)
    cal = xic.index
    next_session = pd.Series(cal[1:], index=cal[:-1])

    rows = []
    syms = elig.loc[elig["eligible"], "yahoo"].unique()
    elig_by_sym = {s: g.set_index("date") for s, g in elig[elig["yahoo"].isin(syms)].groupby("yahoo")}
    for n, sym in enumerate(syms):
        df, acts = _load_clean(sym)
        f = factors.compute(df)
        e = elig_by_sym[sym]
        ok = e["eligible"].reindex(df.index, fill_value=False) & f["scoreable"]
        if not ok.any():
            continue
        flagged = df.index.isin(list(blocking.get(sym, ()))).tolist()
        o, h, l, c, v = (df[k].tolist() for k in ("open", "high", "low", "close", "volume"))
        cumdiv = sim.cumulative_dividends(df.index, acts.get("dividends")).tolist()
        for p in np.flatnonzero(ok.to_numpy()):
            s = df.index[p]
            t = next_session.get(s)
            if t is None:
                continue  # signal on the last session: no next day yet
            book = e.at[s, "book"]
            cost = sim.COST[book]
            base = {"t": t, "s": s, "yahoo": sym, "universe": book, "price_score": int(f["price_score"].iat[p]),
                    "trend": int(f["trend"].iat[p]), "thrust": int(f["thrust"].iat[p]), "room": int(f["room"].iat[p]),
                    "fits_stop": int(f["fits_stop"].iat[p]), "value_traded_20d": float(e.at[s, "value_traded_20d"]),
                    "limit": sim.buy_limit(c[p])}
            has_bar = p + 1 < len(df) and df.index[p + 1] == t
            for var in VARIANTS:
                if not has_bar:
                    r = {"filled": False, "reason": "Missed (no bar)", "fill": math.nan, "exit_date": pd.NaT,
                         "exit_price": math.nan, "sessions": 0, "skipped": 0, "dividends": 0.0,
                         "gross": math.nan, "net": math.nan}
                else:
                    r = sim.run(o, h, l, c, v, flagged, cumdiv, p + 1, base["limit"], var,
                                float(f["atr14"].iat[p]), cost)
                    r["exit_date"] = df.index[r.pop("exit_index")]
                rows.append({**base, "variant": var, **r})
        if n % 200 == 0:
            logging.info("outcomes: %d/%d names, %d rows", n, len(syms), len(rows))
    out = pd.DataFrame(rows)
    out["type"] = out["yahoo"].map(data.security_type)
    out.to_parquet(OUTCOMES)
    return out


# --- 3: books -------------------------------------------------------------------

def _mark_closes(syms, cal) -> dict[str, pd.Series]:
    """Clean closes on the XIC calendar, forward-filled over flagged or missing bars."""
    flags = pd.read_parquet(CLEAN / "flags.parquet")
    blocking = flags[flags["flag"].isin(quality.BLOCKING)]
    out = {}
    for sym in syms:
        df, _ = _load_clean(sym)
        c = df["close"].copy()
        c[c.index.isin(blocking.loc[blocking["yahoo"] == sym, "date"])] = np.nan
        out[sym] = c.reindex(cal.union(c.index)).ffill().reindex(cal)
    return out


def run_book(book: Book, threshold: int, use_filter: bool, variant: str, cands: pd.DataFrame,
             mfilter: pd.Series, cal: pd.DatetimeIndex, marks: dict[str, pd.Series]):
    """Day-by-day book. Returns (trades, orders_per_day, equity)."""
    pool = cands[(cands["variant"] == variant) & (cands["universe"] == book.universe)
                 & (cands["price_score"] >= threshold)]
    if use_filter:
        pool = pool[pool["s"].map(mfilter).fillna(False).astype(bool)]
    pool = pool.sort_values(["t", "price_score", "value_traded_20d"], ascending=[True, False, False])
    by_day = {t: g for t, g in pool.groupby("t", sort=False)}

    cash, equity_prev = START_EQUITY, START_EQUITY
    open_pos: list[dict] = []
    trades, orders, equity = [], {}, np.empty(len(cal))
    for d_i, t in enumerate(cal):
        todays = by_day.get(t)
        free = SLOTS - len(open_pos)
        if todays is not None and free > 0:
            held = {p["yahoo"] for p in open_pos}
            picks = todays[~todays["yahoo"].isin(held)].head(free)
            if len(picks):
                orders[t] = len(picks)
            for r in picks.itertuples(index=False):
                if not r.filled or r.reason == "Open":
                    continue
                if book.sizing == "cash":
                    shares = math.floor(min(cash, equity_prev / SLOTS) / r.fill)
                    if shares < 1:
                        continue
                else:
                    shares = (equity_prev / SLOTS) / r.fill
                cash -= shares * r.fill
                pos = {**r._asdict(), "shares": shares}
                open_pos.append(pos)
        # Exits at today's prices are booked at the end of the day.
        still = []
        for p in open_pos:
            if p["exit_date"] == t:
                cash += p["shares"] * (p["exit_price"] + p["dividends"]) - book.cost * p["shares"] * p["fill"]
                trades.append(p)
            else:
                still.append(p)
        open_pos = still
        equity_prev = cash + sum(p["shares"] * marks[p["yahoo"]].iat[d_i] for p in open_pos)
        equity[d_i] = equity_prev
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["fill_date"] = tr["t"]
    return tr, pd.Series(orders, dtype=int), pd.Series(equity, index=cal)


# --- 4: random baseline ---------------------------------------------------------

def random_baseline(book: Book, variant: str, orders: pd.Series, cands: pd.DataFrame,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Per run and year: filled count, wins, sum net, sum of wins, sum of losses."""
    pool = cands[(cands["variant"] == variant) & (cands["universe"] == book.universe)]
    nets_by_day = {t: g["net"].to_numpy() for t, g in pool.groupby("t")}
    years = sorted({t.year for t in orders.index})
    acc = {y: np.zeros((5, RANDOM_RUNS)) for y in years}
    for t, n in orders.items():
        nets = nets_by_day[t]
        idx = rng.random((RANDOM_RUNS, len(nets))).argpartition(n - 1, axis=1)[:, :n]
        vals = nets[idx]
        filled = ~np.isnan(vals)
        v0 = np.where(filled, vals, 0.0)
        a = acc[t.year]
        a[0] += filled.sum(1)
        a[1] += (v0 > 0).sum(1)
        a[2] += v0.sum(1)
        a[3] += np.where(v0 > 0, v0, 0).sum(1)
        a[4] += np.where(v0 < 0, v0, 0).sum(1)
    rows = []
    for y, a in acc.items():
        for run_i in range(RANDOM_RUNS):
            rows.append({"year": y, "run": run_i, "n": a[0, run_i], "wins": a[1, run_i], "sum": a[2, run_i],
                         "pos": a[3, run_i], "neg": a[4, run_i]})
    return pd.DataFrame(rows)


# --- metrics ----------------------------------------------------------------------

def period_of(year: int) -> str:
    return "IS" if year <= IN_SAMPLE[1] else "OOS"


def _cagr(series: pd.Series) -> float:
    if len(series) < 2 or series.iloc[0] <= 0:
        return math.nan
    yrs = (series.index[-1] - series.index[0]).days / 365.25
    return (series.iloc[-1] / series.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else math.nan


def _period_slice(s: pd.Series, period: str) -> pd.Series:
    """Equity over a period, starting from the last value before it."""
    if period == "IS":
        mask = s.index.year <= IN_SAMPLE[1]
        return s[mask]
    before = s[s.index.year < OUT_SAMPLE_START]
    after = s[s.index.year >= OUT_SAMPLE_START]
    return pd.concat([before.tail(1), after]) if len(before) else after


def metrics(trades: pd.DataFrame, equity: pd.Series, xic_adj: pd.Series, period: str,
            first_signal: pd.Timestamp) -> dict:
    eq = _period_slice(equity[equity.index >= first_signal], period)
    xa = _period_slice(xic_adj[xic_adj.index >= first_signal], period)
    tr = trades[trades["fill_date"].map(lambda d: period_of(d.year)) == period] if len(trades) else trades
    n = len(tr)
    sessions = len(eq) - (1 if period == "OOS" else 0)
    weeks = max(sessions / 5, 1e-9)
    out = {"trades": n, "trades_per_week": n / weeks}
    if n:
        net = tr["net"]
        wins, losses = net[net > 0], net[net <= 0]
        out.update(win_rate=(net > 0).mean(), avg_win=wins.mean() if len(wins) else math.nan,
                   avg_loss=losses.mean() if len(losses) else math.nan, expectancy=net.mean(),
                   profit_factor=wins.sum() / -losses.sum() if losses.sum() < 0 else math.inf,
                   avg_hold=tr["sessions"].mean(), skipped_trades=int((tr["skipped"] > 0).sum()))
        for reason in ("Stop", "Gap stop", "Target", "Gap target", "Time stop"):
            out[f"exit_{reason}"] = (tr["reason"] == reason).mean()
        days = pd.Series(False, index=eq.index)
        for f, x in zip(tr["fill_date"], tr["exit_date"]):
            days[(days.index >= f) & (days.index <= x)] = True
        out["pct_days_invested"] = days.mean()
    else:
        out.update(win_rate=math.nan, avg_win=math.nan, avg_loss=math.nan, expectancy=math.nan,
                   profit_factor=math.nan, avg_hold=math.nan, skipped_trades=0, pct_days_invested=0.0)
    out["max_drawdown"] = (eq / eq.cummax() - 1).min() if len(eq) else math.nan
    out["cagr"] = _cagr(eq)
    out["xic_cagr"] = _cagr(xa)
    out["cagr_vs_xic"] = out["cagr"] - out["xic_cagr"]
    return out


def random_summary(rand: pd.DataFrame, period: str) -> dict:
    r = rand[rand["year"].map(period_of) == period].groupby("run")[["n", "wins", "sum", "pos", "neg"]].sum()
    if r.empty or (r["n"] == 0).all():
        return {"rand_expectancy": math.nan, "rand_p5": math.nan, "rand_p95": math.nan, "rand_win_rate": math.nan,
                "rand_pf": math.nan, "rand_trades": math.nan}
    exp = r["sum"] / r["n"]
    return {"rand_expectancy": exp.mean(), "rand_p5": exp.quantile(0.05), "rand_p95": exp.quantile(0.95),
            "rand_win_rate": (r["wins"] / r["n"]).mean(), "rand_pf": (r["pos"] / -r["neg"]).mean(),
            "rand_trades": r["n"].mean(), "_exp_runs": exp.to_numpy()}


# --- run everything -------------------------------------------------------------

def run_all(cands: pd.DataFrame):
    xic, _ = _load_clean(data.BENCHMARK)
    cal = xic.index
    mfilter = factors.market_filter(xic)
    first_signal = cands["t"].min()
    cal = cal[cal >= first_signal]
    marks = _mark_closes(cands.loc[cands["filled"], "yahoo"].unique(), cal)
    rng = np.random.default_rng(SEED)
    results, all_trades, yearly = [], [], []
    for book in BOOKS:
        for thr in THRESHOLDS:
            for filt in FILTERS:
                for var in VARIANTS:
                    tr, orders, eq = run_book(book, thr, filt, var, cands, mfilter, cal, marks)
                    rand = random_baseline(book, var, orders, cands, rng) if len(orders) else pd.DataFrame(
                        columns=["year", "run", "n", "wins", "sum", "pos", "neg"])
                    cfg = {"book": book.name, "threshold": thr, "market_filter": "Yes" if filt else "No",
                           "variant": var}
                    for period in ("IS", "OOS"):
                        m = metrics(tr, eq, xic["adj_close"], period, first_signal)
                        rs = random_summary(rand, period)
                        runs = rs.pop("_exp_runs", None)
                        m["rand_pctile"] = (float((runs < m["expectancy"]).mean())
                                            if runs is not None and not math.isnan(m["expectancy"]) else math.nan)
                        m["orders"] = int(orders[orders.index.map(lambda d: period_of(d.year)) == period].sum()) \
                            if len(orders) else 0
                        results.append({**cfg, "period": period, **m, **rs})
                    yearly.append(_yearly(cfg, tr, eq, rand, xic["adj_close"]))
                    if len(tr):
                        all_trades.append(tr.assign(**cfg))
                    logging.info("%s thr%d filter=%s %s: %d trades", book.name, thr, filt, var, len(tr))
    return pd.DataFrame(results), pd.concat(all_trades, ignore_index=True), pd.concat(yearly, ignore_index=True)


def _yearly(cfg, tr, eq, rand, xic_adj) -> pd.DataFrame:
    rows = []
    for y in sorted(set(eq.index.year)):
        e = eq[eq.index.year <= y]
        prev = e[e.index.year < y]
        start = prev.iloc[-1] if len(prev) else e.iloc[0]
        book_ret = e.iloc[-1] / start - 1
        xa = xic_adj[xic_adj.index.year <= y]
        xprev = xa[xa.index.year < y]
        xs = xprev.iloc[-1] if len(xprev) else xa[xa.index >= eq.index[0]].iloc[0]
        t = tr[tr["fill_date"].map(lambda d: d.year) == y] if len(tr) else tr
        r = rand[rand["year"] == y]
        rows.append({**cfg, "year": y, "trades": len(t), "win_rate": (t["net"] > 0).mean() if len(t) else math.nan,
                     "expectancy": t["net"].mean() if len(t) else math.nan,
                     "rand_expectancy": (r["sum"] / r["n"].where(r["n"] > 0)).mean() if len(r) else math.nan,
                     "book_return": book_ret, "xic_return": xa.iloc[-1] / xs - 1})
    return pd.DataFrame(rows)


def main() -> None:
    import argparse

    from engine import report_backtest

    p = argparse.ArgumentParser()
    p.add_argument("--reuse-outcomes", action="store_true", help="reuse data/clean/outcomes.parquet")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cands = pd.read_parquet(OUTCOMES) if args.reuse_outcomes and OUTCOMES.exists() else build_outcomes()
    results, trades, yearly = run_all(cands)
    results.to_parquet(CLEAN / "backtest_results.parquet")
    yearly.to_parquet(CLEAN / "backtest_yearly.parquet")
    trades.to_parquet(CLEAN / "backtest_trades.parquet")
    report_backtest.write(results, trades, yearly, cands)
    print((RESULTS / "backtest_v1.md").resolve(), datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
