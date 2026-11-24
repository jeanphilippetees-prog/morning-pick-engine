"""Hand-worked examples for every rule in docs/rules.md.

The first block is the acceptance list from SPEC.md, word for word in the test
names. Bars are built session by session: fill day = session 1.
"""
import math

import pandas as pd
import pytest

from engine import simulate as sim


def bars(rows, start="2026-03-02"):
    """rows: list of (open, high, low, close) or (open, high, low, close, volume)."""
    idx = pd.bdate_range(start, periods=len(rows), name="date")
    out = []
    for r in rows:
        o, h, l, c, *v = r
        out.append({"open": o, "high": h, "low": l, "close": c, "volume": v[0] if v else 1000})
    return pd.DataFrame(out, index=idx)


FLAT = (10.0, 10.2, 9.8, 10.0)  # a quiet session: no stop (9.50) and no target (10.80)


def trade(rows, limit=10.0, **kw):
    return sim.simulate_trade(bars(rows), limit, **kw)


# --- SPEC.md acceptance tests -------------------------------------------------

def test_buy_limit_1005_next_open_998_filled_at_998():
    assert sim.fill_price(10.05, open_=9.98, low=9.90, volume=1000) == 9.98


def test_limit_1005_open_1020_low_1001_filled_at_1005():
    assert sim.fill_price(10.05, open_=10.20, low=10.01, volume=1000) == 10.05


def test_limit_1005_low_1006_missed():
    assert sim.fill_price(10.05, open_=10.20, low=10.06, volume=1000) is None
    t = trade([(10.20, 10.30, 10.06, 10.10)], limit=10.05)
    assert t["reason"] == "Missed" and not t["filled"]


def test_fill_1000_later_session_opens_940_gap_stop_at_940():
    t = trade([FLAT, FLAT, (9.40, 9.60, 9.30, 9.50)])
    assert (t["reason"], t["exit_price"], t["sessions"]) == ("Gap stop", 9.40, 3)


def test_fill_1000_session_low_945_high_1090_stop_at_950_stop_first():
    t = trade([FLAT, (10.0, 10.90, 9.45, 10.5)])
    assert (t["reason"], t["exit_price"]) == ("Stop", pytest.approx(9.50))


def test_fill_1000_session_opens_1095_gap_target_at_1095():
    t = trade([FLAT, (10.95, 11.0, 10.85, 10.9)])
    assert (t["reason"], t["exit_price"]) == ("Gap target", 10.95)


def test_fill_1000_nothing_in_10_sessions_time_stop_at_10th_close():
    rows = [FLAT] * 9 + [(10.0, 10.2, 9.8, 10.07)] + [(10.0, 12.0, 8.0, 10.0)]
    t = trade(rows)
    assert (t["reason"], t["exit_price"], t["sessions"]) == ("Time stop", 10.07, 10)
    assert t["exit_date"] == bars(rows).index[9]


def test_fill_day_low_948_stops_on_fill_day():
    t = trade([(10.0, 10.2, 9.48, 9.9)])
    assert (t["reason"], t["exit_price"], t["sessions"]) == ("Stop", pytest.approx(9.50), 1)


def test_fill_day_high_1090_alone_is_no_target_that_day():
    t = trade([(10.0, 10.90, 9.9, 10.5)] + [FLAT] * 9)
    assert t["reason"] == "Time stop"


def test_net_is_gross_minus_0003_regular_and_001_smallcap():
    rows = [FLAT, (10.0, 10.9, 9.9, 10.5)]  # target at 10.80 on session 2: gross +8%
    reg = trade(rows, cost=sim.COST["regular"])
    small = trade(rows, cost=sim.COST["smallcap"])
    assert reg["gross"] == pytest.approx(0.08)
    assert reg["net"] == pytest.approx(0.08 - 0.003)
    assert small["net"] == pytest.approx(0.08 - 0.01)


# --- More base-exit examples ---------------------------------------------------

def test_limit_is_prior_close_times_1005():
    assert sim.buy_limit(10.0) == pytest.approx(10.05)


def test_target_intraday_session_2():
    t = trade([FLAT, (10.2, 10.85, 10.1, 10.6)])
    assert (t["reason"], t["exit_price"]) == ("Target", pytest.approx(10.80))


def test_gap_stop_checked_before_gap_target_order():
    # open exactly at the stop is a gap stop, at open
    t = trade([FLAT, (9.50, 10.0, 9.4, 9.8)])
    assert (t["reason"], t["exit_price"]) == ("Gap stop", 9.50)


def test_open_at_target_is_gap_target():
    t = trade([FLAT, (10.80, 10.9, 10.7, 10.8)])
    assert (t["reason"], t["exit_price"]) == ("Gap target", 10.80)


def test_fill_at_limit_when_open_above():
    t = trade([(10.20, 10.30, 10.01, 10.10)] + [FLAT] * 9, limit=10.05)
    assert t["fill"] == 10.05 and t["exit_price"] == 10.0
    assert t["gross"] == pytest.approx(10.0 / 10.05 - 1)


def test_no_fill_on_zero_volume_day():
    t = trade([(9.9, 10.0, 9.8, 9.9, 0)])
    assert t["reason"] == "Missed" and not t["filled"]


def test_time_stop_5_and_15():
    rows = [FLAT] * 16
    assert trade(rows, variant="time5")["sessions"] == 5
    assert trade(rows, variant="time15")["sessions"] == 15


def test_open_trade_at_end_of_data():
    t = trade([FLAT] * 4)
    assert t["reason"] == "Open" and t["sessions"] == 4


# --- Flagged bars inside a trade ----------------------------------------------

def test_flagged_bar_is_skipped_and_checks_move_to_next_clean_bar():
    rows = [FLAT, (5.0, 5.0, 4.0, 4.5), (10.0, 10.2, 9.8, 10.0)] + [FLAT] * 9
    df = bars(rows)
    t = sim.simulate_trade(df, 10.0, flagged=[False, True] + [False] * 10)
    assert t["skipped"] == 1                       # the bad print never triggers the stop
    assert t["reason"] == "Time stop" and t["sessions"] == 10
    assert t["exit_date"] == df.index[10]          # 10 clean sessions = 11 calendar bars


def test_flagged_fill_day_is_not_filled():
    t = sim.simulate_trade(bars([FLAT, FLAT]), 10.0, flagged=[True, False])
    assert t["reason"] == "Missed (flagged)" and not t["filled"]


# --- Dividends ---------------------------------------------------------------

def test_dividend_inside_window_adds_to_gross():
    df = bars([FLAT] * 10)
    divs = pd.Series([0.20], index=[df.index[3]])
    t = sim.simulate_trade(df, 10.0, dividends=divs)
    assert t["dividends"] == pytest.approx(0.20)
    assert t["gross"] == pytest.approx(0.02)       # (10.00 + 0.20) / 10.00 - 1


def test_dividend_on_fill_day_or_after_exit_does_not_count():
    df = bars([FLAT] * 11)
    divs = pd.Series([0.30, 0.40], index=[df.index[0], df.index[10]])
    t = sim.simulate_trade(df, 10.0, dividends=divs)
    assert t["dividends"] == 0 and t["gross"] == pytest.approx(0.0)


def test_dividend_on_gap_stop_day_counts():
    # held through the close before the ex-date, so the dividend is owed
    df = bars([FLAT, FLAT, (9.40, 9.6, 9.3, 9.5)])
    t = sim.simulate_trade(df, 10.0, dividends=pd.Series([0.10], index=[df.index[2]]))
    assert t["gross"] == pytest.approx((9.40 + 0.10) / 10.0 - 1)


# --- Trail ---------------------------------------------------------------------

def test_trail_stop_rises_with_highest_high_of_prior_sessions():
    # highs 10.2, 11.0 -> from session 3 the stop is 11.0 x 0.94 = 10.34
    rows = [FLAT, (10.5, 11.0, 10.4, 10.9), (10.8, 10.9, 10.30, 10.5)]
    t = trade(rows, variant="trail")
    assert (t["reason"], t["exit_price"], t["sessions"]) == ("Stop", pytest.approx(10.34), 3)


def test_trail_has_no_target():
    rows = [FLAT, (10.5, 12.0, 10.4, 11.9)] + [(11.9, 12.0, 11.8, 11.9)] * 8
    t = trade(rows, variant="trail")
    assert t["reason"] == "Time stop" and t["exit_price"] == 11.9


def test_trail_floor_is_fill_x_095():
    # fill-day high 10.05 x 0.94 = 9.447 is below the floor, so the stop stays 9.50
    t = trade([(10.0, 10.05, 9.8, 10.0), (9.6, 9.7, 9.49, 9.6)], variant="trail")
    assert (t["reason"], t["exit_price"]) == ("Stop", pytest.approx(9.50))


def test_trail_gap_stop_at_open():
    rows = [FLAT, (10.5, 11.0, 10.4, 10.9), (10.0, 10.2, 9.9, 10.1)]
    t = trade(rows, variant="trail")
    assert (t["reason"], t["exit_price"]) == ("Gap stop", 10.0)


# --- Breakeven ----------------------------------------------------------------

def test_breakeven_moves_stop_to_fill_from_next_session():
    # session 2 high 10.45 >= 10.40, so from session 3 the stop is 10.00
    rows = [FLAT, (10.2, 10.45, 10.1, 10.3), (10.2, 10.3, 9.95, 10.1)]
    t = trade(rows, variant="breakeven")
    assert (t["reason"], t["exit_price"]) == ("Stop", 10.0)


def test_breakeven_not_on_the_same_session():
    # session 2: high 10.45 and low 9.96 -> still the 9.50 stop that day;
    # later sessions stay above the new 10.00 stop
    rows = [FLAT, (10.2, 10.45, 9.96, 10.3)] + [(10.1, 10.3, 10.05, 10.2)] * 8
    t = trade(rows, variant="breakeven")
    assert (t["reason"], t["exit_price"]) == ("Time stop", 10.2)


def test_breakeven_counts_the_fill_day_high():
    rows = [(10.0, 10.45, 9.9, 10.3), (10.1, 10.2, 9.99, 10.1)]
    t = trade(rows, variant="breakeven")
    assert (t["reason"], t["exit_price"]) == ("Stop", 10.0)


def test_breakeven_keeps_the_base_target():
    t = trade([FLAT, (10.2, 10.85, 10.1, 10.6)], variant="breakeven")
    assert (t["reason"], t["exit_price"]) == ("Target", pytest.approx(10.80))


# --- ATR ------------------------------------------------------------------------

def test_atr_stop_and_target():
    # ATR14 = 0.20 -> stop 9.60, target 10.60
    t = trade([FLAT, (10.2, 10.65, 10.1, 10.5)], variant="atr", atr=0.20)
    assert (t["reason"], t["exit_price"]) == ("Target", pytest.approx(10.60))
    t = trade([(10.0, 10.1, 9.55, 9.7)], variant="atr", atr=0.20)
    assert (t["reason"], t["exit_price"], t["sessions"]) == ("Stop", pytest.approx(9.60), 1)


def test_atr_needs_a_value():
    with pytest.raises(ValueError):
        trade([FLAT], variant="atr")


def test_atr14_wilder():
    # constant true range of 0.4 -> ATR 0.4
    df = bars([(10.0, 10.2, 9.8, 10.0)] * 30)
    assert sim.atr14(df).iloc[-1] == pytest.approx(0.4)
    assert math.isnan(sim.atr14(df).iloc[12])


# --- Strict small-cap fill (sensitivity) --------------------------------------

def test_strict_fill_needs_low_half_a_percent_below_limit():
    # limit 10.05 -> strict level 10.05 x 0.995 = 9.99975
    assert sim.fill_price(10.05, open_=9.98, low=10.00, volume=1000, strict=True) is None
    assert sim.fill_price(10.05, open_=9.98, low=9.99, volume=1000, strict=True) == 9.98
    assert sim.fill_price(10.05, open_=10.20, low=9.99, volume=1000, strict=True) == 10.05
    assert sim.fill_price(10.05, open_=10.20, low=10.01, volume=1000) == 10.05   # normal rule fills


def test_strict_fill_in_a_trade():
    t = trade([(10.20, 10.30, 10.01, 10.10)] + [FLAT] * 9, limit=10.05, strict=True)
    assert t["reason"] == "Missed"
