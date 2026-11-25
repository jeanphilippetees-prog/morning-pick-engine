# US earnings-drift test v1 (phase 2c)

Generated 2026-11-25T00:28:31Z. Signals 2017-11-28 to 2026-11-24; in-sample = fills 2017-2022, out-of-sample = fills from 2023-01-01. Same engine and rules as the Canadian studies (docs/rules.md exits, v2 blocking flags, random baseline). **Nothing was tuned.**

**Survivorship, strongly:** the universe is *today's* S&P 500 and S&P 400 members. Names that were dropped, acquired or went bankrupt since 2016 are missing, and today's members are partly in the index *because* they did well. Every number here is an upper bound, more so than in the Canadian studies.

## Answer

- **USD account, 0.10% round trip:** earnings +4%/3x in the 3-slot shadow book clears the bar (beats random AND SPY out-of-sample with 100+ trades) for 0 of 6 exits; beats random for 0, beats SPY's CAGR for 0. Out-of-sample trades by exit: atr 264, base 303, breakeven 328, time15 263, time5 423, trail 304.
- **CAD account, 2.0% round trip:** earnings +4%/3x in the 3-slot shadow book clears the bar (beats random AND SPY out-of-sample with 100+ trades) for 0 of 6 exits; beats random for 0, beats SPY's CAGR for 0. Out-of-sample trades by exit: atr 264, base 303, breakeven 328, time15 263, time5 423, trail 304.
- Earnings +4%/3x events per week (candidate universe): 5.43.

## Data

- Universe: 903 current constituents (results/us_universe_v1.csv: S&P 500 and S&P 400 pages on Wikipedia, saved in data/us/source/). Yahoo had no data for 0.
- Quality (same checks as Canada, docs/corrections.csv applied): flagged bars by type: zero_volume 2,248, jump 96, gap_jump 45, bad_ohlc 39, bad_print 9.
- Automatic drops (history before an unresolved split-sized level shift): 7 names: US:ARWR from 2016-11-30, US:CORT from 2025-12-31, US:MTDR from 2020-03-09, US:SHC from 2023-01-10, US:APA from 2020-03-09, US:OXY from 2020-03-09, US:TRGP from 2020-03-09.
- Earnings dates: Yahoo had a calendar for 897 of 897 names in the candidate universe (73,215 past release dates).
- Point-in-time eligible names per session (gate $5 and $20M USD a day): 2017 692, 2018 710, 2019 724, 2020 752, 2021 790, 2022 814, 2023 836, 2024 869, 2025 889, 2026 898.
- Outcome table: every +4%/3x event day plus a fixed 15% uniform sample of all other eligible name-days; the random baseline and the all-candidates average draw only from the sample.

Events in the candidate universe:

| Event | IS events | OOS events | Per week |
|---|---|---|---|
| earnings +4%/3x | 1,168 | 1,285 | 5.43 |
| earnings +6%/5x | 311 | 252 | 1.25 |
| non-earnings +4%/3x | 956 | 858 | 4.01 |

## Summary over every configuration

### USD account, 0.10% round trip

- 18 configurations (shadow book x 3 event setups x 6 exits). 18 have at least 100 out-of-sample trades.
- Out-of-sample, among those 18: 12 have positive net expectancy after costs, 1 beat the random-entry baseline (net expectancy above the 95th percentile of 200 random runs), 1 beat SPY's CAGR, and **1 do both** (the spec's bar for a playbook proposal).
- Configurations that beat random in both periods with 100+ trades each: 1.

### Configurations that clear the bar out-of-sample

| Config | OOS trades | OOS net exp. | OOS win | OOS PF | OOS CAGR | SPY CAGR | Random p95 | Pctile vs random | IS net exp. | IS trades |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow USD / non-earnings +4%/3x / atr | 301 | +1.39% | 53.5% | 1.48 | 36.4% | 19.0% | +0.80% | 100.0% | +1.52% | 369 |


### Best out-of-sample configurations (100+ OOS trades, by net expectancy)

| Config | OOS trades | OOS net exp. | OOS win | OOS PF | OOS CAGR | SPY CAGR | Random p95 | Pctile vs random | IS net exp. | IS trades |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow USD / non-earnings +4%/3x / atr | 301 | +1.39% | 53.5% | 1.48 | 36.4% | 19.0% | +0.80% | 100.0% | +1.52% | 369 |
| shadow USD / earnings +6%/5x / time15 | 157 | +0.61% | 47.1% | 1.25 | 7.6% | 19.0% | +0.98% | 70.5% | +0.11% | 200 |
| shadow USD / earnings +6%/5x / base | 173 | +0.55% | 46.8% | 1.25 | 7.5% | 19.0% | +0.83% | 77.5% | +0.08% | 221 |
| shadow USD / earnings +6%/5x / breakeven | 184 | +0.47% | 37.0% | 1.25 | 6.8% | 19.0% | +0.79% | 74.0% | -0.01% | 229 |
| shadow USD / earnings +6%/5x / time5 | 197 | +0.44% | 47.7% | 1.22 | 6.7% | 19.0% | +0.66% | 83.5% | -0.08% | 255 |
| shadow USD / earnings +4%/3x / atr | 264 | +0.39% | 50.8% | 1.15 | 6.9% | 19.0% | +0.78% | 66.0% | +0.20% | 337 |
| shadow USD / earnings +4%/3x / time5 | 423 | +0.35% | 49.2% | 1.20 | 11.6% | 19.0% | +0.40% | 91.0% | +0.04% | 517 |
| shadow USD / earnings +4%/3x / breakeven | 328 | +0.12% | 37.2% | 1.06 | 2.8% | 19.0% | +0.49% | 51.0% | +0.30% | 397 |
| shadow USD / earnings +6%/5x / atr | 152 | +0.12% | 45.4% | 1.04 | -0.4% | 19.0% | +0.96% | 34.5% | +0.44% | 203 |
| shadow USD / earnings +6%/5x / trail | 179 | +0.11% | 43.0% | 1.05 | 0.9% | 19.0% | +0.85% | 24.5% | +0.02% | 221 |

### Worst out-of-sample configurations

| Config | OOS trades | OOS net exp. | OOS win | OOS PF | OOS CAGR | SPY CAGR | Random p95 | Pctile vs random | IS net exp. | IS trades |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow USD / non-earnings +4%/3x / breakeven | 405 | -0.31% | 30.1% | 0.87 | -12.2% | 19.0% | +0.56% | 2.0% | +0.03% | 482 |
| shadow USD / non-earnings +4%/3x / trail | 383 | -0.31% | 38.1% | 0.87 | -12.0% | 19.0% | +0.58% | 0.5% | -0.12% | 453 |
| shadow USD / non-earnings +4%/3x / base | 375 | -0.29% | 41.3% | 0.90 | -11.0% | 19.0% | +0.62% | 1.5% | +0.11% | 457 |
| shadow USD / non-earnings +4%/3x / time5 | 473 | -0.28% | 42.7% | 0.89 | -13.1% | 19.0% | +0.34% | 2.5% | +0.08% | 559 |
| shadow USD / non-earnings +4%/3x / time15 | 327 | -0.11% | 41.0% | 0.96 | -5.3% | 19.0% | +0.78% | 7.5% | -0.04% | 414 |

Ranking on out-of-sample results is descriptive only. Picking the top row and calling it the rule would be tuning on the out-of-sample period; any change goes through the playbook's proposal process.

### CAD account, 2.0% round trip

- 18 configurations (shadow book x 3 event setups x 6 exits). 18 have at least 100 out-of-sample trades.
- Out-of-sample, among those 18: 0 have positive net expectancy after costs, 1 beat the random-entry baseline (net expectancy above the 95th percentile of 200 random runs), 0 beat SPY's CAGR, and **0 do both** (the spec's bar for a playbook proposal).
- Configurations that beat random in both periods with 100+ trades each: 1.

### Best out-of-sample configurations (100+ OOS trades, by net expectancy)

| Config | OOS trades | OOS net exp. | OOS win | OOS PF | OOS CAGR | SPY CAGR | Random p95 | Pctile vs random | IS net exp. | IS trades |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow CAD / non-earnings +4%/3x / atr | 301 | -0.51% | 42.9% | 0.87 | -16.5% | 19.0% | -1.00% | 100.0% | -0.38% | 369 |
| shadow CAD / earnings +6%/5x / time15 | 157 | -1.29% | 41.4% | 0.63 | -16.7% | 19.0% | -0.92% | 70.5% | -1.79% | 200 |
| shadow CAD / earnings +6%/5x / base | 173 | -1.35% | 39.3% | 0.60 | -18.9% | 19.0% | -0.93% | 75.0% | -1.82% | 221 |
| shadow CAD / earnings +6%/5x / breakeven | 184 | -1.43% | 31.5% | 0.54 | -20.9% | 19.0% | -1.14% | 68.0% | -1.91% | 229 |
| shadow CAD / earnings +6%/5x / time5 | 197 | -1.46% | 37.6% | 0.53 | -22.6% | 19.0% | -1.32% | 87.5% | -1.98% | 255 |
| shadow CAD / earnings +4%/3x / atr | 264 | -1.51% | 42.0% | 0.58 | -30.8% | 19.0% | -1.14% | 71.0% | -1.70% | 337 |
| shadow CAD / earnings +4%/3x / time5 | 423 | -1.55% | 35.7% | 0.46 | -44.3% | 19.0% | -1.54% | 94.5% | -1.86% | 517 |
| shadow CAD / earnings +4%/3x / breakeven | 328 | -1.78% | 31.7% | 0.44 | -40.1% | 19.0% | -1.36% | 50.5% | -1.60% | 397 |
| shadow CAD / earnings +6%/5x / atr | 152 | -1.78% | 36.2% | 0.57 | -22.3% | 19.0% | -0.79% | 30.5% | -1.46% | 203 |
| shadow CAD / earnings +6%/5x / trail | 179 | -1.79% | 29.6% | 0.45 | -24.8% | 19.0% | -0.99% | 29.0% | -1.88% | 221 |

### Worst out-of-sample configurations

| Config | OOS trades | OOS net exp. | OOS win | OOS PF | OOS CAGR | SPY CAGR | Random p95 | Pctile vs random | IS net exp. | IS trades |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow CAD / non-earnings +4%/3x / breakeven | 405 | -2.21% | 24.9% | 0.41 | -55.0% | 19.0% | -1.35% | 1.5% | -1.87% | 482 |
| shadow CAD / non-earnings +4%/3x / trail | 383 | -2.21% | 26.6% | 0.41 | -53.3% | 19.0% | -1.19% | 2.0% | -2.02% | 453 |
| shadow CAD / non-earnings +4%/3x / base | 375 | -2.19% | 33.3% | 0.46 | -52.1% | 19.0% | -1.28% | 2.5% | -1.79% | 457 |
| shadow CAD / non-earnings +4%/3x / time5 | 473 | -2.18% | 33.0% | 0.40 | -60.1% | 19.0% | -1.54% | 1.5% | -1.82% | 559 |
| shadow CAD / non-earnings +4%/3x / time15 | 327 | -2.01% | 33.6% | 0.52 | -44.8% | 19.0% | -1.12% | 4.0% | -1.94% | 414 |

Ranking on out-of-sample results is descriptive only. Picking the top row and calling it the rule would be tuning on the out-of-sample period; any change goes through the playbook's proposal process.

### Robustness of configurations that clear the bar

36 configurations were tested, so about 2 would clear the random 95th percentile by chance alone. Checks: the OOS mean without the best 5 and 10 trades, and the same event and exit with no slot limit (IS / OOS) next to a random entry.

| Config | OOS net exp. | Without top 5 | Without top 10 | Random p95 | Unlimited event IS / OOS | Unlimited random IS / OOS |
|---|---|---|---|---|---|---|
| shadow USD / non-earnings +4%/3x / atr | +1.39% | +0.79% | +0.43% | +0.80% | -0.07% / +0.83% | +0.40% / +0.35% |

## Unlimited event average (every event, no slots)

Each cell: filled trades / mean net return per trade (± 95% interval) / win rate. 'All candidates' is the uniform sample of every eligible name-day: what a random entry earns on average.

### USD account, 0.10% round trip, base exit

| Group | IS | OOS |
|---|---|---|
| all candidates (sample) | 134,192 / +0.18% (±0.03%) / 49.2% | 119,210 / +0.27% (±0.03%) / 48.9% |
| earnings +4%/3x | 1,095 / +0.25% (±0.31%) / 49.8% | 1,184 / +0.24% (±0.32%) / 47.0% |
| earnings +6%/5x | 296 / +0.15% (±0.63%) / 45.9% | 226 / +0.58% (±0.75%) / 46.0% |
| non-earnings +4%/3x | 877 / -0.46% (±0.40%) / 41.2% | 763 / +0.03% (±0.47%) / 42.9% |

### USD account, 0.10% round trip, time15 exit

| Group | IS | OOS |
|---|---|---|
| all candidates (sample) | 134,192 / +0.25% (±0.03%) / 47.6% | 119,210 / +0.34% (±0.03%) / 47.4% |
| earnings +4%/3x | 1,095 / +0.32% (±0.34%) / 47.9% | 1,184 / +0.26% (±0.34%) / 45.9% |
| earnings +6%/5x | 296 / +0.25% (±0.66%) / 45.9% | 226 / +0.58% (±0.78%) / 46.5% |
| non-earnings +4%/3x | 877 / -0.49% (±0.42%) / 38.5% | 763 / +0.17% (±0.49%) / 42.3% |

### CAD account, 2.0% round trip, base exit

| Group | IS | OOS |
|---|---|---|
| all candidates (sample) | 134,192 / -1.72% (±0.03%) / 36.8% | 119,210 / -1.63% (±0.03%) / 36.8% |
| earnings +4%/3x | 1,095 / -1.65% (±0.31%) / 39.5% | 1,184 / -1.66% (±0.32%) / 38.3% |
| earnings +6%/5x | 296 / -1.75% (±0.63%) / 39.5% | 226 / -1.32% (±0.75%) / 40.3% |
| non-earnings +4%/3x | 877 / -2.36% (±0.40%) / 32.8% | 763 / -1.87% (±0.47%) / 35.0% |

### CAD account, 2.0% round trip, time15 exit

| Group | IS | OOS |
|---|---|---|
| all candidates (sample) | 134,192 / -1.65% (±0.03%) / 39.1% | 119,210 / -1.56% (±0.03%) / 39.2% |
| earnings +4%/3x | 1,095 / -1.58% (±0.34%) / 40.2% | 1,184 / -1.64% (±0.34%) / 39.3% |
| earnings +6%/5x | 296 / -1.65% (±0.66%) / 40.2% | 226 / -1.32% (±0.78%) / 42.0% |
| non-earnings +4%/3x | 877 / -2.39% (±0.42%) / 34.3% | 763 / -1.73% (±0.49%) / 37.1% |

### Earnings +4%/3x by year, base exit (unlimited)

| Year | Costs | Trades | Net exp. | 95% interval | Win |
|---|---|---|---|---|---|
| 2017 | USD account | 8 | +0.19% | ±3.65% | 50.0% |
| 2018 | USD account | 249 | -0.19% | ±0.60% | 47.8% |
| 2019 | USD account | 328 | +0.22% | ±0.51% | 52.1% |
| 2020 | USD account | 164 | -0.82% | ±0.87% | 40.2% |
| 2021 | USD account | 162 | +0.95% | ±0.85% | 53.7% |
| 2022 | USD account | 184 | +1.25% | ±0.88% | 53.3% |
| 2023 | USD account | 309 | +0.33% | ±0.57% | 49.5% |
| 2024 | USD account | 381 | +1.05% | ±0.62% | 53.3% |
| 2025 | USD account | 269 | -0.34% | ±0.62% | 41.3% |
| 2026 | USD account | 225 | -0.54% | ±0.73% | 40.0% |
| 2017 | CAD account | 8 | -1.71% | ±3.65% | 37.5% |
| 2018 | CAD account | 249 | -2.09% | ±0.60% | 35.3% |
| 2019 | CAD account | 328 | -1.68% | ±0.51% | 38.4% |
| 2020 | CAD account | 164 | -2.72% | ±0.87% | 30.5% |
| 2021 | CAD account | 162 | -0.95% | ±0.85% | 46.9% |
| 2022 | CAD account | 184 | -0.65% | ±0.88% | 48.4% |
| 2023 | CAD account | 309 | -1.57% | ±0.57% | 37.9% |
| 2024 | CAD account | 381 | -0.85% | ±0.62% | 43.8% |
| 2025 | CAD account | 269 | -2.24% | ±0.62% | 34.9% |
| 2026 | CAD account | 225 | -2.44% | ±0.73% | 33.3% |

## Negative earnings events: do they keep falling? (report only, no trades)

Close-to-close return from the event close, earnings events with |return| >= 4% on >= 3x volume, point-in-time eligible names. No costs, no dividends. Last column: 10-session return minus SPY's.

| Side | Period | Events | 1-session | 5-session | 10-session | 15-session | 10-session vs SPY |
|---|---|---|---|---|---|---|---|
| up | IS | 1,521 | +0.07% (±0.15%), n=1,521 | +0.21% (±0.29%), n=1,521 | +0.32% (±0.37%), n=1,521 | +0.63% (±0.46%), n=1,521 | +0.08% (±0.32%), n=1,521 |
| up | OOS | 1,301 | +0.13% (±0.18%), n=1,301 | +0.20% (±0.33%), n=1,297 | +0.88% (±0.43%), n=1,296 | +1.20% (±0.52%), n=1,281 | +0.04% (±0.41%), n=1,296 |
| down | IS | 1,822 | -0.05% (±0.15%), n=1,822 | +0.04% (±0.27%), n=1,822 | -0.06% (±0.36%), n=1,822 | -0.13% (±0.46%), n=1,822 | -0.30% (±0.31%), n=1,822 |
| down | OOS | 1,687 | +0.14% (±0.16%), n=1,687 | +0.58% (±0.28%), n=1,682 | +0.91% (±0.36%), n=1,680 | +1.12% (±0.42%), n=1,659 | +0.03% (±0.34%), n=1,680 |

## All configurations (shadow book)

Net expectancy per trade after costs, IS | OOS, with OOS trades and whether OOS beats random (R) and SPY (X).

### shadow USD (us_low universe, cost 0.1% round trip)

| Setup | base | trail | breakeven | atr | time5 | time15 |
|---|---|---|---|---|---|---|
| earnings +4%/3x | +0.19% \| +0.11% (303) | +0.03% \| +0.11% (304) | +0.30% \| +0.12% (328) | +0.20% \| +0.39% (264) | +0.04% \| +0.35% (423) | -0.10% \| -0.02% (263) |
| earnings +6%/5x | +0.08% \| +0.55% (173) | +0.02% \| +0.11% (179) | -0.01% \| +0.47% (184) | +0.44% \| +0.12% (152) | -0.08% \| +0.44% (197) | +0.11% \| +0.61% (157) |
| non-earnings +4%/3x | +0.11% \| -0.29% (375) | -0.12% \| -0.31% (383) | +0.03% \| -0.31% (405) | +1.52% \| +1.39% (301, RX) | +0.08% \| -0.28% (473) | -0.04% \| -0.11% (327) |

### shadow CAD (us_high universe, cost 2.0% round trip)

| Setup | base | trail | breakeven | atr | time5 | time15 |
|---|---|---|---|---|---|---|
| earnings +4%/3x | -1.71% \| -1.79% (303) | -1.87% \| -1.79% (304) | -1.60% \| -1.78% (328) | -1.70% \| -1.51% (264) | -1.86% \| -1.55% (423) | -2.00% \| -1.92% (263) |
| earnings +6%/5x | -1.82% \| -1.35% (173) | -1.88% \| -1.79% (179) | -1.91% \| -1.43% (184) | -1.46% \| -1.78% (152) | -1.98% \| -1.46% (197) | -1.79% \| -1.29% (157) |
| non-earnings +4%/3x | -1.79% \| -2.19% (375) | -2.02% \| -2.21% (383) | -1.87% \| -2.21% (405) | -0.38% \| -0.51% (301, R) | -1.82% \| -2.18% (473) | -1.94% \| -2.01% (327) |

## Full metrics

### shadow USD, earnings +4%/3x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 337 / 264 | 1.31 / 1.35 | 53.7% / 50.8% | 4.9% / 5.8% | -5.3% / -5.2% | +0.20% / +0.39% | 1.08 / 1.15 | -42.4% / -49.0% | 25.2% / 25.8% | 3.6% / 1.9% | 11.0% / 11.4% | 0.6% / 1.9% | 59.6% / 59.1% | 8.0 / 8.2 | 88.1% / 90.6% | 2.1% / 6.9% | -7.5% / -12.1% |
| base | 374 / 303 | 1.46 / 1.55 | 48.7% / 45.2% | 5.1% / 5.3% | -4.5% / -4.2% | +0.19% / +0.11% | 1.08 / 1.05 | -41.7% / -25.6% | 36.4% / 37.0% | 3.2% / 1.7% | 15.5% / 16.2% | 3.7% / 3.0% | 41.2% / 42.2% | 6.7 / 6.6 | 85.7% / 87.2% | 2.4% / 1.8% | -7.2% / -17.2% |
| breakeven | 397 / 328 | 1.55 / 1.68 | 42.1% / 37.2% | 5.3% / 5.5% | -3.3% / -3.0% | +0.30% / +0.12% | 1.16 / 1.06 | -37.3% / -24.7% | 42.3% / 45.1% | 6.5% / 6.7% | 14.1% / 14.0% | 3.0% / 2.7% | 34.0% / 31.4% | 6.2 / 5.8 | 82.9% / 84.3% | 6.1% / 2.8% | -3.4% / -16.2% |
| time15 | 330 / 263 | 1.29 / 1.34 | 43.0% / 43.0% | 6.1% / 6.0% | -4.8% / -4.6% | -0.10% / -0.02% | 0.96 / 0.99 | -44.4% / -29.3% | 43.9% / 44.9% | 5.2% / 2.3% | 21.5% / 20.5% | 3.0% / 3.8% | 26.4% / 28.5% | 8.1 / 8.3 | 89.8% / 92.7% | -4.4% / -1.3% | -13.9% / -20.3% |
| time5 | 517 / 423 | 2.02 / 2.16 | 48.9% / 49.2% | 4.0% / 4.3% | -3.8% / -3.5% | +0.04% / +0.35% | 1.02 / 1.20 | -39.9% / -21.8% | 26.9% / 24.8% | 3.1% / 1.7% | 9.5% / 12.1% | 1.9% / 2.6% | 58.6% / 58.9% | 4.0 / 4.0 | 74.5% / 78.5% | -0.3% / 11.6% | -9.9% / -7.4% |
| trail | 379 / 304 | 1.48 / 1.55 | 45.1% / 42.4% | 4.5% / 4.8% | -3.7% / -3.3% | +0.03% / +0.11% | 1.02 / 1.06 | -36.6% / -28.4% | 55.1% / 53.9% | 7.4% / 6.9% | 0.0% / 0.0% | 0.0% / 0.0% | 37.5% / 39.1% | 6.5 / 6.5 | 83.9% / 85.6% | -1.1% / 2.1% | -10.6% / -16.9% |
| random (base exit) | 379.5 / 319.7 | - | 48.0% / 48.0% | - | - | +0.07% / +0.14% | 1.04 / 1.07 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base +0.07% / +0.14% (-0.27% to +0.58%); trail +0.03% / +0.13% (-0.29% to +0.56%); breakeven +0.07% / +0.13% (-0.21% to +0.49%); atr +0.05% / +0.25% (-0.30% to +0.78%); time5 -0.02% / +0.10% (-0.20% to +0.40%); time15 +0.17% / +0.10% (-0.45% to +0.63%)

### shadow USD, earnings +6%/5x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 203 / 152 | 0.79 / 0.78 | 53.2% / 45.4% | 5.9% / 7.0% | -5.8% / -5.6% | +0.44% / +0.12% | 1.16 / 1.04 | -33.1% / -51.3% | 27.1% / 23.7% | 2.0% / 4.6% | 11.3% / 11.2% | 0.0% / 2.0% | 59.6% / 58.6% | 8.0 / 8.0 | 67.9% / 61.0% | 4.7% / -0.4% | -4.9% / -19.3% |
| base | 221 / 173 | 0.86 / 0.88 | 45.2% / 46.8% | 5.7% / 6.0% | -4.5% / -4.2% | +0.08% / +0.55% | 1.03 / 1.25 | -36.5% / -30.4% | 41.2% / 37.0% | 3.2% / 2.9% | 20.4% / 22.0% | 2.3% / 5.2% | 33.0% / 32.9% | 5.9 / 5.9 | 58.7% / 53.2% | 0.2% / 7.5% | -9.4% / -11.4% |
| breakeven | 229 / 184 | 0.89 / 0.94 | 37.6% / 37.0% | 5.6% / 6.3% | -3.4% / -3.0% | -0.01% / +0.47% | 0.99 / 1.25 | -36.0% / -27.9% | 48.5% / 48.9% | 5.7% / 7.1% | 16.2% / 18.5% | 2.2% / 4.9% | 27.5% / 20.7% | 5.3 / 4.9 | 56.1% / 50.1% | -1.0% / 6.8% | -10.5% / -12.2% |
| time15 | 200 / 157 | 0.78 / 0.80 | 45.0% / 47.1% | 6.3% / 6.4% | -4.9% / -4.6% | +0.11% / +0.61% | 1.04 / 1.25 | -35.4% / -22.9% | 46.0% / 40.8% | 4.0% / 3.2% | 25.0% / 25.5% | 2.5% / 6.4% | 22.5% / 24.2% | 7.4 / 7.2 | 63.1% / 58.7% | 0.6% / 7.6% | -9.0% / -11.4% |
| time5 | 255 / 197 | 0.99 / 1.01 | 46.7% / 47.7% | 4.5% / 5.1% | -4.1% / -3.8% | -0.08% / +0.44% | 0.96 / 1.22 | -29.8% / -28.1% | 32.5% / 28.4% | 2.4% / 2.5% | 12.2% / 15.7% | 2.4% / 4.6% | 50.6% / 48.7% | 3.8 / 3.7 | 47.5% / 45.9% | -2.1% / 6.7% | -11.7% / -12.3% |
| trail | 221 / 179 | 0.86 / 0.92 | 43.9% / 43.0% | 4.9% / 5.0% | -3.8% / -3.6% | +0.02% / +0.11% | 1.01 / 1.05 | -32.2% / -26.9% | 57.5% / 64.2% | 9.0% / 10.6% | 0.0% / 0.0% | 0.0% / 0.0% | 33.5% / 25.1% | 5.9 / 5.3 | 58.4% / 49.9% | -0.5% / 0.9% | -10.1% / -18.1% |
| random (base exit) | 219.5 / 179.7 | - | 50.5% / 50.1% | - | - | +0.25% / +0.33% | 1.14 / 1.17 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base +0.25% / +0.33% (-0.19% to +0.83%); trail +0.25% / +0.33% (-0.22% to +0.85%); breakeven +0.28% / +0.27% (-0.28% to +0.79%); atr +0.30% / +0.29% (-0.41% to +0.96%); time5 +0.15% / +0.18% (-0.26% to +0.66%); time15 +0.37% / +0.36% (-0.38% to +0.98%)

### shadow USD, non-earnings +4%/3x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 369 / 301 | 1.44 / 1.54 | 48.2% / 53.5% | 9.5% / 8.0% | -5.9% / -6.2% | +1.52% / +1.39% | 1.50 / 1.48 | -43.1% / -18.6% | 24.1% / 23.3% | 4.9% / 5.3% | 12.5% / 16.3% | 3.3% / 4.0% | 55.3% / 51.2% | 7.8 / 7.7 | 95.2% / 95.4% | 25.5% / 36.4% | 15.9% / 17.4% |
| base | 457 / 375 | 1.78 / 1.92 | 43.8% / 41.3% | 6.3% / 6.1% | -4.7% / -4.8% | +0.11% / -0.29% | 1.04 / 0.90 | -29.6% / -59.3% | 39.8% / 43.5% | 5.9% / 6.4% | 19.5% / 16.3% | 6.6% / 5.3% | 28.2% / 28.5% | 5.6 / 5.5 | 89.2% / 91.6% | 1.2% / -11.0% | -8.4% / -30.0% |
| breakeven | 482 / 405 | 1.88 / 2.07 | 36.7% / 30.1% | 6.4% / 6.8% | -3.6% / -3.4% | +0.03% / -0.31% | 1.01 / 0.87 | -39.1% / -50.4% | 46.9% / 51.9% | 10.2% / 12.3% | 16.6% / 13.6% | 6.0% / 4.2% | 20.3% / 18.0% | 5.1 / 4.9 | 88.7% / 90.2% | -0.8% / -12.2% | -10.4% / -31.2% |
| time15 | 414 / 327 | 1.61 / 1.67 | 41.3% / 41.0% | 7.0% / 7.0% | -5.0% / -5.0% | -0.04% / -0.11% | 0.99 / 0.96 | -45.7% / -40.3% | 44.9% / 46.2% | 6.8% / 7.0% | 20.5% / 20.5% | 8.0% / 7.0% | 19.8% / 19.3% | 6.6 / 6.7 | 91.7% / 93.9% | -3.3% / -5.3% | -12.9% / -24.3% |
| time5 | 559 / 473 | 2.18 / 2.42 | 46.2% / 42.7% | 4.9% / 5.1% | -4.1% / -4.3% | +0.08% / -0.28% | 1.04 / 0.89 | -35.0% / -56.4% | 30.6% / 35.9% | 4.5% / 4.2% | 14.3% / 11.6% | 3.9% / 3.2% | 46.7% / 45.0% | 3.7 / 3.6 | 81.5% / 84.6% | 1.0% / -13.1% | -8.5% / -32.1% |
| trail | 453 / 383 | 1.77 / 1.96 | 39.1% / 38.1% | 5.6% / 5.6% | -3.8% / -3.9% | -0.12% / -0.31% | 0.95 / 0.87 | -55.9% / -47.1% | 60.3% / 59.3% | 11.9% / 15.9% | 0.0% / 0.0% | 0.0% / 0.0% | 27.8% / 24.8% | 5.6 / 5.2 | 90.3% / 91.2% | -5.5% / -12.0% | -15.0% / -31.0% |
| random (base exit) | 467.4 / 399.2 | - | 49.7% / 48.5% | - | - | +0.28% / +0.22% | 1.14 / 1.11 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base +0.28% / +0.22% (-0.14% to +0.62%); trail +0.16% / +0.22% (-0.14% to +0.58%); breakeven +0.25% / +0.16% (-0.23% to +0.56%); atr +0.44% / +0.34% (-0.23% to +0.80%); time5 +0.10% / +0.07% (-0.19% to +0.34%); time15 +0.32% / +0.33% (-0.15% to +0.78%)

### shadow CAD, earnings +4%/3x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 337 / 264 | 1.31 / 1.35 | 40.9% / 42.0% | 4.3% / 4.9% | -5.8% / -6.2% | -1.70% / -1.51% | 0.51 / 0.58 | -87.5% / -82.4% | 25.2% / 25.8% | 3.6% / 1.9% | 11.0% / 11.4% | 0.6% / 1.9% | 59.6% / 59.1% | 8.0 / 8.2 | 88.1% / 90.6% | -33.2% / -30.8% | -42.8% / -49.8% |
| base | 374 / 303 | 1.46 / 1.55 | 39.8% / 37.3% | 4.2% / 4.3% | -5.6% / -5.4% | -1.71% / -1.79% | 0.49 / 0.47 | -90.9% / -86.5% | 36.4% / 37.0% | 3.2% / 1.7% | 15.5% / 16.2% | 3.7% / 3.0% | 41.2% / 42.2% | 6.7 / 6.6 | 85.7% / 87.2% | -36.1% / -38.3% | -45.6% / -57.3% |
| breakeven | 397 / 328 | 1.55 / 1.68 | 35.0% / 31.7% | 4.3% / 4.4% | -4.8% / -4.6% | -1.60% / -1.78% | 0.49 / 0.44 | -89.6% / -87.4% | 42.3% / 45.1% | 6.5% / 6.7% | 14.1% / 14.0% | 3.0% / 2.7% | 34.0% / 31.4% | 6.2 / 5.8 | 82.9% / 84.3% | -35.5% / -40.1% | -45.1% / -59.1% |
| time15 | 330 / 263 | 1.29 / 1.34 | 37.9% / 38.8% | 4.8% / 4.7% | -6.2% / -6.1% | -2.00% / -1.92% | 0.48 / 0.48 | -91.0% / -84.2% | 43.9% / 44.9% | 5.2% / 2.3% | 21.5% / 20.5% | 3.0% / 3.8% | 26.4% / 28.5% | 8.1 / 8.3 | 89.8% / 92.7% | -36.9% / -36.1% | -46.5% / -55.1% |
| time5 | 517 / 423 | 2.02 / 2.16 | 35.0% / 35.7% | 3.4% / 3.7% | -4.7% / -4.5% | -1.86% / -1.55% | 0.39 / 0.46 | -96.4% / -90.5% | 26.9% / 24.8% | 3.1% / 1.7% | 9.5% / 12.1% | 1.9% / 2.6% | 58.6% / 58.9% | 4.0 / 4.0 | 74.5% / 78.5% | -48.1% / -44.3% | -57.6% / -63.2% |
| trail | 379 / 304 | 1.48 / 1.55 | 33.8% / 31.6% | 3.9% / 4.2% | -4.8% / -4.6% | -1.87% / -1.79% | 0.41 / 0.42 | -91.8% / -85.5% | 55.1% / 53.9% | 7.4% / 6.9% | 0.0% / 0.0% | 0.0% / 0.0% | 37.5% / 39.1% | 6.5 / 6.5 | 83.9% / 85.6% | -38.6% / -38.1% | -48.2% / -57.1% |
| random (base exit) | 379.6 / 319.7 | - | 36.7% / 35.3% | - | - | -1.82% / -1.79% | 0.45 / 0.45 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base -1.82% / -1.79% (-2.21% to -1.36%); trail -1.89% / -1.76% (-2.23% to -1.33%); breakeven -1.84% / -1.79% (-2.21% to -1.36%); atr -1.83% / -1.67% (-2.21% to -1.14%); time5 -1.91% / -1.83% (-2.14% to -1.54%); time15 -1.73% / -1.80% (-2.31% to -1.23%)

### shadow CAD, earnings +6%/5x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 203 / 152 | 0.79 / 0.78 | 41.9% / 36.2% | 5.4% / 6.6% | -6.4% / -6.5% | -1.46% / -1.78% | 0.61 / 0.57 | -66.3% / -71.2% | 27.1% / 23.7% | 2.0% / 4.6% | 11.3% / 11.2% | 0.0% / 2.0% | 59.6% / 58.6% | 8.0 / 8.0 | 67.9% / 61.0% | -18.9% / -22.3% | -28.5% / -41.3% |
| base | 221 / 173 | 0.86 / 0.88 | 39.4% / 39.3% | 4.5% / 5.1% | -5.9% / -5.5% | -1.82% / -1.35% | 0.49 / 0.60 | -75.4% / -59.8% | 41.2% / 37.0% | 3.2% / 2.9% | 20.4% / 22.0% | 2.3% / 5.2% | 33.0% / 32.9% | 5.9 / 5.9 | 58.7% / 53.2% | -24.1% / -18.9% | -33.7% / -37.9% |
| breakeven | 229 / 184 | 0.89 / 0.94 | 32.8% / 31.5% | 4.5% / 5.4% | -5.0% / -4.6% | -1.91% / -1.43% | 0.43 / 0.54 | -78.1% / -62.4% | 48.5% / 48.9% | 5.7% / 7.1% | 16.2% / 18.5% | 2.2% / 4.9% | 27.5% / 20.7% | 5.3 / 4.9 | 56.1% / 50.1% | -25.8% / -20.9% | -35.3% / -39.9% |
| time15 | 200 / 157 | 0.78 / 0.80 | 40.0% / 41.4% | 5.0% / 5.3% | -6.3% / -5.9% | -1.79% / -1.29% | 0.53 / 0.63 | -71.9% / -55.4% | 46.0% / 40.8% | 4.0% / 3.2% | 25.0% / 25.5% | 2.5% / 6.4% | 22.5% / 24.2% | 7.4 / 7.2 | 63.1% / 58.7% | -21.8% / -16.7% | -31.4% / -35.7% |
| time5 | 255 / 197 | 0.99 / 1.01 | 35.3% / 37.6% | 3.7% / 4.3% | -5.1% / -4.9% | -1.98% / -1.46% | 0.40 / 0.53 | -82.5% / -65.6% | 32.5% / 28.4% | 2.4% / 2.5% | 12.2% / 15.7% | 2.4% / 4.6% | 50.6% / 48.7% | 3.8 / 3.7 | 47.5% / 45.9% | -29.0% / -22.6% | -38.6% / -41.6% |
| trail | 221 / 179 | 0.86 / 0.92 | 31.7% / 29.6% | 4.6% / 4.9% | -4.9% / -4.6% | -1.88% / -1.79% | 0.44 / 0.45 | -76.4% / -69.2% | 57.5% / 64.2% | 9.0% / 10.6% | 0.0% / 0.0% | 0.0% / 0.0% | 33.5% / 25.1% | 5.9 / 5.3 | 58.4% / 49.9% | -24.7% / -24.8% | -34.3% / -43.8% |
| random (base exit) | 219.6 / 179.8 | - | 36.9% / 37.7% | - | - | -1.67% / -1.58% | 0.46 / 0.49 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base -1.67% / -1.58% (-2.14% to -0.93%); trail -1.66% / -1.59% (-2.13% to -0.99%); breakeven -1.59% / -1.60% (-2.12% to -1.14%); atr -1.63% / -1.56% (-2.23% to -0.79%); time5 -1.75% / -1.72% (-2.12% to -1.32%); time15 -1.54% / -1.54% (-2.16% to -0.92%)

### shadow CAD, non-earnings +4%/3x

| Exit | Trades IS / OOS | Per week IS / OOS | Win IS / OOS | Avg win IS / OOS | Avg loss IS / OOS | Net exp. IS / OOS | PF IS / OOS | Max DD IS / OOS | Stop IS / OOS | Gap stop IS / OOS | Target IS / OOS | Gap tgt IS / OOS | Time IS / OOS | Hold IS / OOS | Invested IS / OOS | CAGR IS / OOS | vs XIC IS / OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr | 369 / 301 | 1.44 / 1.54 | 37.1% / 42.9% | 10.2% / 7.8% | -6.6% / -6.8% | -0.38% / -0.51% | 0.91 / 0.87 | -74.6% / -55.4% | 24.1% / 23.3% | 4.9% / 5.3% | 12.5% / 16.3% | 3.3% / 4.0% | 55.3% / 51.2% | 7.8 / 7.7 | 95.2% / 95.4% | -20.8% / -16.5% | -30.4% / -35.5% |
| base | 457 / 375 | 1.78 / 1.92 | 36.1% / 33.3% | 5.5% / 5.5% | -5.9% / -6.0% | -1.79% / -2.19% | 0.53 / 0.46 | -94.6% / -94.6% | 39.8% / 43.5% | 5.9% / 6.4% | 19.5% / 16.3% | 6.6% / 5.3% | 28.2% / 28.5% | 5.6 / 5.5 | 89.2% / 91.6% | -43.1% / -52.1% | -52.7% / -71.1% |
| breakeven | 482 / 405 | 1.88 / 2.07 | 30.3% / 24.9% | 5.6% / 6.2% | -5.1% / -5.0% | -1.87% / -2.21% | 0.48 / 0.41 | -95.8% / -95.7% | 46.9% / 51.9% | 10.2% / 12.3% | 16.6% / 13.6% | 6.0% / 4.2% | 20.3% / 18.0% | 5.1 / 4.9 | 88.7% / 90.2% | -45.9% / -55.0% | -55.5% / -74.0% |
| time15 | 414 / 327 | 1.61 / 1.67 | 37.2% / 33.6% | 5.7% / 6.3% | -6.5% / -6.2% | -1.94% / -2.01% | 0.52 / 0.52 | -94.5% / -90.6% | 44.9% / 46.2% | 6.8% / 7.0% | 20.5% / 20.5% | 8.0% / 7.0% | 19.8% / 19.3% | 6.6 / 6.7 | 91.7% / 93.9% | -42.7% / -44.8% | -52.3% / -63.8% |
| time5 | 559 / 473 | 2.18 / 2.42 | 33.1% / 33.0% | 4.6% / 4.5% | -5.0% / -5.5% | -1.82% / -2.18% | 0.45 / 0.40 | -97.1% / -97.3% | 30.6% / 35.9% | 4.5% / 4.2% | 14.3% / 11.6% | 3.9% / 3.2% | 46.7% / 45.0% | 3.7 / 3.6 | 81.5% / 84.6% | -50.0% / -60.1% | -59.6% / -79.1% |
| trail | 453 / 383 | 1.77 / 1.96 | 30.2% / 26.6% | 5.1% / 5.7% | -5.1% / -5.1% | -2.02% / -2.21% | 0.44 / 0.41 | -96.1% / -95.0% | 60.3% / 59.3% | 11.9% / 15.9% | 0.0% / 0.0% | 0.0% / 0.0% | 27.8% / 24.8% | 5.6 / 5.2 | 90.3% / 91.2% | -46.6% / -53.3% | -56.2% / -72.3% |
| random (base exit) | 467.2 / 399.3 | - | 38.2% / 36.4% | - | - | -1.63% / -1.70% | 0.49 / 0.47 | - | - | - | - | - | - | - | - | - | - |
| SPY buy and hold | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 9.6% / 19.0% | - |

Random baseline per exit, net expectancy IS / OOS (mean of 200 runs; 5th-95th percentile OOS): base -1.63% / -1.70% (-2.10% to -1.28%); trail -1.73% / -1.67% (-2.05% to -1.19%); breakeven -1.66% / -1.69% (-2.05% to -1.35%); atr -1.47% / -1.55% (-2.08% to -1.00%); time5 -1.78% / -1.83% (-2.10% to -1.54%); time15 -1.56% / -1.57% (-1.99% to -1.12%)

## By year (shadow book, base exit)

### shadow USD

| Year | Setup | Trades | Win | Net exp. | Random exp. | Book return | SPY return |
|---|---|---|---|---|---|---|---|
| 2017 | earnings +4%/3x | 4 | 50.0% | -0.88% | -0.39% | -1.2% | 21.7% |
| 2018 | earnings +4%/3x | 75 | 49.3% | +0.01% | -0.59% | -2.6% | -4.6% |
| 2019 | earnings +4%/3x | 79 | 54.4% | +0.47% | +0.61% | 13.7% | 31.2% |
| 2020 | earnings +4%/3x | 71 | 32.4% | -1.53% | +0.21% | -32.6% | 18.3% |
| 2021 | earnings +4%/3x | 70 | 54.3% | +0.80% | +0.53% | 19.7% | 28.7% |
| 2022 | earnings +4%/3x | 75 | 52.0% | +1.16% | -0.39% | 27.7% | -18.2% |
| 2023 | earnings +4%/3x | 75 | 49.3% | +0.28% | +0.31% | 9.3% | 26.2% |
| 2024 | earnings +4%/3x | 81 | 44.4% | +0.17% | +0.35% | 1.2% | 24.9% |
| 2025 | earnings +4%/3x | 77 | 50.6% | +0.65% | +0.21% | 15.0% | 17.7% |
| 2026 | earnings +4%/3x | 70 | 35.7% | -0.75% | -0.31% | -15.7% | 6.2% |
| 2017 | earnings +6%/5x | 5 | 60.0% | +0.42% | +0.13% | 0.6% | 21.7% |
| 2018 | earnings +6%/5x | 50 | 50.0% | +0.41% | +0.07% | 5.9% | -4.6% |
| 2019 | earnings +6%/5x | 62 | 41.9% | -0.13% | +0.70% | -4.2% | 31.2% |
| 2020 | earnings +6%/5x | 35 | 31.4% | -2.13% | +0.33% | -22.3% | 18.3% |
| 2021 | earnings +6%/5x | 40 | 55.0% | +1.64% | +0.18% | 23.3% | 28.7% |
| 2022 | earnings +6%/5x | 29 | 44.8% | +0.43% | -0.29% | 3.4% | -18.2% |
| 2023 | earnings +6%/5x | 52 | 59.6% | +1.45% | +0.34% | 27.2% | 26.2% |
| 2024 | earnings +6%/5x | 51 | 41.2% | +0.23% | +0.71% | 2.8% | 24.9% |
| 2025 | earnings +6%/5x | 47 | 40.4% | +0.16% | +0.25% | 1.7% | 17.7% |
| 2026 | earnings +6%/5x | 23 | 43.5% | +0.04% | -0.45% | -0.2% | 6.2% |
| 2017 | non-earnings +4%/3x | 7 | 100.0% | +2.86% | +0.72% | 4.4% | 21.7% |
| 2018 | non-earnings +4%/3x | 75 | 38.7% | +0.07% | -0.38% | 2.6% | -4.6% |
| 2019 | non-earnings +4%/3x | 69 | 55.1% | +1.32% | +0.63% | 33.3% | 31.2% |
| 2020 | non-earnings +4%/3x | 112 | 41.1% | -0.22% | +0.16% | -9.9% | 18.3% |
| 2021 | non-earnings +4%/3x | 98 | 42.9% | -0.01% | +0.60% | -4.5% | 28.7% |
| 2022 | non-earnings +4%/3x | 96 | 39.6% | -0.41% | +0.26% | -13.3% | -18.2% |
| 2023 | non-earnings +4%/3x | 83 | 49.4% | +0.76% | +0.41% | 16.0% | 26.2% |
| 2024 | non-earnings +4%/3x | 100 | 39.0% | -1.16% | -0.09% | -32.2% | 24.9% |
| 2025 | non-earnings +4%/3x | 109 | 35.8% | -0.65% | +0.28% | -25.3% | 17.7% |
| 2026 | non-earnings +4%/3x | 83 | 43.4% | +0.20% | +0.33% | 7.9% | 6.2% |

### shadow CAD

| Year | Setup | Trades | Win | Net exp. | Random exp. | Book return | SPY return |
|---|---|---|---|---|---|---|---|
| 2017 | earnings +4%/3x | 4 | 25.0% | -2.78% | -2.01% | -3.7% | 21.7% |
| 2018 | earnings +4%/3x | 75 | 38.7% | -1.89% | -2.42% | -39.7% | -4.6% |
| 2019 | earnings +4%/3x | 79 | 40.5% | -1.43% | -1.27% | -31.0% | 31.2% |
| 2020 | earnings +4%/3x | 71 | 28.2% | -3.43% | -1.63% | -58.2% | 18.3% |
| 2021 | earnings +4%/3x | 70 | 45.7% | -1.10% | -1.37% | -22.8% | 28.7% |
| 2022 | earnings +4%/3x | 75 | 46.7% | -0.74% | -2.38% | -20.6% | -18.2% |
| 2023 | earnings +4%/3x | 75 | 37.3% | -1.62% | -1.66% | -31.9% | 26.2% |
| 2024 | earnings +4%/3x | 81 | 35.8% | -1.73% | -1.63% | -39.9% | 24.9% |
| 2025 | earnings +4%/3x | 77 | 44.2% | -1.25% | -1.72% | -30.1% | 17.7% |
| 2026 | earnings +4%/3x | 70 | 31.4% | -2.65% | -2.16% | -46.9% | 6.2% |
| 2017 | earnings +6%/5x | 5 | 40.0% | -1.48% | -2.02% | -2.5% | 21.7% |
| 2018 | earnings +6%/5x | 50 | 38.0% | -1.49% | -1.81% | -22.9% | -4.6% |
| 2019 | earnings +6%/5x | 62 | 37.1% | -2.03% | -1.20% | -35.3% | 31.2% |
| 2020 | earnings +6%/5x | 35 | 22.9% | -4.03% | -1.54% | -38.6% | 18.3% |
| 2021 | earnings +6%/5x | 40 | 55.0% | -0.26% | -1.79% | -4.4% | 28.7% |
| 2022 | earnings +6%/5x | 29 | 44.8% | -1.47% | -2.26% | -14.0% | -18.2% |
| 2023 | earnings +6%/5x | 52 | 44.2% | -0.45% | -1.53% | -8.5% | 26.2% |
| 2024 | earnings +6%/5x | 51 | 37.3% | -1.67% | -1.26% | -25.8% | 24.9% |
| 2025 | earnings +6%/5x | 47 | 36.2% | -1.74% | -1.60% | -24.6% | 17.7% |
| 2026 | earnings +6%/5x | 23 | 39.1% | -1.86% | -2.37% | -13.8% | 6.2% |
| 2017 | non-earnings +4%/3x | 7 | 57.1% | +0.96% | -1.34% | 1.9% | 21.7% |
| 2018 | non-earnings +4%/3x | 75 | 33.3% | -1.83% | -2.25% | -37.7% | -4.6% |
| 2019 | non-earnings +4%/3x | 69 | 43.5% | -0.58% | -1.39% | -13.8% | 31.2% |
| 2020 | non-earnings +4%/3x | 112 | 32.1% | -2.12% | -1.76% | -55.9% | 18.3% |
| 2021 | non-earnings +4%/3x | 98 | 36.7% | -1.91% | -1.29% | -48.5% | 28.7% |
| 2022 | non-earnings +4%/3x | 96 | 35.4% | -2.31% | -1.62% | -54.3% | -18.2% |
| 2023 | non-earnings +4%/3x | 83 | 36.1% | -1.14% | -1.52% | -31.2% | 26.2% |
| 2024 | non-earnings +4%/3x | 100 | 30.0% | -3.06% | -1.99% | -64.7% | 24.9% |
| 2025 | non-earnings +4%/3x | 109 | 32.1% | -2.55% | -1.65% | -62.8% | 17.7% |
| 2026 | non-earnings +4%/3x | 83 | 36.1% | -1.70% | -1.59% | -37.3% | 6.2% |

## Flagged bars inside trades

A flagged bar inside an open trade is skipped and its checks move to the next clean bar. Counts over every configuration:

| Book | Trades | Trades with a skipped bar | Bars skipped |
|---|---|---|---|
| shadow CAD | 11,588 | 1 | 1 |
| shadow USD | 11,588 | 1 | 1 |

## SPY over each trade's own window (secondary benchmark)

Average of (trade net return - SPY total return from the signal close to the exit date), all configurations pooled:

| Book | IS | OOS |
|---|---|---|
| shadow USD | +0.03% | -0.35% |
| shadow CAD | -1.87% | -2.25% |

## Choices and caveats

- Survivorship (above): today's index members only.
- Same rules as docs/rules.md: limit close(t-1) x 1.005 for day t, stop-only fill day, gap/stop-first/target/time-stop order, all six exits. Shadow book: 3 slots, equal weight, no cash limit, names ranked by 20-day value traded.
- Earnings reaction session: release before the open = that session; after the close = the next; no time or intraday = either. Yahoo's calendar times are not always right.
- Costs are round-trip and per trade; the 2.0% case assumes about 1% currency conversion each way, nothing else (no withholding tax on US dividends, which would lower it further).
- The random baseline and the all-candidates average use a 15% uniform sample of eligible name-days (see Data); a uniform sample of a day's universe is still a uniform draw.
- 95% intervals assume independent trades; events cluster in earnings season, so the true intervals are wider.
