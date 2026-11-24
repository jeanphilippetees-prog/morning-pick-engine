import math

import numpy as np
import pandas as pd
import pytest

from engine import backtest as bt

CAL = pd.bdate_range("2023-01-02", periods=6)


def cand(sym, t_i, score, value, fill=10.0, exit_i=None, exit_price=10.0, filled=True, reason="Time stop",
         universe="regular", variant="base", net=None, limit=None):
    exit_i = t_i if exit_i is None else exit_i
    gross = exit_price / fill - 1 if filled else math.nan
    return {"t": CAL[t_i], "s": CAL[t_i] - pd.Timedelta(days=1), "yahoo": sym, "universe": universe,
            "limit": fill if limit is None else limit, "strict": False, "market_ok": True,
            "price_score": score, "value_traded_20d": value, "variant": variant, "filled": filled,
            "fill": fill if filled else math.nan, "exit_date": CAL[exit_i] if filled else pd.NaT,
            "exit_price": exit_price if filled else math.nan, "reason": reason if filled else "Missed",
            "sessions": exit_i - t_i + 1, "skipped": 0, "dividends": 0.0, "gross": gross,
            "net": (gross - 0.003) if net is None and filled else net}


def marks(syms, price=10.0):
    return {s: pd.Series(price, index=CAL) for s in syms}


MAIN = bt.MAIN


def run(rows, threshold=2, book=MAIN, settings=bt.V1, full=False):
    c = pd.DataFrame(rows)
    out = bt.run_book(book, c, bt.price_score_setup(threshold, False), CAL, marks(c["yahoo"].unique()), settings)
    return out if full else out[:3]


def test_three_slots_ranked_by_score_then_value():
    rows = [cand("A", 0, 4, 1e6, exit_i=3), cand("B", 0, 3, 9e6, exit_i=3), cand("C", 0, 3, 8e6, exit_i=3),
            cand("D", 0, 3, 7e6, exit_i=3), cand("E", 0, 2, 9e9, exit_i=3)]
    tr, orders, _ = run(rows)
    assert sorted(tr["yahoo"]) == ["A", "B", "C"]
    assert orders.iloc[0] == 3


def test_threshold_filters_scores():
    tr, _, _ = run([cand("A", 0, 2, 1e6), cand("B", 0, 3, 1e6)], threshold=3)
    assert list(tr["yahoo"]) == ["B"]


def test_skip_ticker_already_open():
    rows = [cand("A", 0, 4, 1e6, exit_i=4), cand("A", 1, 4, 1e6), cand("B", 1, 3, 1e6)]
    tr, _, _ = run(rows)
    assert sorted(zip(tr["yahoo"], tr["fill_date"])) == [("A", CAL[0]), ("B", CAL[1])]


def test_slot_frees_the_session_after_an_exit():
    full = [cand(s, 0, 4, 1e6, exit_i=2) for s in "ABC"]
    later = [cand("D", 2, 4, 1e6), cand("E", 3, 4, 1e6)]
    tr, _, _ = run(full + later)
    assert "D" not in set(tr["yahoo"])             # exits on day 2 are not free for day-2 orders
    assert "E" in set(tr["yahoo"])


def test_missed_order_does_not_hold_a_slot():
    rows = [cand("A", 0, 4, 1e6, filled=False), cand("B", 1, 4, 1e6)]
    tr, orders, _ = run(rows)
    assert list(tr["yahoo"]) == ["B"] and orders.sum() == 2


def test_main_account_whole_shares_and_cost():
    # equity 30,000 / 3 = 10,000 at $10.01 -> 999 shares; exit +10% minus 0.3% round trip
    rows = [cand("A", 0, 4, 1e6, fill=10.01, exit_i=1, exit_price=11.011)]
    tr, _, eq = run(rows)
    assert tr["shares"].iloc[0] == 999
    pnl = 999 * (11.011 - 10.01) - 0.003 * 999 * 10.01
    assert eq.iloc[-1] == pytest.approx(bt.V1.main_equity + pnl)


def test_shadow_equal_weight_fractional():
    rows = [cand("A", 0, 4, 1e6, fill=10.01, exit_i=1, exit_price=11.011)]
    tr, _, eq = run(rows, book=bt.SHADOW)
    assert tr["shares"].iloc[0] == pytest.approx(10_000 / 10.01)
    assert eq.iloc[-1] == pytest.approx(bt.V1.equal_equity * (1 + (0.10 - 0.003) / 3))


def test_random_baseline_draws_same_count_from_the_day_pool():
    rows = [cand(s, 0, 2, 1e6, net=n) for s, n in zip("ABCD", [0.1, -0.1, 0.1, -0.1])]
    c = pd.DataFrame(rows)
    orders = pd.Series({CAL[0]: 2})
    r = bt.random_baseline(c, orders, np.random.default_rng(1))
    assert (r["n"] == 2).all()
    assert set(np.round(r["sum"], 6)) <= {0.2, 0.0, -0.2}



# --- v2 main account: $1,000, whole shares at the limit, skip for price ---------

def test_v2_main_skips_names_it_cannot_afford_and_takes_the_next():
    # $1,000 / 3 = $333.33 per position: a $400 share is skipped, the $20 name is taken
    rows = [cand("BIG", 0, 4, 9e9, fill=400.0, exit_i=2), cand("CHEAP", 0, 3, 1e6, fill=20.0, exit_i=2)]
    tr, orders, eq, info = run(rows, settings=bt.V2, full=True)
    assert list(tr["yahoo"]) == ["CHEAP"] and info["skipped_price"] == 1
    assert tr["shares"].iloc[0] == 16            # floor(333.33 / 20.00)
    assert orders.sum() == 1


def test_v2_main_sizes_on_the_limit():
    # limit 10.05, fill at the open 9.98: shares = floor(333.33 / 10.05) = 33
    rows = [cand("A", 0, 4, 1e6, fill=9.98, limit=10.05, exit_i=1, exit_price=9.98)]
    tr, _, eq, _ = run(rows, settings=bt.V2, full=True)
    assert tr["shares"].iloc[0] == 33
    assert eq.iloc[-1] == pytest.approx(1000 - 0.003 * 33 * 9.98)


def test_v2_main_skips_for_cash_when_cash_is_short():
    # Day 0: A and B fill 33 shares at $10 -> $660 invested, $340 cash. They then mark at $20,
    # so equity = 340 + 1,320 = 1,660 and equity / 3 = 553. Day 1: C at $400 is affordable by
    # position size (553) but not by cash (340) -> skipped for cash; D at $15 is taken.
    rows = [cand("A", 0, 4, 2e6, fill=10.0, exit_i=5), cand("B", 0, 4, 1e6, fill=10.0, exit_i=5),
            cand("C", 1, 4, 9e6, fill=400.0, exit_i=5), cand("D", 1, 3, 1e6, fill=15.0, exit_i=5)]
    c = pd.DataFrame(rows)
    m = {s: pd.Series(20.0, index=CAL) for s in "AB"} | {s: pd.Series(p, index=CAL) for s, p in (("C", 400.0), ("D", 15.0))}
    tr, _, _, info = bt.run_book(bt.MAIN, c, bt.price_score_setup(2, False), CAL, m, bt.V2)
    assert info["skipped_cash"] == 1 and info["skipped_price"] == 0
    assert sorted(tr["yahoo"]) == ["A", "B", "D"]
    assert tr.set_index("yahoo").at["D", "shares"] == 22   # floor(min(340, 553) / 15)


def test_random_baseline_respects_the_price_cap():
    rows = [cand("A", 0, 2, 1e6, fill=500.0, net=0.5), cand("B", 0, 2, 1e6, fill=10.0, net=-0.1)]
    c = pd.DataFrame(rows)
    r = bt.random_baseline(c, pd.Series({CAL[0]: 1}), np.random.default_rng(1), caps=pd.Series({CAL[0]: 333.0}))
    assert (np.round(r["sum"], 6) == -0.1).all()


def test_v2_blocking_ignores_real_jumps():
    assert "jump" not in bt.V2.blocking and "bad_print" in bt.V2.blocking
