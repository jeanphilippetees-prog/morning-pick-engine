import pandas as pd
import pytest

from engine import universe as u

DIRECTORY = {"results": [
    {"symbol": "RY", "name": "Royal Bank of Canada", "instruments": [
        {"symbol": "RY", "name": "Royal Bank"}, {"symbol": "RY.PR.J", "name": "Royal Bank Pr J"},
        {"symbol": "RY.U", "name": "Royal Bank US"}]},
    {"symbol": "BBD.B", "name": "Bombardier Inc.", "instruments": [
        {"symbol": "BBD.A", "name": "Bombardier A"}, {"symbol": "BBD.B", "name": "Bombardier B"}]},
    {"symbol": "REI.UN", "name": "RioCan Real Estate Investment Trust", "instruments": [
        {"symbol": "REI.UN", "name": "RioCan Un"}]},
    {"symbol": "XIU", "name": "iShares S&P/TSX 60 Index ETF", "instruments": [{"symbol": "XIU", "name": "x"}]},
    {"symbol": "ABC", "name": "ABC Mining", "instruments": [{"symbol": "ABC.WT", "name": "Wt"},
                                                             {"symbol": "ABC.DB", "name": "Deb"}]},
]}


def test_directory_keeps_common_and_units_only():
    c = u.candidates_from_directory(DIRECTORY, "TSX")
    assert sorted(c["yahoo"]) == ["BBD-A.TO", "BBD-B.TO", "REI-UN.TO", "RY.TO"]


def test_capital_pool_companies_dropped():
    d = {"results": [{"symbol": "CPC.P", "name": "Shell Capital Corp.", "instruments": [{"symbol": "CPC.P"}]}]}
    assert u.candidates_from_directory(d, "TSXV").empty


@pytest.mark.parametrize("close,value,book", [
    (5.00, 5_000_000, "regular"),     # both gates inclusive
    (4.99, 5_000_000, "smallcap"),    # under $5 is small-cap
    (4.99, 999_999, None),            # small-cap needs $1M/day
    (1.00, 1_000_000, "smallcap"),    # $1 inclusive
    (0.99, 9_000_000, None),          # under $1 is out
    (50.0, 4_999_999, None),          # regular price but not liquid enough
    (float("nan"), 9e9, None),
])
def test_assign_book(close, value, book):
    assert u.assign_book(close, value) == book


def bars(closes, volumes):
    idx = pd.bdate_range("2026-10-01", periods=len(closes), name="date")
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes,
                         "adj_close": closes, "volume": volumes}, index=idx)


def test_liquidity_uses_last_20_sessions():
    # 5 old sessions at $1 x 1 share, then 20 sessions at $10 x 600,000 shares = $6M/day
    df = bars([1.0] * 5 + [10.0] * 20, [1] * 5 + [600_000] * 20)
    snap = u.liquidity_snapshot(df)
    assert snap["value_traded_20d"] == pytest.approx(6_000_000)
    assert snap["close"] == 10.0


def test_short_history_is_not_gated():
    snap = u.liquidity_snapshot(bars([10.0] * 19, [10**6] * 19))
    assert pd.isna(snap["value_traded_20d"])


def test_filter_universe():
    got = u.filter_universe({"BIG.TO": bars([10.0] * 20, [600_000] * 20),
                             "SMALL.V": bars([2.0] * 20, [600_000] * 20),
                             "THIN.V": bars([2.0] * 20, [1_000] * 20)})
    assert dict(zip(got["yahoo"], got["book"])) == {"BIG.TO": "regular", "SMALL.V": "smallcap"}


def test_daily_eligibility_point_in_time():
    # 25 sessions at $10 x 600k = $6M/day -> regular from session 20 on
    df = bars([10.0] * 25, [600_000] * 25)
    e = u.daily_eligibility(df)
    assert not e["eligible"].iloc[18]          # only 19 sessions of history
    assert e["eligible"].iloc[19] and e["book"].iloc[19] == "regular"


def test_zero_volume_rules():
    vols = [600_000] * 20 + [0] * 4 + [600_000] + [0] + [600_000]
    df = bars([10.0] * len(vols), vols)
    e = u.daily_eligibility(df)
    assert not e["gate_ok"].iloc[20]           # zero volume on the signal day itself
    # session 24: last 20 hold 4 zero days -> still allowed (value avg 4.8M fails though)
    assert e["zero_volume_20d"].iloc[24] == 4
    assert e["zero_volume_20d"].iloc[26] == 5 and not e["gate_ok"].iloc[26]   # >4 of 20


def test_flag_blocks_signals_for_60_sessions():
    df = bars([10.0] * 100, [600_000] * 100)
    e = u.daily_eligibility(df, blocked_dates=[df.index[30]])
    assert e["eligible"].iloc[29]
    assert not e["eligible"].iloc[30] and not e["eligible"].iloc[89]   # 30..89 = 60 sessions
    assert e["eligible"].iloc[90]
