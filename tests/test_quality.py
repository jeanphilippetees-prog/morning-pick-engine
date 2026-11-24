import pandas as pd

from engine import quality as q


def bars(closes, opens=None, volumes=None, start="2026-01-05"):
    idx = pd.bdate_range(start, periods=len(closes), name="date")
    opens = opens or closes
    return pd.DataFrame({"open": opens, "high": [max(o, c) for o, c in zip(opens, closes)],
                         "low": [min(o, c) for o, c in zip(opens, closes)], "close": closes,
                         "adj_close": closes, "volume": volumes or [1000] * len(closes)}, index=idx)


def flags_of(df, splits=None):
    return list(q.bar_flags(df, splits)["flag"])


def test_clean_series_has_no_flags():
    assert flags_of(bars([10, 10.5, 10.2, 10.8])) == []


def test_jump_over_40_pct_flagged_but_40_exactly_is_not():
    assert flags_of(bars([10, 14.0])) == []
    assert "jump" in flags_of(bars([10, 14.01], opens=[10, 10.0]))


def test_gap_jump_on_open():
    f = flags_of(bars([10, 10.0], opens=[10, 4.0]))
    assert f == ["gap_jump"]


def test_zero_volume():
    assert flags_of(bars([10, 10], volumes=[1000, 0])) == ["zero_volume"]


def test_bad_ohlc():
    df = bars([10, 10])
    df.loc[df.index[1], "high"] = 9.0
    assert "bad_ohlc" in flags_of(df)


def test_halving_without_recorded_split_is_possible_split():
    f = flags_of(bars([10, 5.0], opens=[10, 5.0]))
    assert {"jump", "possible_split", "gap_jump"} <= set(f)


def test_recorded_split_still_in_prices_is_unadjusted():
    df = bars([10, 5.0], opens=[10, 5.0])
    splits = pd.Series([2.0], index=[df.index[1]])
    f = flags_of(df, splits)
    assert "split_unadjusted" in f and "possible_split" not in f


def test_recorded_split_properly_adjusted_is_clean():
    df = bars([5.0, 5.1])
    assert flags_of(df, pd.Series([2.0], index=[df.index[1]])) == []


def test_missing_days_against_calendar():
    cal = pd.bdate_range("2026-01-05", periods=5)
    df = bars([10, 10, 10, 10, 10]).drop(cal[2])
    miss = q.missing_days(df, cal)
    assert list(miss) == [cal[2]]
    # days before the first bar are not "missing"
    assert list(q.missing_days(df.iloc[2:], cal)) == []
