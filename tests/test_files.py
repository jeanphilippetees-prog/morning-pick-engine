import gzip

import pandas as pd

from engine import files


def test_write_and_read_gz_round_trip(tmp_path):
    df = pd.DataFrame({"ticker": ["TSX:RY", "TSX:CCL.B"], "net": [0.01, -0.02]})
    out = files.write_csv_gz(df, tmp_path / "trades.csv", index=False)
    assert out.name == "trades.csv.gz" and not (tmp_path / "trades.csv").exists()
    pd.testing.assert_frame_equal(files.read_csv(tmp_path / "trades.csv"), df)   # plain name resolves to .gz
    pd.testing.assert_frame_equal(files.read_csv(out), df)


def test_same_table_same_bytes(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    # gzip stores the file name, so compare two writes of the same name
    a = files.write_csv_gz(df, tmp_path / "a.csv", index=False).read_bytes()
    b = files.write_csv_gz(df, tmp_path / "a.csv", index=False).read_bytes()
    assert a == b


def test_compress_file_keeps_bytes(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes(b"a,b\n1,2\n")
    out = files.compress_file(p)
    assert gzip.open(out).read() == b"a,b\n1,2\n" and not p.exists()
    assert files.read_csv(tmp_path / "x.csv").shape == (1, 2)
