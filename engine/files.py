"""CSV files in results/: large tables are committed gzip-compressed (.csv.gz).

No committed file may be over MAX_BYTES (CLAUDE.md). Readers accept either the
plain or the compressed name, so a caller can ask for "trades_v2.csv" and get
"trades_v2.csv.gz".
"""
from __future__ import annotations

import gzip
import shutil
from pathlib import Path

import pandas as pd

MAX_BYTES = 10 * 1024 * 1024
GZIP = {"method": "gzip", "mtime": 0}  # mtime 0: the same table gives the same bytes


def gz_path(path) -> Path:
    path = Path(path)
    return path if path.suffix == ".gz" else path.with_name(path.name + ".gz")


def write_csv_gz(df: pd.DataFrame, path, **kw) -> Path:
    """Write df as <name>.csv.gz and remove a stale uncompressed copy."""
    out = gz_path(path)
    df.to_csv(out, compression=GZIP, **kw)
    plain = out.with_name(out.name[:-3])
    if plain.exists():
        plain.unlink()
    return out


def resolve(path) -> Path:
    """The existing file for a .csv or .csv.gz name."""
    path = Path(path)
    for p in (path, gz_path(path), path.with_name(path.name[:-3]) if path.suffix == ".gz" else None):
        if p is not None and p.exists():
            return p
    raise FileNotFoundError(path)


def read_csv(path, **kw) -> pd.DataFrame:
    return pd.read_csv(resolve(path), **kw)  # pandas infers gzip from the suffix


def compress_file(path) -> Path:
    """Compress an existing CSV byte for byte, then delete the original."""
    path = Path(path)
    out = gz_path(path)
    with open(path, "rb") as src, gzip.GzipFile(out, "wb", mtime=0) as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()
    return out
