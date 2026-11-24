"""Hand-worked examples for docs/strategies.md."""
import numpy as np
import pandas as pd
import pytest

from engine import systematic as sy


def month_end_series(values, start="2020-01-31"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="BME"), dtype=float)


# --- 12-1 momentum -------------------------------------------------------------

def test_12_1_return_skips_the_latest_month():
    # month-ends m0..m12; 12 months ago = 100, 1 month ago = 120, latest = 130 (skipped)
    adj = month_end_series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 120, 130])
    mom = sy.momentum(adj.to_frame("A"), lookback=12, skip=1)
    assert mom["A"].iloc[-1] == pytest.approx(120 / 100 - 1)
    assert np.isnan(mom["A"].iloc[-2])          # only 12 month-ends: not enough history


def test_6_1_return():
    adj = month_end_series([50, 60, 70, 80, 90, 100, 110, 999])
    assert sy.momentum(adj.to_frame("A"), lookback=6, skip=1)["A"].iloc[-1] == pytest.approx(110 / 60 - 1)


# --- trend filter and execution timing ----------------------------------------

def test_trend_filter_uses_last_10_month_ends_including_this_one():
    closes = month_end_series([10] * 9 + [10.0])
    assert not sy.trend_filter(closes).iloc[-1]         # equal to the average: not above
    closes = month_end_series([10] * 9 + [10.1])
    assert sy.trend_filter(closes).iloc[-1]
    assert not sy.trend_filter(month_end_series([10] * 9)).any()   # fewer than 10 month-ends


def daily(prices, start="2020-01-27"):
    idx = pd.bdate_range(start, periods=len(prices))
    p = pd.Series(prices, index=idx, dtype=float)
    return pd.DataFrame({"open": p, "close": p, "adj_close": p})


def test_trade_happens_at_the_next_open_not_the_signal_close():
    cal = pd.bdate_range("2020-01-27", periods=10)        # month-end is Fri 2020-01-31 (index 4)
    sig = sy.month_ends(cal)
    assert sig[0] == pd.Timestamp("2020-01-31")
    assert sy.trade_date(cal, sig[0]) == pd.Timestamp("2020-02-03")


# --- buffer ------------------------------------------------------------------------

def test_buffer_keeps_rank_15_drops_rank_21_and_fills_from_the_top():
    ranked = [f"N{i}" for i in range(1, 31)]               # N1 is best
    held = {"N15", "N21"} | {f"N{i}" for i in range(1, 9)}
    new = sy.select(ranked, held, n=10, buffer=20)
    assert "N15" in new and "N21" not in new
    # N1-N8 and N15 stay; the slot N21 frees goes to N9, the best-ranked name not held
    assert set(new) == {f"N{i}" for i in range(1, 10)} | {"N15"}


def test_no_buffer_is_plain_top_n():
    ranked = [f"N{i}" for i in range(1, 31)]
    assert sy.select(ranked, {"N15"}, n=10, buffer=10) == [f"N{i}" for i in range(1, 11)]


# --- costs ---------------------------------------------------------------------------

def test_costs_charged_on_traded_value_only():
    # $3,000 book in A and B ($1,500 each); switch B for C at equal weight: sell 1,500 B, buy 1,500 C
    cost = sy.rebalance_cost({"A": 1500.0, "B": 1500.0}, {"A": 0.5, "C": 0.5}, 3000.0, side=0.0015)
    assert cost == pytest.approx(0.0015 * 3000)
    assert sy.rebalance_cost({"A": 1500.0, "B": 1500.0}, {"A": 0.5, "B": 0.5}, 3000.0, side=0.0015) == 0.0


# --- whole shares at $1,000 -------------------------------------------------------------

def test_whole_shares_at_1000_with_a_350_stock_and_top_5():
    prices = {"BIG": 350.0, "A": 20.0, "B": 45.0, "C": 199.0, "D": 201.0}
    shares, cash, missed = sy.whole_share_orders(1000.0, prices, ["BIG", "A", "B", "C", "D"], side=0.0)
    assert shares["BIG"] == 0 and missed == ["BIG", "D"]   # $200 slot: $350 and $201 shares do not fit
    assert shares == {"BIG": 0, "A": 10, "B": 4, "C": 1, "D": 0}
    assert cash == pytest.approx(1000 - 10 * 20 - 4 * 45 - 199)


# --- no look-ahead -------------------------------------------------------------------------

def test_prices_after_the_signal_close_do_not_change_the_signal():
    idx = pd.bdate_range("2019-01-01", "2020-06-30")
    rng = np.random.default_rng(0)
    adj = pd.DataFrame({k: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx)))) for k in "ABC"}, index=idx)
    sig = pd.Timestamp("2020-03-31")
    m1 = sy.momentum(sy.month_end_values(adj, sy.month_ends(idx)), 12, 1)
    changed = adj.copy()
    changed.loc[changed.index > sig] *= 3.0
    m2 = sy.momentum(sy.month_end_values(changed, sy.month_ends(idx)), 12, 1)
    pd.testing.assert_series_equal(m1.loc[sig], m2.loc[sig])
