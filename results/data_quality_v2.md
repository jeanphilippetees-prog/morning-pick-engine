# Data quality report v2

As of 2026-11-24 (generated 2026-11-24T19:22:09Z). Source: Yahoo Finance via yfinance, daily bars from 2016-11-24; candidates from the public TMX company directory (TSX and TSXV). Changes from v1 follow the PM review of 2026-11-24: history for every candidate, docs/corrections.csv applied on load, point-in-time eligibility.

**Known gaps:** CSE names are not covered (no TMX directory, patchy Yahoo .CN data); the live trial still covers CSE. Survivorship: Yahoo only has names listed today, so delisted and acquired names are missing and every backtest on this data is an upper bound.

## Candidates and download

- Candidates after dropping ETFs, funds, split corps, preferreds, debentures, warrants, USD lines and capital pool companies: 1981 (REIT and trust units kept, type = unit).
- Candidates with any Yahoo data: 1979; without: 2 (TSXV:AVX, TSXV:PVF.A).
- Candidates ever eligible (point-in-time, any day since 2016-11-24): 537. Eligible at the last close: 234 regular, 58 small-cap (results/universe_v2.csv).

Ever-eligible names by type:

| type | names | eligible_days |
|---|---|---|
| common | 511 | 414771 |
| unit | 26 | 30340 |

## Point-in-time eligibility

A name can get a signal for session t only if, at the close of t-1: it passes a book gate (regular: close >= $5 and 20-day average close x volume >= $5M; small-cap: $1 <= close < $5 and >= $1M), at most 4 of its last 20 sessions had zero volume, t-1 itself traded, and none of its last 60 sessions carries a blocking flag (bad_ohlc, bad_print, gap_jump, jump, level_shift, split_unadjusted).

Average number of names per session. *gate* = book gate and zero-volume rules; *eligible* = gate plus a clean 60-session lookback.

| year | regular gate | regular eligible | smallcap gate | smallcap eligible |
|---|---|---|---|---|
| 2016 | 31.10 | 31.10 | 4.40 | 4.40 |
| 2017 | 119.70 | 119.50 | 16.80 | 16.20 |
| 2018 | 126.20 | 126.10 | 19.90 | 19.40 |
| 2019 | 131.60 | 131.40 | 19.80 | 19.70 |
| 2020 | 149.00 | 147.10 | 23.80 | 21.60 |
| 2021 | 164.80 | 163.40 | 24.90 | 22.90 |
| 2022 | 162.60 | 162.40 | 24.40 | 24.00 |
| 2023 | 148.40 | 148.20 | 20.00 | 19.20 |
| 2024 | 151.10 | 150.30 | 21.90 | 21.60 |
| 2025 | 181.30 | 180.20 | 31.50 | 30.20 |
| 2026 | 225.90 | 225.10 | 50.60 | 49.40 |

The 60-session flag lookback removes 0.9% of name-days that pass the gate.

## Corrections (docs/corrections.csv)

| ticker | date | action | flags on that date after cleaning |
|---|---|---|---|
| TSX:TLRY | 2025-12-02 | split ratio 0.1 | none |
| TSX:TLO | 2026-01-27 | split ratio 0.1 | none |
| TSX:FDY | 2020-07-08 | split ratio 0.25 | none |
| TSX:CVE | 2020-03-09 | verified real move | jump, level_shift |
| TSX:BHC | 2022-07-28 | verified real move | jump, level_shift |
| TSX:SSRM | 2024-02-13 | verified real move | jump, level_shift |
| TSX:LAC | 2025-09-24 | verified real move | gap_jump, jump, level_shift |
| TSX:VZLA | 2020-07-08 | verified real move | gap_jump, jump, level_shift |
| TSX:SDE | 2023-06-21 | verified real move | gap_jump, jump, level_shift |
| TSX:SDE | 2019-11-13 | drop history before | none |
| TSX:TLG | 2017-02-15 | drop history before | none |
| TSX:CVVY | 2017-11-02 | drop history before | none |
| TSXV:ZDC | 2020-04-06 | drop history before | none |
| TSX:ATX | 2020-09-29 | drop history before | none |
| TSX:HMMC | 2025-01-06 | drop history before | none |
| TSXV:MOON | 2024-08-16 | drop history before | none |

All split corrections remove the jump on the split date.

### Automatic drops

Level shifts outside corrections.csv are unconfirmed by default: the history before the latest one is dropped (the name's data starts at the shift). Sorted by eligible days after the drop.

| ticker | starts | ever_eligible | eligible_days |
|---|---|---|---|
| TSX:NDM | 2020-11-25 | True | 226 |
| TSXV:QNC | 2024-02-26 | True | 223 |
| TSXV:SLI | 2016-12-05 | True | 211 |
| TSXV:ASE | 2021-08-05 | True | 137 |
| TSXV:GOT | 2019-10-28 | True | 122 |
| TSXV:WRLG | 2020-01-27 | True | 104 |
| TSXV:NAU | 2020-01-28 | True | 98 |
| TSX:MNO | 2016-12-08 | True | 91 |
| TSX:TSK | 2023-09-06 | True | 82 |
| TSXV:FOBI | 2020-07-17 | True | 78 |
| TSXV:NDA | 2018-12-19 | True | 77 |
| TSXV:SALT | 2019-11-11 | True | 75 |
| TSXV:APGO | 2017-05-02 | True | 62 |
| TSXV:QTWO | 2021-08-18 | True | 60 |
| TSXV:SRGE | 2017-12-06 | True | 54 |
| TSXV:SIG | 2018-10-11 | True | 51 |
| TSX:TMQ | 2025-10-07 | True | 49 |
| TSXV:CGNT | 2024-01-19 | True | 43 |
| TSXV:LIB | 2019-11-07 | True | 41 |
| TSXV:AGX | 2018-12-27 | True | 41 |
| TSXV:CERT | 2020-02-06 | True | 37 |
| TSXV:GORO | 2022-09-20 | True | 25 |
| TSX:NEXT | 2021-02-08 | True | 24 |
| TSXV:NURS | 2021-08-31 | True | 19 |
| TSXV:LIXX | 2020-02-05 | True | 18 |
| TSXV:PPP | 2025-10-01 | True | 18 |
| TSXV:KRY | 2016-11-29 | True | 17 |
| TSXV:OGN | 2018-12-06 | True | 16 |
| TSXV:ZOMD | 2018-04-27 | True | 15 |
| TSXV:ANDC | 2023-12-01 | True | 15 |
| TSX:TCL.A | 2026-03-23 | True | 12 |
| TSXV:RECO | 2022-11-09 | True | 10 |
| TSXV:SOU | 2017-08-15 | True | 10 |
| TSXV:THRM | 2020-07-24 | True | 10 |
| TSXV:AGAG | 2018-03-06 | True | 9 |
| TSXV:GSVR | 2019-03-14 | True | 3 |
| TSX:DII.B | 2022-02-02 | True | 3 |
| TSX:TALA | 2024-02-15 | True | 2 |
| TSXV:AZM | 2020-01-14 | True | 1 |
| TSXV:VPI | 2024-06-19 | False | 0 |

508 names in total; the full list is in results/data_quality_flags_v2.csv as the level shift dates.

## Summary after cleaning

| group | names | full_10y | median_years | bars | missing_days | zero_volume_days | jumps | gap_jumps | bad_ohlc | bad_print | level_shift | split_unadjusted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ever eligible | 537 | 368 | 10.00 | 1179531 | 15 | 32731 | 785 | 395 | 1 | 120 | 6 | 0 |
| never eligible | 1442 | 565 | 6.86 | 2252354 | 1292 | 531847 | 10303 | 7912 | 721 | 2914 | 0 | 1 |

**XIC.TO benchmark:** 2016-11-24 to 2026-11-24, 2509 sessions, 0 zero-volume days, 0 jumps over 40%.

## Ever-eligible names: missing days

| ticker | missing_days | sessions | eligible_days |
|---|---|---|---|
| TSXV:DMX | 4 | 2505 | 44 |
| TSX:WELL | 3 | 2506 | 1611 |
| TSXV:FAN | 2 | 2507 | 5 |
| TSX:TLG | 2 | 2451 | 293 |
| TSX:CHR | 1 | 2508 | 168 |
| TSX:CRON | 1 | 2508 | 1214 |
| TSXV:GSVR | 1 | 1932 | 3 |
| TSXV:KRY | 1 | 2505 | 17 |

## Ever-eligible names: zero-volume days

| ticker | zero_volume_days | sessions | eligible_days |
|---|---|---|---|
| TSXV:AGAG | 1342 | 2190 | 9 |
| TSXV:BFM | 999 | 2509 | 75 |
| TSXV:MLP | 980 | 2234 | 149 |
| TSXV:FAN | 837 | 2507 | 5 |
| TSXV:OMG | 813 | 2509 | 297 |
| TSXV:DMX | 742 | 2505 | 44 |
| TSXV:TDG | 730 | 2052 | 27 |
| TSXV:APGO | 679 | 2401 | 62 |
| TSXV:STE | 630 | 2509 | 21 |
| TSX:CNL | 618 | 1976 | 86 |
| TSX:ELF | 547 | 2509 | 1 |
| TSXV:WRLG | 547 | 1715 | 104 |
| TSXV:THX | 509 | 2509 | 27 |
| TSXV:ZOMD | 507 | 2153 | 15 |
| TSXV:AGX | 457 | 1986 | 41 |

## Ever-eligible names: jumps over 40%

1180 flagged bars across 198 ever-eligible names. Most recent 20:

| date | ticker | flag | detail |
|---|---|---|---|
| 2026-11-16 | TSXV:ASE | jump | close -41.5% |
| 2026-11-12 | TSXV:TDG | jump | close +44.9% |
| 2026-11-12 | TSX:DND | jump | close -43.4% |
| 2026-10-15 | TSXV:BRW | jump | close +50.0% |
| 2026-10-14 | TSX:CORS | jump | close -42.9% |
| 2026-10-13 | TSX:CORS | jump | close -83.7% |
| 2026-10-13 | TSX:CORS | gap_jump | open -83.0% vs prior close |
| 2026-09-29 | TSX:DND | jump | close +144.2% |
| 2026-09-28 | TSX:SGR.UN | gap_jump | open +61.6% vs prior close |
| 2026-09-28 | TSX:SGR.UN | jump | close +64.6% |
| 2026-09-24 | TSX:THNC | gap_jump | open +62.5% vs prior close |
| 2026-09-24 | TSX:THNC | jump | close +90.0% |
| 2026-09-16 | TSX:GLO | jump | close +44.9% |
| 2026-08-21 | TSX:S | jump | close +42.9% |
| 2026-08-20 | TSX:S | jump | close -41.7% |
| 2026-08-13 | TSXV:FOBI | gap_jump | open +50.0% vs prior close |
| 2026-08-05 | TSX:GTE | gap_jump | open +50.7% vs prior close |
| 2026-07-15 | TSX:ELVA | gap_jump | open +53.7% vs prior close |
| 2026-07-15 | TSX:ELVA | jump | close +48.6% |
| 2026-07-10 | TSX:NVO | gap_jump | open -98.3% vs prior close |

## Ever-eligible names: bad prints and bad OHLC

| ticker | bad_print | sessions | eligible_days |
|---|---|---|---|
| TSXV:SOU | 37 | 2329 | 10 |
| TSXV:AMT | 15 | 2178 | 30 |
| TSXV:OMG | 8 | 2509 | 297 |
| TSXV:GSVR | 4 | 1932 | 3 |
| TSXV:NAU | 4 | 1714 | 98 |
| TSXV:LIB | 4 | 1769 | 41 |
| TSXV:DMX | 3 | 2505 | 44 |
| TSXV:BFM | 3 | 2509 | 75 |
| TSXV:THRM | 3 | 1590 | 10 |
| TSXV:IFOS | 3 | 2509 | 23 |
| TSXV:WRLG | 3 | 1715 | 104 |
| TSXV:ESK | 2 | 2509 | 17 |
| TSXV:AGAG | 2 | 2190 | 9 |
| TSXV:APGO | 2 | 2401 | 62 |
| TSXV:FAN | 2 | 2507 | 5 |

| ticker | bad_ohlc | sessions | eligible_days |
|---|---|---|---|
| TSX:FTG | 1 | 2509 | 17 |

## Caveats

- Survivorship (above). The point-in-time universe reduces, but does not remove, the bias.
- CSE not covered (above).
- Prices are Yahoo's split-adjusted (not dividend-adjusted) bars, so limits, stops and targets match real quotes; dividends come from Yahoo's dividend history. adj_close is used only for XIC.
- Missed splits are found only when the jump is near a common ratio and the new level holds; a missed split hidden inside a normal-looking move would not be caught.
