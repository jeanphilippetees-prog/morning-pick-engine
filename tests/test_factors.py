import numpy as np
import pandas as pd
import pytest

from engine import factors


def frame(closes, volumes=None, spread=0.1):
    idx = pd.bdate_range("2020-01-01", periods=len(closes), name="date")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c, "high": c + spread, "low": c - spread, "close": c,
                         "volume": volumes if volumes is not None else [1000] * len(c)}, index=idx)


def test_trend():
    f = factors.compute(frame(np.linspace(10, 20, 300)))
    assert f["trend"].iloc[-1] == 1                    # rising: close > SMA20 > SMA50
    f = factors.compute(frame(np.linspace(20, 10, 300)))
    assert f["trend"].iloc[-1] == 0


def test_thrust_needs_2pct_and_1_5x_prior_volume():
    closes = [10.0] * 299 + [10.20]                    # +2.0% on the last day
    f = factors.compute(frame(closes, [1000] * 299 + [1500]))
    assert f["thrust"].iloc[-1] == 1                   # exactly 2% and exactly 1.5x
    f = factors.compute(frame(closes, [1000] * 299 + [1499]))
    assert f["thrust"].iloc[-1] == 0
    f = factors.compute(frame([10.0] * 299 + [10.19], [1000] * 299 + [5000]))
    assert f["thrust"].iloc[-1] == 0


def test_room_pullback_or_breakout():
    # 52w high 20.1 (high of a 20.0 close); now 19.0 <= 0.95 x 20.1 = 19.095 -> room
    f = factors.compute(frame([20.0] * 260 + [19.0]))
    assert f["room"].iloc[-1] == 1
    f = factors.compute(frame([20.0] * 260 + [19.5]))  # near the high, no breakout
    assert f["room"].iloc[-1] == 0
    f = factors.compute(frame([20.0] * 260 + [20.5]))  # close above every prior high: breakout
    assert f["room"].iloc[-1] == 1


def test_fits_the_stop():
    # ATR 0.2 on a $10 stock = 2% and not stretched -> 1
    f = factors.compute(frame([10.0] * 300))
    assert f["fits_stop"].iloc[-1] == 1
    f = factors.compute(frame([10.0] * 300, spread=0.25))  # ATR 0.5 = 5% > 4%
    assert f["fits_stop"].iloc[-1] == 0
    f = factors.compute(frame([10.0] * 299 + [11.2]))      # 11.2 > 1.10 x SMA20 (~10.06)
    assert f["fits_stop"].iloc[-1] == 0


def test_not_scoreable_before_a_year_of_history():
    f = factors.compute(frame([10.0] * 252))
    assert not f["scoreable"].iloc[-1]                # needs 252 prior sessions for the breakout test
    f = factors.compute(frame([10.0] * 253))
    assert f["scoreable"].iloc[-1]


def test_score_uses_only_data_to_the_row_close():
    base = frame(np.linspace(10, 20, 300))
    f1 = factors.compute(base)
    changed = base.copy()
    changed.iloc[-1, :4] = 1.0                         # a crash on the last day
    f2 = factors.compute(changed)
    pd.testing.assert_frame_equal(f1.iloc[:-1], f2.iloc[:-1])


def test_market_filter():
    xic = frame(list(np.linspace(30, 40, 60)))
    assert factors.market_filter(xic).iloc[-1]
    assert not factors.market_filter(xic).iloc[10]     # no SMA50 yet
