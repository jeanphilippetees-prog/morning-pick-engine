import pandas as pd
import pytest

from engine import data


def raw_frame(dates, closes, tz="America/Toronto"):
    idx = pd.DatetimeIndex(pd.to_datetime(dates)).tz_localize(tz)
    return pd.DataFrame({"Open": closes, "High": [c + 0.1 for c in closes], "Low": [c - 0.1 for c in closes],
                         "Close": closes, "Adj Close": [c * 0.98 for c in closes], "Volume": [100] * len(closes)},
                        index=idx)


@pytest.mark.parametrize("yahoo,out", [("XYZ.TO", "TSX:XYZ"), ("ABC.V", "TSXV:ABC"), ("Q.CN", "CSE:Q"),
                                       ("BBD-B.TO", "TSX:BBD-B")])
def test_ticker_round_trip(yahoo, out):
    assert data.to_output_ticker(yahoo) == out
    assert data.to_yahoo(out) == yahoo


def test_tmx_class_shares_use_dash():
    assert data.tmx_symbol_to_yahoo("BBD.B", "TSX") == "BBD-B.TO"
    assert data.tmx_symbol_to_yahoo("REI.UN", "TSX") == "REI-UN.TO"
    assert data.tmx_symbol_to_yahoo("abc", "TSXV") == "ABC.V"


def test_non_canadian_symbol_rejected():
    with pytest.raises(ValueError):
        data.to_output_ticker("AAPL")


def test_normalize_strips_tz_dedupes_and_drops_empty_close():
    raw = raw_frame(["2026-11-20", "2026-11-23", "2026-11-23"], [10.0, 10.5, 10.6])
    raw.loc[raw.index[0], "Close"] = float("nan")
    df = data.normalize_history(raw)
    assert list(df.columns) == data.PRICE_COLS
    assert df.index.tz is None
    assert list(df.index) == [pd.Timestamp("2026-11-23")]
    assert df["close"].iloc[0] == 10.6  # last duplicate wins
    assert df["volume"].dtype == "int64"


def test_merge_new_rows_win():
    old = data.normalize_history(raw_frame(["2026-11-20", "2026-11-23"], [10.0, 10.5]))
    new = data.normalize_history(raw_frame(["2026-11-23", "2026-11-24"], [10.4, 10.7]))
    merged = data.merge_into_cache(old, new)
    assert list(merged["close"]) == [10.0, 10.4, 10.7]


def test_download_batches_and_skips_empty():
    calls = []

    def fake(symbols, start, end):
        calls.append(list(symbols))
        frames = {s: raw_frame(["2026-11-23"], [5.0]) for s in symbols if s != "DEAD.V"}
        frames["DEAD.V"] = raw_frame(["2026-11-23"], [float("nan")])
        return pd.concat({s: frames[s] for s in symbols}, axis=1)

    got = data.download(["A.TO", "B.TO", "DEAD.V"], "2016-01-01", batch=2, pause=0, fetcher=fake)
    assert calls == [["A.TO", "B.TO"], ["DEAD.V"]]
    assert set(got) == {"A.TO", "B.TO"}


def test_cache_round_trip(tmp_path):
    df = data.normalize_history(raw_frame(["2026-11-23", "2026-11-24"], [10.0, 10.2]))
    data.save_cached("XYZ.TO", df, tmp_path)
    pd.testing.assert_frame_equal(data.load_cached("XYZ.TO", tmp_path), df, check_freq=False)
    assert data.load_cached("NOPE.TO", tmp_path) is None
