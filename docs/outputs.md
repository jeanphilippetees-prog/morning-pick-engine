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

**Tickers** in every output file use the trade log's format: `TSX:XYZ`, `TSXV:XYZ` (later `CSE:XYZ`). Share classes and units keep the TMX dot: `TSX:CCL.B`, `TSX:REI.UN`. Yahoo symbols (`CCL-B.TO`, `REI-UN.TO`) are internal only; a `yahoo` column may appear next to `ticker` for traceability.

**docs/corrections.csv** (committed, applied on every load): manual data fixes.

```csv
ticker,date,ratio,reason,source
TSX:TLRY,2025-12-02,0.1,1-for-10 reverse split not adjusted by Yahoo,https://...
```

`ratio` is Yahoo's split convention (new shares per old share; 0.1 = 1-for-10): prices before `date` are divided by it, volume multiplied. `ratio` 1 = verified real move (no change). `ratio` 0 = unconfirmed shift: every bar before `date` is dropped.

**results/universe_v2.csv** (phase 1, v2): names that pass a book gate at the last close.

```csv
yahoo,ticker,book,type,last_date,close,value_traded_20d,zero_volume_20d,clean_lookback,exchange,name
RY.TO,TSX:RY,regular,common,2026-11-23,270.2900,998084138.8293,0,True,TSX,Royal Bank of Canada
```

`type` is `common` or `unit` (REIT and trust units, `.UN`). `clean_lookback` is False when a blocking flag sits in the last 60 sessions.

**results/data_quality_flags_v2.csv** (phase 1, v2): one row per flagged bar after corrections. `flag` is one of jump, gap_jump, zero_volume, bad_ohlc, split_unadjusted, level_shift, bad_print, missing_day. Blocking flags (jump, gap_jump, bad_ohlc, bad_print, split_unadjusted, level_shift) stop any signal whose 60-session lookback contains them and are skipped inside a trade.

```csv
ticker,date,flag,detail
TSXV:XYZ,2024-03-11,jump,close +52.0%
```

**results/data_quality_v2.md** (phase 1, v2): candidates and download, point-in-time eligibility by book and year, corrections and automatic drops, flags after cleaning, caveats. The v1 files (universe_v1.csv, data_quality_flags_v1.csv, data_quality_v1.md) are kept as reviewed; they use the old `TSX:BBD-B` style tickers.

**results/backtest_v1.md** (on demand): one table per book with every metric from docs/rules.md, base and each variant as rows, in-sample and out-of-sample as columns, the random baseline and XIC on the last rows, then a short list of caveats. Plus results/trades_v1.csv with every simulated trade.

The report also has a summary (best and worst out-of-sample configurations, counts that beat random and XIC), setup frequency per day, an all-configurations matrix per book, by-year tables, flagged-bar counts and XIC over each trade's own window.

**results/trades_v1.csv** (phase 2): one row per filled and closed trade in every configuration. Missed orders and trades still open at the end of the data are not rows.

```csv
book,threshold,market_filter,variant,period,ticker,type,universe,signal_date,fill_date,exit_date,price_score,trend,thrust,room,fits_stop,limit,fill,exit_price,reason,sessions,skipped_bars,dividends,gross,net,shares,xic_window_return
main,3,Yes,base,OOS,TSX:XYZ,common,regular,2024-03-08,2024-03-11,2024-03-15,3,1,0,1,1,10.05,9.98,10.7784,Target,5,0,0,0.08,0.077,334,0.0041
```

`period` is IS (fills 2016-2022) or OOS (fills from 2023). `reason` is Stop, Gap stop, Target, Gap target or Time stop. `shares` is whole for the main book and fractional for shadow and small-cap. `xic_window_return` is XIC's total return from the signal close to the exit date.
