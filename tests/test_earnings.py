import pandas as pd

from engine import earnings

CAL = pd.bdate_range("2026-03-02", periods=10)  # Mon 2 Mar ... Fri 13 Mar


def when(*stamps):
    return pd.Series(pd.DatetimeIndex(stamps).tz_localize(earnings.TZ))


def test_after_close_reacts_next_session():
    assert earnings.reaction_sessions(when("2026-03-03 17:00"), CAL) == {pd.Timestamp("2026-03-04")}


def test_before_open_reacts_same_session():
    assert earnings.reaction_sessions(when("2026-03-03 07:00"), CAL) == {pd.Timestamp("2026-03-03")}


def test_unknown_time_or_intraday_takes_both():
    both = {pd.Timestamp("2026-03-03"), pd.Timestamp("2026-03-04")}
    assert earnings.reaction_sessions(when("2026-03-03 00:00"), CAL) == both
    assert earnings.reaction_sessions(when("2026-03-03 12:00"), CAL) == both


def test_weekend_release_reacts_monday():
    assert earnings.reaction_sessions(when("2026-03-07 10:00"), CAL) == {pd.Timestamp("2026-03-09")}
