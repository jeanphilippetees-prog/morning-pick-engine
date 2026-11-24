import math

import numpy as np
import pandas as pd
import pytest

from engine import backtest as bt

CAL = pd.bdate_range("2023-01-02", periods=6)


def cand(sym, t_i, score, value, fill=10.0, exit_i=None, exit_price=10.0, filled=True, reason="Time stop",
         universe="regular", variant="base", net=None):
    exit_i = t_i if exit_i is None else exit_i
    gross = exit_price / fill - 1 if filled else math.nan
    return {"t": CAL[t_i], "s": CAL[t_i] - pd.Timedelta(days=1), "yahoo": sym, "universe": universe,
            "price_score": score, "value_traded_20d": value, "variant": variant, "filled": filled,
            "fill": fill if filled else math.nan, "exit_date": CAL[exit_i] if filled else pd.NaT,
            "exit_price": exit_price if filled else math.nan, "reason": reason if filled else "Missed",
            "sessions": exit_i - t_i + 1, "skipped": 0, "dividends": 0.0, "gross": gross,
            "net": (gross - 0.003) if net is None and filled else net}


def marks(syms, price=10.0):
    return {s: pd.Series(price, index=CAL) for s in syms}


MAIN = bt.BOOKS[0]
NO_FILTER = pd.Series(dtype=bool)


def run(rows, threshold=2, book=MAIN):
    c = pd.DataFrame(rows)
    return bt.run_book(book, threshold, False, "base", c, NO_FILTER, CAL, marks(c["yahoo"].unique()))


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
    assert eq.iloc[-1] == pytest.approx(bt.START_EQUITY + pnl)


def test_shadow_equal_weight_fractional():
    rows = [cand("A", 0, 4, 1e6, fill=10.01, exit_i=1, exit_price=11.011)]
    tr, _, eq = run(rows, book=bt.BOOKS[1])
    assert tr["shares"].iloc[0] == pytest.approx(10_000 / 10.01)
    assert eq.iloc[-1] == pytest.approx(bt.START_EQUITY * (1 + (0.10 - 0.003) / 3))


def test_random_baseline_draws_same_count_from_the_day_pool():
    rows = [cand(s, 0, 2, 1e6, net=n) for s, n in zip("ABCD", [0.1, -0.1, 0.1, -0.1])]
    c = pd.DataFrame(rows)
    orders = pd.Series({CAL[0]: 2})
    r = bt.random_baseline(MAIN, "base", orders, c, np.random.default_rng(1))
    assert (r["n"] == 2).all()
    assert set(np.round(r["sum"], 6)) <= {0.2, 0.0, -0.2}
