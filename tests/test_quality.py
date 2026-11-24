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


def test_lasting_10x_jump_without_recorded_split_is_level_shift():
    # price was already sliding before the jump; compare with the prior close
    # TLRY.TO-style 1-for-10 consolidation that Yahoo never adjusted
    closes = [1.47, 1.29, 1.15, 1.10, 10.78, 9.86, 10.05, 10.17, 9.97]
    f = flags_of(bars(closes))
    assert {"jump", "gap_jump", "level_shift"} <= set(f)
    assert "bad_print" not in f


def test_one_day_half_price_print_is_bad_print():
    # OMG.V-style: 0.15 flat, one print at 0.075, then back to 0.15
    closes = [0.15] * 5 + [0.075] + [0.15] * 5
    f = q.bar_flags(bars(closes))
    assert list(f.loc[f["flag"].isin(["bad_print", "level_shift"]), "flag"]) == ["bad_print", "bad_print"]


def test_tiny_recorded_split_is_not_checked():
    # Yahoo records stock dividends as splits like 0.987; a normal 1% move must not flag
    df = bars([10.0, 9.87])
    assert flags_of(df, pd.Series([0.987], index=[df.index[1]])) == []


def test_recorded_split_still_in_prices_is_unadjusted():
    df = bars([10, 5.0], opens=[10, 5.0])
    splits = pd.Series([2.0], index=[df.index[1]])
    f = flags_of(df, splits)
    assert "split_unadjusted" in f and "level_shift" not in f


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


def test_two_tick_flip_flop_is_bad_print_not_level_shift():
    # ATX-style: a thin name bouncing between 0.30 and 0.60 for days at a time
    closes = [0.6, 0.6, 0.3, 0.3, 0.3, 0.6, 0.6, 0.6, 0.6, 0.6]
    f = q.bar_flags(bars(closes))
    assert list(f.loc[f["flag"].isin(["bad_print", "level_shift"]), "flag"]) == ["bad_print", "bad_print"]
