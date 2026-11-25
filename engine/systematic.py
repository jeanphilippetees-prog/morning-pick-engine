"""Systematic strategy study v1: monthly momentum and a market trend filter (docs/strategies.md).

    python -m engine.systematic       # writes results/systematic_v1.md and results/systematic_holdings_v1.csv

Research only. Nothing here touches docs/rules.md or the playbook backtest.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from engine import backtest as bt, data, quality

SIDE_COST = 0.0015
XBB = "XBB.TO"
RUNS = 200
SEED = 20261124
IS_YEARS = (2017, 2022)
OOS_START = 2023


# --- building blocks (unit-tested) ------------------------------------------------

def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last session of each month."""
    s = pd.Series(cal, index=cal)
    return pd.DatetimeIndex(s.groupby([cal.year, cal.month]).max().to_numpy())


def trade_date(cal: pd.DatetimeIndex, signal: pd.Timestamp) -> pd.Timestamp | None:
    i = cal.searchsorted(signal, side="right")
    return cal[i] if i < len(cal) else None


def month_end_values(daily: pd.DataFrame, ends: pd.DatetimeIndex) -> pd.DataFrame:
    """Values at each month-end session (last value on or before it)."""
    return daily.reindex(daily.index.union(ends)).ffill().reindex(ends)


def momentum(month_end_adj: pd.DataFrame, lookback: int = 12, skip: int = 1) -> pd.DataFrame:
    """adj(m - skip) / adj(m - lookback) - 1 at each month-end m."""
    return month_end_adj.shift(skip) / month_end_adj.shift(lookback) - 1


def trend_filter(month_end_close: pd.Series, n: int = 10) -> pd.Series:
    """True when the month-end close is above the average of the last n month-end closes (this one included)."""
    avg = month_end_close.rolling(n, min_periods=n).mean()
    return (month_end_close > avg) & avg.notna()


def select(ranked: list[str], held: set[str], n: int, buffer: int) -> list[str]:
    """Keep held names ranked within `buffer`; fill up to n with the best-ranked names not kept."""
    top_buffer = set(ranked[:buffer])
    keep = [s for s in ranked if s in held and s in top_buffer][:n]
    fill = [s for s in ranked if s not in keep][: n - len(keep)]
    order = {s: i for i, s in enumerate(ranked)}
    return sorted(keep + fill, key=order.get)


def rebalance_cost(current_values: dict[str, float], target_weights: dict[str, float], equity: float,
                   side: float = SIDE_COST) -> float:
    """side x traded value; positions already at target cost nothing."""
    names = set(current_values) | set(target_weights)
    traded = sum(abs(target_weights.get(s, 0.0) * equity - current_values.get(s, 0.0)) for s in names)
    return side * traded


def whole_share_orders(equity: float, prices: dict[str, float], names: list[str], side: float = SIDE_COST):
    """Equal slots of equity / len(names), whole shares at the price; a name whose share costs more than its
    slot is not bought (missed) and its slot stays in cash. Returns (shares, cash, missed)."""
    slot = equity / len(names) if names else 0.0
    shares, spent, missed = {}, 0.0, []
    for s in names:
        k = math.floor(slot / (prices[s] * (1 + side))) if prices[s] > 0 else 0
        shares[s] = k
        spent += k * prices[s] * (1 + side)
        if k == 0:
            missed.append(s)
    return shares, equity - spent, missed


# --- data -------------------------------------------------------------------------

@dataclass
class Panel:
    cal: pd.DatetimeIndex
    ends: pd.DatetimeIndex          # signal month-ends used (first with 12-1 history .. last with a next session)
    trades: pd.DatetimeIndex        # trade date for each signal
    adj_open: pd.DataFrame          # dates x names (dividend-adjusted open)
    adj_close: pd.DataFrame
    open: pd.DataFrame              # split-adjusted nominal
    close: pd.DataFrame
    divs: pd.DataFrame              # dividends by ex-date (nominal, split-adjusted)
    eligible: pd.DataFrame          # month-end x names (point-in-time regular book)
    me_adj: pd.DataFrame            # month-end adjusted closes
    xic_close_me: pd.Series
    has_xbb: bool


def _wide(frames: dict[str, pd.Series], cal) -> pd.DataFrame:
    return pd.DataFrame(frames).reindex(cal)


def load_panel() -> Panel:
    clean = bt.CLEAN
    xic, _ = bt._load_clean(data.BENCHMARK)
    cal = xic.index
    elig = pd.read_parquet(clean / "eligibility.parquet", columns=["yahoo", "date", "book", "gate_ok"])
    reg = elig[elig["gate_ok"] & (elig["book"] == "regular")]
    blocked = bt.blocked_dates(bt.V2)
    names = sorted(reg["yahoo"].unique())
    ao, ac, op, cl, dv, ok = {}, {}, {}, {}, {}, {}
    ends_all = month_ends(cal)
    for sym in names + [data.BENCHMARK] + ([XBB] if (clean / "prices" / f"{XBB}.parquet").exists() else []):
        df, acts = bt._load_clean(sym)
        factor = df["adj_close"] / df["close"]
        ao[sym], ac[sym], op[sym], cl[sym] = df["open"] * factor, df["adj_close"], df["open"], df["close"]
        if "dividends" in acts:
            d = acts["dividends"]
            dv[sym] = d[d > 0]
        if sym in (data.BENCHMARK, XBB):
            continue
        g = reg[reg["yahoo"] == sym].set_index("date")["gate_ok"].reindex(df.index, fill_value=False)
        fl = pd.Series(df.index.isin(list(blocked.get(sym, ()))), index=df.index).astype(int)
        clean_lb = fl.rolling(60, min_periods=1).sum() == 0
        ok[sym] = (g & clean_lb).reindex(cal, fill_value=False)
    adj_close = _wide(ac, cal)
    me_adj = month_end_values(adj_close[names], ends_all)
    eligible = pd.DataFrame(ok).reindex(ends_all).fillna(False).astype(bool)
    divs = pd.DataFrame({k: v for k, v in dv.items()}).reindex(cal).fillna(0.0) if dv else pd.DataFrame(index=cal)
    mom_ok = momentum(me_adj, 12, 1).notna().any(axis=1)
    first = mom_ok.idxmax()
    trades = [trade_date(cal, e) for e in ends_all]
    use = [(e, t) for e, t in zip(ends_all, trades) if e >= first and t is not None]
    return Panel(cal, pd.DatetimeIndex([e for e, _ in use]), pd.DatetimeIndex([t for _, t in use]),
                 _wide(ao, cal), adj_close, _wide(op, cal), _wide(cl, cal), divs, eligible, me_adj,
                 month_end_values(_wide(cl, cal)[[data.BENCHMARK]], ends_all)[data.BENCHMARK],
                 XBB in ac)


# --- strategies ----------------------------------------------------------------------

@dataclass(frozen=True)
class Strategy:
    name: str
    kind: str               # "A" XIC hold, "B" XIC + filter, "C" momentum, "D" momentum + filter
    n: int = 10
    buffer: int = 20
    lookback: int = 12
    off_asset: str = "cash"  # "cash" or "XBB"


PRIMARY = Strategy("D primary", "D")
STRATEGIES = [
    Strategy("A XIC buy and hold", "A"),
    Strategy("B XIC + trend filter", "B"),
    Strategy("C momentum top 10", "C"),
    PRIMARY,
    Strategy("D top 5", "D", n=5, buffer=10),
    Strategy("D top 20", "D", n=20, buffer=40),
    Strategy("D no buffer", "D", buffer=10),
    Strategy("D 6-1 lookback", "D", lookback=6),
    Strategy("D XBB off-asset", "D", off_asset="XBB"),
    Strategy("B XBB off-asset", "B", off_asset="XBB"),
]


def ranking(p: Panel, m: int, lookback: int) -> list[str]:
    """Eligible names at signal m, best 12-1 (or 6-1) return first, buyable at the next open."""
    e = p.ends[m]
    mom = momentum(p.me_adj, lookback, 1).loc[e]
    ok = p.eligible.loc[e] & mom.notna() & p.adj_open.loc[p.trades[m], mom.index].notna()
    return mom[ok[mom.index]].sort_values(ascending=False, kind="mergesort").index.tolist()


def targets(p: Panel, s: Strategy, m: int, held: set[str], rng=None, filt=None) -> dict[str, float]:
    off = {XBB: 1.0} if s.off_asset == "XBB" else {}
    if s.kind == "A":
        return {data.BENCHMARK: 1.0}
    on = bool(filt.loc[p.ends[m]]) if s.kind in ("B", "D") else True
    if s.kind == "B":
        return {data.BENCHMARK: 1.0} if on else off
    if not on:
        return off
    ranked = ranking(p, m, s.lookback)
    if rng is not None:
        ranked = list(rng.permutation(ranked))
    picks = select(ranked, held, s.n, s.buffer)
    return {k: 1.0 / len(picks) for k in picks} if picks else {}


def _exit_value(p: Panel, sym: str, t_next: pd.Timestamp) -> float:
    v = p.adj_open.at[t_next, sym]
    if not np.isnan(v):
        return v
    return p.adj_close[sym].loc[:t_next].dropna().iloc[-1]   # halted or delisted: last adjusted close


def run_weights(p: Panel, s: Strategy, filt: pd.Series, rng=None, daily: bool = True) -> dict:
    """Weight-based monthly run. Returns monthly returns, daily equity, holdings, turnover and trade counts."""
    equity = 1.0
    values: dict[str, float] = {}              # current position values (equity units), drifted
    monthly, rows, turnover, trades = [], [], [], []
    marks = []
    for m in range(len(p.ends) - 1):
        t, t_next = p.trades[m], p.trades[m + 1]
        held = {k for k, v in values.items() if v > 0 and k not in (data.BENCHMARK, XBB)}
        w = targets(p, s, m, held, rng, filt)
        cost = rebalance_cost(values, w, equity)
        traded = sum(abs(w.get(k, 0.0) * equity - values.get(k, 0.0)) for k in set(values) | set(w))
        names_traded = sum(1 for k in set(values) | set(w)
                           if (values.get(k, 0.0) > 0) != (w.get(k, 0.0) > 0))
        start = equity - cost
        new_values = {}
        for k, wk in w.items():
            entry = p.adj_open.at[t, k]
            new_values[k] = start * wk * _exit_value(p, k, t_next) / entry
        cash = start * (1 - sum(w.values()))
        end = cash + sum(new_values.values())
        if daily:
            seg = p.cal[(p.cal >= t) & (p.cal < t_next)]
            rel = sum(start * wk * p.adj_close.loc[seg, k].ffill() / p.adj_open.at[t, k] for k, wk in w.items()) \
                if w else pd.Series(0.0, index=seg)
            marks.append(pd.Series(start, index=[t - pd.Timedelta(hours=1)]))   # value at the open after costs
            marks.append(rel + cash if isinstance(rel, pd.Series) else pd.Series(cash, index=seg))
        monthly.append({"signal": p.ends[m], "trade": t, "ret": end / equity - 1, "invested": sum(w.values()) > 0,
                        "turnover": traded / equity / 2, "names_traded": names_traded})
        rows.append({"month": p.ends[m].strftime("%Y-%m"), "holdings": w})
        equity, values = end, new_values
    out = {"monthly": pd.DataFrame(monthly), "holdings": rows}
    if daily:
        eq = pd.concat(marks)
        out["daily"] = eq[~eq.index.duplicated(keep="last")].sort_index()
    return out


# --- metrics ------------------------------------------------------------------------

def period_mask(df: pd.DataFrame, period: str) -> pd.Series:
    y = df["trade"].dt.year
    return (y >= IS_YEARS[0]) & (y <= IS_YEARS[1]) if period == "IS" else y >= OOS_START


def stats(run: dict, period: str) -> dict:
    mo = run["monthly"]
    sub = mo[period_mask(mo, period)]
    if sub.empty:
        return {}
    growth = (1 + sub["ret"]).prod()
    years = len(sub) / 12
    r = sub["ret"]
    out = {"months": len(sub), "cagr": growth ** (1 / years) - 1, "sharpe": r.mean() / r.std(ddof=1) * math.sqrt(12),
           "worst_month": r.min(), "pct_invested": sub["invested"].mean(),
           "turnover": sub["turnover"].sum() / years, "trades_per_year": sub["names_traded"].sum() / years}
    if "daily" in run:
        d = run["daily"]
        lo, hi = sub["trade"].iloc[0], sub["trade"].iloc[-1] + pd.offsets.MonthEnd(1)
        seg = d[(d.index >= lo - pd.Timedelta(days=1)) & (d.index <= hi)]
        out["max_dd"] = (seg / seg.cummax() - 1).min()
    else:
        eq = (1 + r).cumprod()
        out["max_dd"] = (eq / eq.cummax().clip(lower=1) - 1).min()
    return out


def passes(d: dict, xic: dict, rand_p95: float) -> bool:
    if not d:
        return False
    better = d["cagr"] > xic["cagr"] or (d["sharpe"] > xic["sharpe"] and d["max_dd"] >= xic["max_dd"])
    return d["cagr"] > rand_p95 and better


# --- $1,000 whole-share run ----------------------------------------------------------

def run_whole_shares(p: Panel, s: Strategy, filt: pd.Series, start_cash: float = 1000.0) -> dict:
    cash, shares = start_cash, {}
    monthly, missed_total, drag = [], 0, []
    equity_prev = start_cash
    for m in range(len(p.ends) - 1):
        t, t_next = p.trades[m], p.trades[m + 1]
        px = lambda k, d: p.open.at[d, k] if not np.isnan(p.open.at[d, k]) else p.close[k].loc[:d].dropna().iloc[-1]
        equity = cash + sum(n * px(k, t) for k, n in shares.items())
        held = {k for k, n in shares.items() if n > 0 and k not in (data.BENCHMARK, XBB)}
        w = targets(p, s, m, held, None, filt)
        names = list(w)
        for k, n in shares.items():           # sell everything not kept at the target size, then rebuy
            cash += n * px(k, t) * (1 - SIDE_COST)
        new, cash_left, missed = whole_share_orders(cash, {k: px(k, t) for k in names}, names) if names else ({}, cash, [])
        # Positions kept at the same share count were sold and rebought above; refund that round trip's cost.
        for k in names:
            same = min(shares.get(k, 0), new.get(k, 0))
            cash_left += same * px(k, t) * SIDE_COST * 2
        cash, shares = cash_left, {k: n for k, n in new.items() if n > 0}
        missed_total += len(missed)
        divs = sum(n * p.divs.loc[(p.divs.index > t) & (p.divs.index <= t_next), k].sum()
                   for k, n in shares.items() if k in p.divs.columns)
        cash += divs
        end = cash + sum(n * px(k, t_next) for k, n in shares.items())
        drag.append(cash / end if end else 0.0)
        monthly.append({"signal": p.ends[m], "trade": t, "ret": end / equity_prev - 1, "invested": bool(shares),
                        "turnover": 0.0, "names_traded": 0})
        equity_prev = end
    return {"monthly": pd.DataFrame(monthly), "missed": missed_total, "cash_drag": float(np.mean(drag)),
            "end": equity_prev}


def replay(monthly: pd.Series, start: float = 1000.0, target: float = 10_000.0, add: float = 0.0) -> str:
    v = start
    for i, r in enumerate(monthly, 1):
        v = v * (1 + r) + add
        if v >= target:
            return str(i)
    return f"not reached in {len(monthly)} (ends ${v:,.0f})"


# --- report ----------------------------------------------------------------------------

def _pct(v):
    return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.1%}"


def write(p: Panel, runs: dict, rand: dict, whole: dict, xbb_note: str) -> str:
    xic_is, xic_oos = stats(runs["A XIC buy and hold"], "IS"), stats(runs["A XIC buy and hold"], "OOS")
    prim_is, prim_oos = stats(runs[PRIMARY.name], "IS"), stats(runs[PRIMARY.name], "OOS")
    rp = {k: {per: np.percentile([stats(r, per)["cagr"] for r in v], [5, 50, 95]).tolist() + [
        float(np.mean([stats(r, per)["cagr"] for r in v]))] for per in ("IS", "OOS")} for k, v in rand.items()}
    pass_oos = passes(prim_oos, xic_oos, rp[PRIMARY.name]["OOS"][2])
    pass_is = passes(prim_is, xic_is, rp[PRIMARY.name]["IS"][2])
    verdict = "PASS" if (pass_oos and pass_is) else "FAIL"

    def row(name, per):
        d = stats(runs[name], per)
        x = xic_is if per == "IS" else xic_oos
        r = rp.get(name.split(" XBB")[0] if name in rand else name, {}).get(per)
        return d, x, r

    tbl = []
    for s in STRATEGIES:
        if s.name not in runs:
            continue
        cells = [s.name]
        for col in ("cagr", "sharpe", "max_dd", "worst_month", "pct_invested", "turnover", "trades_per_year"):
            vals = []
            for per in ("IS", "OOS"):
                d = stats(runs[s.name], per)
                v = d.get(col, math.nan)
                vals.append(f"{v:.2f}" if col in ("sharpe", "turnover") else
                            f"{v:.0f}" if col == "trades_per_year" else _pct(v))
            cells.append(" / ".join(vals))
        vs = []
        for per in ("IS", "OOS"):
            d = stats(runs[s.name], per)
            x = xic_is if per == "IS" else xic_oos
            vs.append(f"{d['cagr'] - x['cagr']:+.1%}")
        cells.append(" / ".join(vs))
        r = rp.get(s.name)
        cells.append(" / ".join(f"{_pct(r[per][3])} ({_pct(r[per][0])} to {_pct(r[per][2])})" for per in ("IS", "OOS"))
                     if r else "-")
        if s.kind in ("C", "D") and r:
            ok = [passes(stats(runs[s.name], per), xic_is if per == "IS" else xic_oos, r[per][2]) for per in ("IS", "OOS")]
            cells.append(" / ".join("pass" if o else "fail" for o in ok))
        else:
            cells.append("-")
        tbl.append(cells)

    years = sorted({t.year for t in runs[PRIMARY.name]["monthly"]["trade"]})
    yr_rows = []
    for y in years:
        cells = [str(y)]
        for s in STRATEGIES:
            mo = runs[s.name]["monthly"]
            sub = mo[mo["trade"].dt.year == y]
            cells.append(_pct((1 + sub["ret"]).prod() - 1) if len(sub) else "-")
        yr_rows.append(cells)

    w_rows = []
    for name, res in whole.items():
        base = runs[name.replace(" at $1,000", "")]
        for per in ("IS", "OOS"):
            a, b = stats(base, per), stats(res, per)
            w_rows.append([name, per, _pct(a["cagr"]), _pct(b["cagr"]), f"{b['cagr'] - a['cagr']:+.1%}",
                           _pct(res["cash_drag"]) if per == "IS" else "", str(res["missed"]) if per == "IS" else ""])
    rep_rows = []
    for name in ("A XIC buy and hold", PRIMARY.name):
        r = runs[name]["monthly"]["ret"]
        rep_rows.append([name] + [replay(r, add=a) for a in (0, 250, 500)])

    from engine.report_backtest import table
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    first, last = p.ends[0].date(), p.ends[-2].date()
    out = [
        "# Systematic strategy study v1",
        "",
        f"Generated {now}. Strategies: docs/strategies.md. Signals at month-ends {first} to {last}; trades at the "
        "next session's open. In-sample = months starting 2017-2022, out-of-sample = months starting 2023-today. "
        "**Nothing was tuned**; the primary configuration and every sensitivity were fixed before the run.",
        "",
        "**Survivorship:** Yahoo only has names listed today; delisted and acquired names are missing, so every "
        "stock-picking number here is an upper bound (as in backtest_v1). XIC and XBB are not affected. "
        "**Cash earns 0%**, which understates the filtered strategies a little.",
        "",
        "## Summary",
        "",
        f"**Primary D: {verdict}.** Bar (out-of-sample, fixed in advance): net CAGR above the random 95th "
        "percentile AND (CAGR above XIC OR Sharpe above XIC with max drawdown no worse). It must also hold "
        f"in-sample. Out-of-sample: {'pass' if pass_oos else 'fail'}; in-sample: {'pass' if pass_is else 'fail'}.",
        "",
        table(["", "CAGR", "Sharpe", "Max drawdown", "Random CAGR 95th pct"], [
            ["Primary D, OOS", _pct(prim_oos["cagr"]), f"{prim_oos['sharpe']:.2f}", _pct(prim_oos["max_dd"]),
             _pct(rp[PRIMARY.name]["OOS"][2])],
            ["XIC, OOS", _pct(xic_oos["cagr"]), f"{xic_oos['sharpe']:.2f}", _pct(xic_oos["max_dd"]), "-"],
            ["Primary D, IS", _pct(prim_is["cagr"]), f"{prim_is['sharpe']:.2f}", _pct(prim_is["max_dd"]),
             _pct(rp[PRIMARY.name]["IS"][2])],
            ["XIC, IS", _pct(xic_is["cagr"]), f"{xic_is['sharpe']:.2f}", _pct(xic_is["max_dd"]), "-"]]),
        "## All strategies",
        "",
        "Each cell is in-sample / out-of-sample. Turnover = one-way traded value per year as a share of the book; "
        "trades = names bought or sold per year. vs XIC = CAGR difference. Random = mean CAGR of 200 random-ranking "
        "runs (5th to 95th percentile). Bar = the pass bar in each period.",
        "",
        table(["Strategy", "CAGR", "Sharpe", "Max DD", "Worst month", "Invested", "Turnover", "Trades/yr",
               "vs XIC", "Random CAGR", "Bar"], tbl),
        "## Yearly returns",
        "",
        "Calendar years by trade date (the first and last years are partial).",
        "",
        table(["Year"] + [s.name for s in STRATEGIES], yr_rows),
        "## Realism check: $1,000, whole shares",
        "",
        "Whole shares at the actual open; a name whose one share costs more than its slot is not bought and the "
        "slot stays in cash; dividends paid in cash; same 0.15% per side. Gap = whole-share CAGR minus the "
        "weight-based CAGR. Cash drag = average share of the book in idle cash at month-ends (whole run).",
        "",
        table(["Run", "Period", "Weight-based CAGR", "$1,000 CAGR", "Gap", "Cash drag", "Names missed"], w_rows),
        "### Historical replay: months from $1,000 to $10,000",
        "",
        "**Historical replay, not a forecast:** each strategy's actual monthly returns applied in order from the "
        "first signal, with the contribution added at each month-end.",
        "",
        table(["Strategy", "$0 a month", "$250 a month", "$500 a month"], rep_rows),
        "## Data notes",
        "",
        f"- Universe: point-in-time regular book (phase 1 v2 eligibility, v2 blocking flags); "
        f"{int(p.eligible.loc[p.ends].sum(axis=1).mean()):.0f} eligible names at an average month-end.",
        f"- {xbb_note}",
        "- Momentum uses dividend-adjusted closes; trades use the adjusted open (open x adj_close / close). The "
        "trend filter uses XIC's split-adjusted close.",
        "- Max drawdown uses daily marks for the strategies; random runs use monthly returns (only their CAGR "
        "enters the bar).",
        "- A held name with no open on a trade date (halt) is valued at its last adjusted close.",
        "",
    ]
    text = "\n".join(out)
    (bt.RESULTS / "systematic_v1.md").write_text(text, encoding="utf-8")
    return text


def write_holdings(runs: dict) -> None:
    rows = []
    for name, r in runs.items():
        for h in r["holdings"]:
            ks = list(h["holdings"])
            rows.append({"month": h["month"], "strategy": name,
                         "holdings": ";".join(data.to_output_ticker(k) for k in ks) if ks else "CASH",
                         "weights": ";".join(f"{h['holdings'][k]:.4f}" for k in ks) if ks else "1.0000"})
    pd.DataFrame(rows).to_csv(bt.RESULTS / "systematic_holdings_v1.csv", index=False)


def ensure_xbb() -> str:
    """Download and clean XBB.TO; report whether its data is clean enough to use."""
    data.update_cache([XBB], "2016-11-24", full=True)
    df, acts, flags, cut = quality.clean_history(XBB)
    if df is None or df.empty:
        return "XBB.TO: no data from Yahoo; the XBB sensitivity runs were skipped."
    (bt.CLEAN / "prices").mkdir(parents=True, exist_ok=True)
    df.to_parquet(bt.CLEAN / "prices" / f"{XBB}.parquet")
    acts.to_parquet(bt.CLEAN / "actions" / f"{XBB}.parquet")
    kinds = flags["flag"].value_counts().to_dict() if len(flags) else {}
    bad = {k: v for k, v in kinds.items() if k not in ("zero_volume", "missing_day")}
    return (f"XBB.TO: {len(df)} sessions from {df.index[0].date()}; flags: {kinds or 'none'}"
            + ("; usable." if not bad and cut is None else f"; check before relying on it ({bad})."))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    xbb_note = ensure_xbb()
    p = load_panel()
    filt = trend_filter(p.xic_close_me)
    strategies = [s for s in STRATEGIES if s.off_asset != "XBB" or p.has_xbb]
    runs = {s.name: run_weights(p, s, filt) for s in strategies}
    logging.info("strategies done")
    rng = np.random.default_rng(SEED)
    rand = {}
    for s in strategies:
        if s.kind in ("C", "D"):
            rand[s.name] = [run_weights(p, s, filt, rng, daily=False) for _ in range(RUNS)]
            logging.info("random %s done", s.name)
    whole = {f"{PRIMARY.name} at $1,000": run_whole_shares(p, PRIMARY, filt),
             "D top 5 at $1,000": run_whole_shares(p, next(s for s in STRATEGIES if s.name == "D top 5"), filt)}
    write_holdings(runs)
    write(p, runs, rand, whole, xbb_note)
    print((bt.RESULTS / "systematic_v1.md").resolve())


if __name__ == "__main__":
    main()
