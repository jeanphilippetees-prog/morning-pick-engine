# Data quality report v1

As of 2026-11-24 (generated 2026-11-24T18:26:07Z). Source: Yahoo Finance via yfinance, daily bars from 2016-11-24 to the last session. Candidates: public TMX company directory (TSX and TSXV).

## Universe

Gates from docs/factors.md on the last 20 sessions: regular = close >= $5 and average close x volume >= $5M; small-cap = $1 <= close < $5 and >= $1M.

| book | TSX | TSXV |
|---|---|---|
| regular | 234 | 2 |
| smallcap | 48 | 8 |

- Candidates in the directory after dropping ETFs, funds, preferreds, debentures, warrants, USD lines and capital pool companies: 1981.
- Candidates with no recent Yahoo data: 3.
- Universe names whose 10-year download failed: 0.

## Summary by book

| book | names | full_10y | median_years | sessions | missing_days | zero_volume_days | jumps | gap_jumps | bad_ohlc | splits_recorded | split_unadjusted | level_shift | bad_print |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regular | 236 | 200 | 10.00 | 554377 | 0 | 1627 | 56 | 25 | 0 | 190 | 0 | 6 | 1 |
| smallcap | 56 | 38 | 10.00 | 120365 | 7 | 6690 | 250 | 198 | 0 | 36 | 0 | 13 | 86 |

Flagged bars (any flag except missing days): 1.280% of 677,250 bars.

## Coverage

Names with less than 10 years listed later (IPOs, spin-offs, moves from TSXV) or have a gap at Yahoo.

| history | names |
|---|---|
| 10y | 238 |
| 5-9.9y | 37 |
| 3-5y | 6 |
| 1-3y | 7 |
| <1y | 4 |

**XIC.TO benchmark:** 2016-11-24 to 2026-11-23, 2508 sessions, 0 zero-volume days, 0 jumps over 40%. Missing days are measured against XIC's own calendar, so XIC shows 0 by construction.

## Missing days

XIC sessions inside each name's own first-to-last range with no bar for that name.

| ticker | book | missing_days | sessions |
|---|---|---|---|
| TSX:WELL | smallcap | 3 | 2505 |
| TSX:TLG | smallcap | 2 | 2506 |
| TSX:ATX | smallcap | 1 | 2507 |
| TSX:CRON | smallcap | 1 | 2507 |

## Zero-volume days

These bars cannot be filled (docs: require volume on the fill day).

| ticker | book | zero_volume_days | sessions |
|---|---|---|---|
| TSX:HMMC | smallcap | 978 | 2508 |
| TSXV:OMG | smallcap | 813 | 2508 |
| TSX:ATX | smallcap | 763 | 2507 |
| TSXV:MOON | smallcap | 597 | 2508 |
| TSXV:ZDC | smallcap | 447 | 2508 |
| TSX:APM | smallcap | 421 | 1859 |
| TSX:DSV | regular | 358 | 2508 |
| TSX:SDE | regular | 329 | 2508 |
| TSXV:AFM | smallcap | 253 | 2508 |
| TSX:TLG | smallcap | 247 | 2506 |
| TSXV:NCX | smallcap | 225 | 2508 |
| TSX:NICU | smallcap | 221 | 1592 |
| TSX:WELL | smallcap | 221 | 2505 |
| TSX:GMIN | regular | 213 | 1778 |
| TSX:RIO | smallcap | 201 | 2508 |

## Suspicious jumps (over 40%)

529 flagged bars across 57 names. Most recent 25:

| date | ticker | book | flag | detail |
|---|---|---|---|---|
| 2026-11-12 | TSX:DND | smallcap | jump | close -43.4% |
| 2026-09-29 | TSX:DND | smallcap | jump | close +144.2% |
| 2026-05-04 | TSX:XNDU | smallcap | jump | close -61.0% |
| 2026-05-04 | TSX:XNDU | smallcap | gap_jump | open -61.1% vs prior close |
| 2026-04-22 | TSX:XNDU | smallcap | jump | close +50.3% |
| 2026-04-15 | TSX:XNDU | smallcap | jump | close +68.1% |
| 2026-03-10 | TSX:GSY | regular | jump | close -57.0% |
| 2026-01-27 | TSX:TLO | smallcap | gap_jump | open +886.4% vs prior close |
| 2026-01-27 | TSX:TLO | smallcap | jump | close +915.2% |
| 2025-12-12 | TSX:TLRY | smallcap | jump | close +44.3% |
| 2025-12-08 | TSX:DND | smallcap | jump | close +44.2% |
| 2025-12-02 | TSX:TLRY | smallcap | gap_jump | open +899.1% vs prior close |
| 2025-12-02 | TSX:HMMC | smallcap | gap_jump | open +265.9% vs prior close |
| 2025-12-02 | TSX:HMMC | smallcap | jump | close +222.0% |
| 2025-12-02 | TSX:TLRY | smallcap | jump | close +880.0% |
| 2025-10-14 | TSX:KEEL | smallcap | jump | close +41.0% |
| 2025-09-29 | TSX:TLRY | smallcap | jump | close +59.6% |
| 2025-09-24 | TSX:LAC | smallcap | jump | close +97.9% |
| 2025-09-24 | TSX:LAC | smallcap | gap_jump | open +67.1% vs prior close |
| 2025-08-11 | TSX:TLRY | smallcap | jump | close +41.1% |
| 2025-06-05 | TSX:TLO | smallcap | jump | close +42.1% |
| 2025-06-05 | TSX:TLO | smallcap | gap_jump | open +57.9% vs prior close |
| 2025-05-01 | TSX:HMMC | smallcap | jump | close +48.4% |
| 2025-02-18 | TSX:POU | regular | gap_jump | open -46.5% vs prior close |
| 2025-02-18 | TSX:POU | regular | jump | close -42.9% |

## Split checks

- Splits recorded by Yahoo across the universe: 226, plus 24 minor adjustments (ratios between 0.8 and 1.25: stock dividends and unit consolidations; too small to check against a jump).
- Recorded splits still visible as a price jump (adjustment failed): 0.
- Level shifts: a split-sized jump (ratio near 2, 3, 4, 5, 10, 20 or the inverse) with no split recorded, where the new price level holds: 19. Each is either an unrecorded split (**history before it is on the wrong scale**) or a real crash or spike; price data alone cannot tell them apart, so each needs a hand check before phase 2.

| date | ticker | book | flag | detail |
|---|---|---|---|---|
| 2017-02-15 | TSX:TLG | smallcap | level_shift | price level x1.889 and holds; no split recorded |
| 2017-10-04 | TSX:CVVY | smallcap | level_shift | price level x2.294 and holds; no split recorded |
| 2017-11-02 | TSX:CVVY | smallcap | level_shift | price level x9.000 and holds; no split recorded |
| 2019-09-27 | TSX:SDE | regular | level_shift | price level x0.500 and holds; no split recorded |
| 2019-11-13 | TSX:SDE | regular | level_shift | price level x2.000 and holds; no split recorded |
| 2020-03-09 | TSX:CVE | regular | level_shift | price level x0.527 and holds; no split recorded |
| 2020-04-06 | TSXV:ZDC | smallcap | level_shift | price level x0.500 and holds; no split recorded |
| 2020-07-08 | TSX:VZLA | smallcap | level_shift | price level x1.964 and holds; no split recorded |
| 2020-07-08 | TSX:FDY | smallcap | level_shift | price level x3.727 and holds; no split recorded |
| 2020-09-29 | TSX:ATX | smallcap | level_shift | price level x1.929 and holds; no split recorded |
| 2022-07-28 | TSX:BHC | regular | level_shift | price level x0.530 and holds; no split recorded |
| 2023-06-21 | TSX:SDE | regular | level_shift | price level x0.320 and holds; no split recorded |
| 2024-01-24 | TSX:HMMC | smallcap | level_shift | price level x2.071 and holds; no split recorded |
| 2024-02-13 | TSX:SSRM | regular | level_shift | price level x0.477 and holds; no split recorded |
| 2024-08-16 | TSXV:MOON | smallcap | level_shift | price level x2.000 and holds; no split recorded |
| 2025-01-06 | TSX:HMMC | smallcap | level_shift | price level x0.481 and holds; no split recorded |
| 2025-09-24 | TSX:LAC | smallcap | level_shift | price level x1.979 and holds; no split recorded |
| 2025-12-02 | TSX:TLRY | smallcap | level_shift | price level x9.136 and holds; no split recorded |
| 2026-01-27 | TSX:TLO | smallcap | level_shift | price level x9.788 and holds; no split recorded |

- Bad prints: split-sized jumps that revert, or that flip back within 20 sessions (thin names bouncing between two ticks): 87, by name:

| ticker | bad_prints |
|---|---|
| TSX:ATX | 38 |
| TSXV:MOON | 33 |
| TSXV:OMG | 8 |
| TSX:HMMC | 3 |
| TSX:ESI | 1 |
| TSX:PMET | 1 |
| TSX:JOY | 1 |
| TSX:VLE | 1 |
| TSXV:NCX | 1 |

## Bad OHLC bars

High below low, open or close outside the day's range, or a price <= 0.

_none_

## Caveats

- Survivorship: the universe is today's listed, liquid names. Delisted and acquired names are missing, and names are picked on today's liquidity, so any backtest on it is an upper bound.
- CSE names are not in this universe: the TMX directory covers TSX and TSXV only.
- Yahoo's OHLC is split-adjusted but not dividend-adjusted; adj_close covers both. Yahoo re-adjusts history after each split, so the cache is re-downloaded in full on each phase 1 run.
- Every flagged bar is listed in results/data_quality_flags_v1.csv; later phases must not trade on them.
