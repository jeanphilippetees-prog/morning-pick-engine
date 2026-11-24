# Output formats

_Copied from SPEC.md, section "Output formats". Do not change a format without updating this file._

The scheduled tasks read these files, so their shape is fixed. Prices in CAD, returns as decimals, dates as YYYY-MM-DD.

**screener/latest.json** (nightly)

```json
{
  "as_of": "2026-11-24",
  "generated_utc": "2026-11-24T22:41:00Z",
  "market": {"xic_close": 0.0, "xic_sma50": 0.0, "filter": "Yes"},
  "counts": {"regular_universe": 0, "smallcap_universe": 0, "price_score_3_plus": 0},
  "names": [
    {"ticker": "TSX:XYZ", "book": "regular", "close": 0.0, "value_traded_20d_m": 0.0,
     "ret_20d": 0.0, "sma20": 0.0, "sma50": 0.0, "high_52w": 0.0, "atr14": 0.0,
     "vol_ratio": 0.0, "trend": 1, "thrust": 0, "room": 1, "fits_stop": 1, "price_score": 3,
     "limit_if_picked": 0.0}
  ],
  "data_issues": ["XYZ.V: no data for 2026-11-24"]
}
```

`names` holds every name with price score >= 2, sorted by score then value traded, regular and small-cap together (the `book` field tells them apart).

**prices/recent.csv** (nightly): one row per ticker per session for the last 30 sessions, both universes plus XIC.

```csv
date,ticker,open,high,low,close,adj_close,volume
2026-11-24,TSX:XYZ,10.02,10.31,9.95,10.20,10.20,412000
```

**results/backtest_v1.md** (on demand): one table per book with every metric from docs/rules.md, base and each variant as rows, in-sample and out-of-sample as columns, the random baseline and XIC on the last rows, then a short list of caveats. Plus results/trades_v1.csv with every simulated trade.
