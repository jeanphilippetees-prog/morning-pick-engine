"""Walk-forward backtest of docs/rules.md on the cleaned phase 1 data.

    python -m engine.backtest            # v2: results/backtest_v2.md, results/trades_v2.csv
    python -m engine.news                # phase 2b: results/news_proxy_v1.md (engine/news.py)

Nothing here is tuned. Every parameter comes from docs/rules.md, docs/factors.md
or a PM decision; in-sample (2016-2022) and out-of-sample (2023-today) are only
reported side by side.

Steps:
1. Candidates: every name-day that passes the point-in-time gate at the close of s
   (engine/universe), has a clean 60-session lookback under the version's
   blocking flags, and is scoreable (engine/factors). The order is for the next
   XIC session t.
2. Outcomes: each candidate is simulated once per exit variant and fill rule
   (engine/simulate), so every book, setup and the random baseline read the same
   table.
3. Books: up to 3 positions. Main = regular universe, cash-limited, whole shares;
   shadow = regular, equal weight, no cash limit; small-cap = equal weight, 1%
   cost (plus a strict-fill sensitivity). A setup selects and ranks candidates.
4. Random baseline: on every day a book placed orders, the same number of names
   drawn at random from that day's candidates in the same universe, same exits;
   200 runs.

Versions:
- v1 (phase 2 as first reviewed): every flag in quality.BLOCKING blocks; main
  starts at $30,000 and sizes on the fill price.
- v2 (PM review of phase 2): only bad prints and unconfirmed level shifts block;
  main starts at $1,000, sizes min(cash, equity/3) in whole shares at the limit,
  and skips a name it cannot afford for the next-ranked one.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

import numpy as np
import pandas as pd

from engine import data, factors, quality, simulate as sim

CLEAN = data.DATA_DIR / "clean"
RESULTS = data.ROOT / "results"

SLOTS = 3
IN_SAMPLE = (2016, 2022)
OUT_SAMPLE_START = 2023
THRESHOLDS = (2, 3, 4)
FILTERS = (True, False)
VARIANTS = list(sim.VARIANTS)
RANDOM_RUNS = 200
SEED = 20261124
LOOKBACK = 60


@dataclass(frozen=True)
class Market:
    """Where a market's cleaned data lives and which benchmark it is measured against."""
    name: str
    clean: object          # Path to the cleaned data (prices/, actions/, flags.parquet, eligibility.parquet)
    benchmark: str         # Yahoo symbol: XIC.TO (Canada) or SPY (US)


CA = Market("ca", CLEAN, data.BENCHMARK)


@dataclass(frozen=True)
class Settings:
    version: str
    blocking: frozenset          # flag names; "level_shift_unconfirmed" = level shifts not verified
    main_equity: float
    main_rule: str               # "v1" or "v2" (see module docstring)
    equal_equity: float = 30_000.0


V1 = Settings("v1", frozenset(quality.BLOCKING), 30_000.0, "v1")
V2 = Settings("v2", frozenset({"bad_print", "level_shift_unconfirmed"}), 1_000.0, "v2")


@dataclass(frozen=True)
class Book:
    name: str
    universe: str
    sizing: str            # "cash" (main) or "equal"
    strict: bool = False   # strict small-cap fill (sensitivity)

    @property
    def cost(self) -> float:
        return sim.COST[self.universe]


MAIN = Book("main", "regular", "cash")
SHADOW = Book("shadow", "regular", "equal")
SMALLCAP = Book("smallcap", "smallcap", "equal")
SMALLCAP_STRICT = Book("smallcap_strict", "smallcap", "equal", strict=True)
BOOKS_V1 = (MAIN, SHADOW, SMALLCAP)
BOOKS = (MAIN, SHADOW, SMALLCAP, SMALLCAP_STRICT)


@dataclass(frozen=True)
class Setup:
    """Selects candidates for a book and ranks them when there are more than free slots."""
    name: str
    select: Callable[[pd.DataFrame], pd.Series]
    rank: tuple = ("value_traded_20d",)
    labels: dict = field(default_factory=dict)


def price_score_setup(threshold: int, use_filter: bool) -> Setup:
    def select(c):
        ok = c["price_score"] >= threshold
        return ok & c["market_ok"] if use_filter else ok
    return Setup(f"score>={threshold} filter {'Yes' if use_filter else 'No'}", select,
                 ("price_score", "value_traded_20d"),
                 {"threshold": threshold, "market_filter": "Yes" if use_filter else "No"})


# --- 1 and 2: candidates and outcomes -----------------------------------------

def _load_clean(sym: str, market: Market = CA) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (pd.read_parquet(market.clean / "prices" / f"{sym}.parquet"),
            pd.read_parquet(market.clean / "actions" / f"{sym}.parquet"))


def blocked_dates(settings: Settings, market: Market = CA) -> dict[str, set]:
    """Per ticker, the dates whose flag blocks signals and is skipped inside a trade."""
    flags = pd.read_parquet(market.clean / "flags.parquet")
    names = set(settings.blocking)
    keep = flags["flag"].isin(names)
    if "level_shift_unconfirmed" in names:
        corr = data.load_corrections()
        verified = set(zip(corr.loc[corr["ratio"] == 1, "yahoo"], corr.loc[corr["ratio"] == 1, "date"]))
        shift = flags["flag"] == "level_shift"
        unconfirmed = shift & ~pd.Series([(y, d) in verified for y, d in zip(flags["yahoo"], flags["date"])],
                                          index=flags.index)
        keep |= unconfirmed
    return flags[keep].groupby("yahoo")["date"].apply(set).to_dict()


def outcomes_path(settings: Settings, market: Market = CA):
    return market.clean / f"outcomes_{settings.version}.parquet"


def build_outcomes(settings: Settings, market: Market = CA, row_filter=None) -> pd.DataFrame:
    """row_filter(sym, df, factors) -> (keep, sampled) boolean arrays, or None to keep every row.

    sampled marks rows in a uniform random sample of the universe; the random baseline
    draws only from sampled rows (see run_configs). Without a filter every row is sampled.
    """
    elig = pd.read_parquet(market.clean / "eligibility.parquet",
                           columns=["yahoo", "date", "book", "gate_ok", "value_traded_20d"])
    blocking = blocked_dates(settings, market)
    xic, _ = _load_clean(market.benchmark, market)
    cal = xic.index
    next_session = pd.Series(cal[1:], index=cal[:-1])
    mfilter = factors.market_filter(xic)

    frames, total = [], 0
    syms = elig.loc[elig["gate_ok"], "yahoo"].unique()
    elig_by_sym = {s: g.set_index("date") for s, g in elig[elig["yahoo"].isin(syms)].groupby("yahoo")}
    for n, sym in enumerate(syms):
        df, acts = _load_clean(sym, market)
        f = factors.compute(df)
        e = elig_by_sym[sym].reindex(df.index)
        flagged_s = pd.Series(df.index.isin(list(blocking.get(sym, ()))), index=df.index)
        clean = flagged_s.astype(int).rolling(LOOKBACK, min_periods=1).sum() == 0
        ok = e["gate_ok"].fillna(False).astype(bool) & clean & f["scoreable"]
        sampled = np.ones(len(df), bool)
        if row_filter is not None:
            keep, sampled = row_filter(sym, df, f)
            ok = ok & keep
        if not ok.any():
            continue
        flagged = flagged_s.tolist()
        o, h, l, c, v = (df[k].tolist() for k in ("open", "high", "low", "close", "volume"))
        cumdiv = sim.cumulative_dividends(df.index, acts.get("dividends")).tolist()
        gap = (df["open"] / df["close"].shift(1) - 1).to_numpy()
        prior20 = (df["close"].shift(1) / df["close"].shift(21) - 1).to_numpy()
        rows = []
        for p in np.flatnonzero(ok.to_numpy()):
            s = df.index[p]
            t = next_session.get(s)
            if t is None:
                continue
            universe = e.at[s, "book"]
            base = {"t": t, "s": s, "yahoo": sym, "universe": universe,
                    "price_score": int(f["price_score"].iat[p]), "trend": int(f["trend"].iat[p]),
                    "thrust": int(f["thrust"].iat[p]), "room": int(f["room"].iat[p]),
                    "fits_stop": int(f["fits_stop"].iat[p]), "value_traded_20d": float(e.at[s, "value_traded_20d"]),
                    "limit": sim.buy_limit(c[p]), "market_ok": bool(mfilter.get(s, False)),
                    "ret_1d": float(f["ret_1d"].iat[p]), "vol_ratio": float(f["vol_ratio"].iat[p]),
                    "gap_1d": float(gap[p]), "ret_20d_prior": float(prior20[p]), "sampled": bool(sampled[p])}
            has_bar = p + 1 < len(df) and df.index[p + 1] == t
            for strict in ((False, True) if universe == "smallcap" else (False,)):
                for var in VARIANTS:
                    if not has_bar:
                        r = {"filled": False, "reason": "Missed (no bar)", "fill": math.nan, "exit_date": pd.NaT,
                             "exit_price": math.nan, "sessions": 0, "skipped": 0, "dividends": 0.0,
                             "gross": math.nan, "net": math.nan}
                    else:
                        r = sim.run(o, h, l, c, v, flagged, cumdiv, p + 1, base["limit"], var,
                                    float(f["atr14"].iat[p]), sim.COST.get(universe, 0.0), strict)
                        r["exit_date"] = df.index[r.pop("exit_index")]
                    rows.append({**base, "strict": strict, "variant": var, **r})
        if rows:
            frames.append(_compact(pd.DataFrame(rows)))
            total += len(rows)
        if n % 100 == 0:
            logging.info("outcomes %s: %d/%d names, %d rows", settings.version, n, len(syms), total)
    out = pd.concat(frames, ignore_index=True)
    for col in ("yahoo", "universe", "variant", "reason"):
        out[col] = out[col].astype("category")
    out["type"] = out["yahoo"].map(data.security_type).astype("category")
    out.to_parquet(outcomes_path(settings, market))
    return out


def _compact(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("price_score", "trend", "thrust", "room", "fits_stop", "sessions", "skipped"):
        df[col] = df[col].astype("int8")
    for col in ("value_traded_20d", "limit", "fill", "exit_price", "dividends", "gross", "net"):
        df[col] = df[col].astype("float64")
    for col in ("ret_1d", "vol_ratio", "gap_1d", "ret_20d_prior"):
        df[col] = df[col].astype("float32")
    return df


def load_outcomes(settings: Settings, rebuild: bool = False, market: Market = CA) -> pd.DataFrame:
    path = outcomes_path(settings, market)
    if path.exists() and not rebuild:
        return pd.read_parquet(path)
    return build_outcomes(settings, market)


# --- 3: books -------------------------------------------------------------------

def mark_closes(syms, cal, blocking: dict[str, set], market: Market = CA) -> dict[str, pd.Series]:
    """Clean closes on the benchmark calendar, forward-filled over flagged or missing bars."""
    out = {}
    for sym in syms:
        df, _ = _load_clean(sym, market)
        c = df["close"].copy()
        c[c.index.isin(list(blocking.get(sym, ())))] = np.nan
        out[sym] = c.reindex(cal.union(c.index)).ffill().reindex(cal)
    return out


def book_pool(cands: pd.DataFrame, book: Book, variant: str) -> pd.DataFrame:
    return cands[(cands["variant"] == variant) & (cands["universe"] == book.universe)
                 & (cands["strict"] == book.strict)]


def run_book(book: Book, pool: pd.DataFrame, setup: Setup, cal: pd.DatetimeIndex,
             marks: dict[str, pd.Series], settings: Settings = V2):
    """Day-by-day book over a pool already cut to one variant, universe and fill rule.

    Returns (trades, orders_per_day, equity, info) where info counts signals skipped
    because one share cost more than the position size ("price") or more than the
    cash left ("cash"), main book only.
    """
    sel = pool[setup.select(pool)]
    sel = sel.sort_values(["t", *setup.rank], ascending=[True] + [False] * len(setup.rank))
    by_day = {t: g for t, g in sel.groupby("t", sort=False, observed=True)}

    start = settings.main_equity if book.sizing == "cash" else settings.equal_equity
    cash, equity_prev = start, start
    open_pos: list[dict] = []
    trades, orders, equity = [], {}, np.empty(len(cal))
    info = {"skipped_price": 0, "skipped_cash": 0}
    caps = np.full(len(cal), np.inf)
    for d_i, t in enumerate(cal):
        caps[d_i] = equity_prev / SLOTS if book.sizing == "cash" else np.inf
        todays = by_day.get(t)
        free = SLOTS - len(open_pos)
        if todays is not None and free > 0:
            held = {p["yahoo"] for p in open_pos}
            placed = 0
            for r in todays.itertuples(index=False):
                if placed == free:
                    break
                if r.yahoo in held:
                    continue
                if book.sizing == "cash" and settings.main_rule == "v2":
                    size = min(cash, equity_prev / SLOTS)
                    if r.limit > equity_prev / SLOTS:
                        info["skipped_price"] += 1
                        continue
                    if r.limit > size:
                        info["skipped_cash"] += 1
                        continue
                    shares = math.floor(size / r.limit)
                elif book.sizing == "cash":   # v1
                    shares = math.floor(min(cash, equity_prev / SLOTS) / r.fill) if r.filled else 0
                else:
                    shares = (equity_prev / SLOTS) / r.fill if r.filled else 0
                placed += 1
                held.add(r.yahoo)
                if not r.filled or r.reason == "Open" or shares <= 0:
                    continue
                cash -= shares * r.fill
                open_pos.append({**r._asdict(), "shares": shares})
            if placed:
                orders[t] = placed
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
    info["caps"] = pd.Series(caps, index=cal)
    return tr, pd.Series(orders, dtype=int), pd.Series(equity, index=cal), info


# --- 4: random baseline ---------------------------------------------------------

def random_baseline(pool: pd.DataFrame, orders: pd.Series, rng: np.random.Generator,
                    caps: pd.Series | None = None) -> pd.DataFrame:
    """Per run and year: filled count, wins, sum net, sum of wins, sum of losses.

    caps: per-day position size for the main book; names whose limit is above it
    are left out of that day's draw, as the book itself could not buy them.
    """
    by_day = {t: (g["net"].to_numpy(), g["limit"].to_numpy()) for t, g in pool.groupby("t", observed=True)}
    years = sorted({t.year for t in orders.index})
    acc = {y: np.zeros((5, RANDOM_RUNS)) for y in years}
    for t, n in orders.items():
        if t not in by_day:
            continue  # no candidates in the (sampled) pool that day
        nets, limits = by_day[t]
        if caps is not None:
            nets = nets[limits <= caps.get(t, np.inf)]
        n = min(n, len(nets))
        if n == 0:
            continue
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
    return pd.DataFrame(rows, columns=["year", "run", "n", "wins", "sum", "pos", "neg"])


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
        return s[s.index.year <= IN_SAMPLE[1]]
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
                   avg_hold=tr["sessions"].mean(), skipped_trades=int((tr["skipped"] > 0).sum()),
                   expectancy_se=net.std(ddof=1) / math.sqrt(n) if n > 1 else math.nan)
        for reason in ("Stop", "Gap stop", "Target", "Gap target", "Time stop"):
            out[f"exit_{reason}"] = (tr["reason"] == reason).mean()
        days = pd.Series(False, index=eq.index)
        for f, x in zip(tr["fill_date"], tr["exit_date"]):
            days[(days.index >= f) & (days.index <= x)] = True
        out["pct_days_invested"] = days.mean()
    else:
        out.update(win_rate=math.nan, avg_win=math.nan, avg_loss=math.nan, expectancy=math.nan,
                   profit_factor=math.nan, avg_hold=math.nan, skipped_trades=0, pct_days_invested=0.0,
                   expectancy_se=math.nan)
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


def yearly_rows(cfg, tr, eq, rand, xic_adj) -> pd.DataFrame:
    rows = []
    for y in sorted(set(eq.index.year)):
        e = eq[eq.index.year <= y]
        prev = e[e.index.year < y]
        start = prev.iloc[-1] if len(prev) else e.iloc[0]
        xa = xic_adj[xic_adj.index.year <= y]
        xprev = xa[xa.index.year < y]
        xs = xprev.iloc[-1] if len(xprev) else xa[xa.index >= eq.index[0]].iloc[0]
        t = tr[tr["fill_date"].map(lambda d: d.year) == y] if len(tr) else tr
        r = rand[rand["year"] == y]
        rows.append({**cfg, "year": y, "trades": len(t), "win_rate": (t["net"] > 0).mean() if len(t) else math.nan,
                     "expectancy": t["net"].mean() if len(t) else math.nan,
                     "rand_expectancy": (r["sum"] / r["n"].where(r["n"] > 0)).mean() if len(r) else math.nan,
                     "book_return": e.iloc[-1] / start - 1, "xic_return": xa.iloc[-1] / xs - 1})
    return pd.DataFrame(rows)


# --- run everything -------------------------------------------------------------

def run_configs(cands: pd.DataFrame, books, setups, settings: Settings = V2, log_name: str = "",
                market: Market = CA):
    """Run every book x setup x exit. Returns (results, trades, yearly)."""
    xic, _ = _load_clean(market.benchmark, market)
    first_signal = cands["t"].min()
    cal = xic.index[xic.index >= first_signal]
    blocking = blocked_dates(settings, market)
    marks = mark_closes(cands.loc[cands["filled"], "yahoo"].unique(), cal, blocking, market)
    rng = np.random.default_rng(SEED)
    results, all_trades, yearly = [], [], []
    for book in books:
        for var in VARIANTS:
            pool = book_pool(cands, book, var)
            rpool = pool[pool["sampled"]] if "sampled" in pool else pool   # random draws: sampled rows only
            for setup in setups:
                tr, orders, eq, info = run_book(book, pool, setup, cal, marks, settings)
                caps = info["caps"] if (book.sizing == "cash" and settings.main_rule == "v2") else None
                rand = random_baseline(rpool, orders, rng, caps) if len(orders) else random_baseline(
                    rpool.iloc[:0], orders, rng)
                cfg = {"book": book.name, "setup": setup.name, **setup.labels, "variant": var}
                for period in ("IS", "OOS"):
                    m = metrics(tr, eq, xic["adj_close"], period, first_signal)
                    rs = random_summary(rand, period)
                    runs = rs.pop("_exp_runs", None)
                    m["rand_pctile"] = (float((runs < m["expectancy"]).mean())
                                        if runs is not None and not math.isnan(m["expectancy"]) else math.nan)
                    m["orders"] = int(orders[orders.index.map(lambda d: period_of(d.year)) == period].sum()) \
                        if len(orders) else 0
                    results.append({**cfg, "period": period, **m, **rs,
                                    "skipped_price": info["skipped_price"], "skipped_cash": info["skipped_cash"]})
                yearly.append(yearly_rows(cfg, tr, eq, rand, xic["adj_close"]))
                if len(tr):
                    all_trades.append(tr.assign(**cfg))
                logging.info("%s %s %s %s: %d trades", log_name, book.name, setup.name, var, len(tr))
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    return pd.DataFrame(results), trades, pd.concat(yearly, ignore_index=True)


def price_score_setups() -> list[Setup]:
    return [price_score_setup(thr, filt) for thr in THRESHOLDS for filt in FILTERS]


def main() -> None:
    import argparse

    from engine import report_backtest

    p = argparse.ArgumentParser()
    p.add_argument("--rebuild", action="store_true", help="rebuild the outcome table")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cands = load_outcomes(V2, args.rebuild)
    results, trades, yearly = run_configs(cands, BOOKS, price_score_setups(), V2, "v2")
    results.to_parquet(CLEAN / "backtest_results_v2.parquet")
    yearly.to_parquet(CLEAN / "backtest_yearly_v2.parquet")
    trades.to_parquet(CLEAN / "backtest_trades_v2.parquet")
    report_backtest.write_v2(results, trades, yearly, cands)
    print((RESULTS / "backtest_v2.md").resolve(), datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
