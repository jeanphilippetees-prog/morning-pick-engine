# Systematic strategy study v1

Generated 2026-11-25T00:42:43Z. Strategies: docs/strategies.md. Signals at month-ends 2017-11-30 to 2026-09-30; trades at the next session's open. In-sample = months starting 2017-2022, out-of-sample = months starting 2023-today. **Nothing was tuned**; the primary configuration and every sensitivity were fixed before the run.

**Survivorship:** Yahoo only has names listed today; delisted and acquired names are missing, so every stock-picking number here is an upper bound (as in backtest_v1). XIC and XBB are not affected. **Cash earns 0%**, which understates the filtered strategies a little.

## Summary

**Primary D: FAIL.** Bar (out-of-sample, fixed in advance): net CAGR above the random 95th percentile AND (CAGR above XIC OR Sharpe above XIC with max drawdown no worse). It must also hold in-sample. Out-of-sample: fail; in-sample: fail.

|  | CAGR | Sharpe | Max drawdown | Random CAGR 95th pct |
|---|---|---|---|---|
| Primary D, OOS | 2.2% | 0.21 | -49.3% | 20.2% |
| XIC, OOS | 20.3% | 1.80 | -12.3% | - |
| Primary D, IS | -2.5% | 0.04 | -48.4% | 4.9% |
| XIC, IS | 6.8% | 0.48 | -37.2% | - |

## All strategies

Each cell is in-sample / out-of-sample. Turnover = one-way traded value per year as a share of the book; trades = names bought or sold per year. vs XIC = CAGR difference. Random = mean CAGR of 200 random-ranking runs (5th to 95th percentile). Bar = the pass bar in each period.

| Strategy | CAGR | Sharpe | Max DD | Worst month | Invested | Turnover | Trades/yr | vs XIC | Random CAGR | Bar |
|---|---|---|---|---|---|---|---|---|---|---|
| A XIC buy and hold | 6.8% / 20.3% | 0.48 / 1.80 | -37.2% / -12.3% | -19.7% / -5.1% | 100.0% / 100.0% | 0.10 / 0.00 | 0 / 0 | +0.0% / +0.0% | - | - |
| B XIC + trend filter | 1.4% / 15.8% | 0.21 / 1.56 | -12.7% / -12.3% | -6.7% / -5.1% | 67.2% / 91.3% | 1.08 / 0.78 | 2 / 2 | -5.4% / -4.5% | - | - |
| C momentum top 10 | 15.6% / 4.7% | 0.54 / 0.30 | -47.4% / -49.3% | -20.3% / -21.5% | 100.0% / 100.0% | 2.69 / 3.06 | 44 / 53 | +8.8% / -15.7% | 4.0% (-3.9% to 12.0%) / 15.2% (5.4% to 24.9%) | pass / fail |
| D primary | -2.5% / 2.2% | 0.04 / 0.21 | -48.4% / -49.3% | -20.3% / -21.5% | 67.2% / 91.3% | 2.78 / 3.34 | 50 / 59 | -9.3% / -18.2% | -0.3% (-5.7% to 4.9%) / 11.3% (1.9% to 20.2%) | fail / fail |
| D top 5 | -1.8% / -1.0% | 0.12 / 0.12 | -54.1% / -60.5% | -26.9% / -21.9% | 67.2% / 91.3% | 2.91 / 3.98 | 26 / 37 | -8.6% / -21.4% | -1.2% (-10.1% to 7.0%) / 11.9% (1.0% to 25.0%) | fail / fail |
| D top 20 | -0.6% / 13.7% | 0.06 / 0.64 | -35.2% / -35.2% | -17.5% / -18.5% | 67.2% / 91.3% | 2.50 / 2.89 | 90 / 102 | -7.4% / -6.6% | -0.3% (-4.3% to 3.4%) / 12.2% (6.9% to 18.7%) | fail / fail |
| D no buffer | 3.7% / 6.8% | 0.26 / 0.37 | -46.8% / -44.2% | -21.6% / -21.5% | 67.2% / 91.3% | 3.73 / 4.74 | 70 / 89 | -3.1% / -13.6% | -0.9% (-7.7% to 4.8%) / 11.3% (3.5% to 21.2%) | fail / fail |
| D 6-1 lookback | -3.4% / -0.7% | -0.02 / 0.12 | -44.4% / -48.0% | -16.5% / -16.2% | 67.2% / 91.3% | 3.81 / 4.75 | 72 / 89 | -10.2% / -21.1% | -1.0% (-6.4% to 4.3%) / 12.1% (4.2% to 21.4%) | fail / fail |
| D XBB off-asset | -0.6% / 3.7% | 0.11 / 0.27 | -48.4% / -49.3% | -20.3% / -21.5% | 100.0% / 100.0% | 3.76 / 4.12 | 52 / 61 | -7.4% / -16.6% | 1.0% (-4.3% to 7.3%) / 12.8% (3.0% to 22.2%) | fail / fail |
| B XBB off-asset | 3.3% / 17.6% | 0.40 / 1.70 | -20.1% / -12.3% | -6.7% / -5.1% | 100.0% / 100.0% | 2.07 / 1.57 | 4 / 3 | -3.5% / -2.7% | - | - |

## Yearly returns

Calendar years by trade date (the first and last years are partial).

| Year | A XIC buy and hold | B XIC + trend filter | C momentum top 10 | D primary | D top 5 | D top 20 | D no buffer | D 6-1 lookback | D XBB off-asset | B XBB off-asset |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 1.1% | 1.1% | -2.3% | -2.3% | -5.4% | 1.4% | -2.3% | 6.5% | -2.3% | 1.1% |
| 2018 | -9.7% | -9.4% | -13.5% | -4.5% | 8.8% | -14.1% | -7.1% | -13.1% | -1.6% | -6.6% |
| 2019 | 24.5% | 9.3% | 16.5% | -10.3% | -21.3% | -6.5% | -0.8% | -4.1% | -9.3% | 10.5% |
| 2020 | 6.2% | -6.4% | 56.3% | -5.1% | 16.9% | -1.3% | 2.8% | -4.8% | -0.1% | -1.5% |
| 2021 | 23.8% | 23.8% | 19.2% | 5.9% | -4.5% | 16.4% | 23.9% | 1.9% | 5.9% | 23.8% |
| 2022 | -6.5% | -7.5% | 14.1% | 4.7% | 0.6% | 3.6% | 5.1% | -2.6% | 5.0% | -7.3% |
| 2023 | 10.7% | -4.4% | -8.8% | -18.8% | -19.9% | -11.1% | -19.5% | -11.6% | -13.8% | 1.5% |
| 2024 | 22.6% | 22.6% | 8.6% | 11.1% | 30.5% | -0.1% | 14.7% | 18.9% | 11.1% | 22.6% |
| 2025 | 31.5% | 31.5% | 84.5% | 84.5% | 81.0% | 96.7% | 92.0% | 33.6% | 84.5% | 31.5% |
| 2026 | 14.0% | 14.0% | -34.8% | -34.8% | -49.2% | -6.4% | -27.5% | -30.7% | -34.8% | 14.0% |

## Realism check: $1,000, whole shares

Whole shares at the actual open; a name whose one share costs more than its slot is not bought and the slot stays in cash; dividends paid in cash; same 0.15% per side. Gap = whole-share CAGR minus the weight-based CAGR. Cash drag = average share of the book in idle cash at month-ends (whole run).

| Run | Period | Weight-based CAGR | $1,000 CAGR | Gap | Cash drag | Names missed |
|---|---|---|---|---|---|---|
| D primary at $1,000 | IS | -2.5% | 4.5% | +7.0% | 38.4% | 77 |
| D primary at $1,000 | OOS | 2.2% | 3.0% | +0.9% |  |  |
| D top 5 at $1,000 | IS | -1.8% | -0.3% | +1.5% | 33.7% | 20 |
| D top 5 at $1,000 | OOS | -1.0% | -2.5% | -1.4% |  |  |

### Historical replay: months from $1,000 to $10,000

**Historical replay, not a forecast:** each strategy's actual monthly returns applied in order from the first signal, with the contribution added at each month-end.

| Strategy | $0 a month | $250 a month | $500 a month |
|---|---|---|---|
| A XIC buy and hold | not reached in 107 (ends $2,840) | 33 | 17 |
| D primary | not reached in 107 (ends $956) | 38 | 23 |

## Data notes

- Universe: point-in-time regular book (phase 1 v2 eligibility, v2 blocking flags); 159 eligible names at an average month-end.
- XBB.TO: 2509 sessions from 2016-11-24; flags: none; usable.
- Momentum uses dividend-adjusted closes; trades use the adjusted open (open x adj_close / close). The trend filter uses XIC's split-adjusted close.
- Max drawdown uses daily marks for the strategies; random runs use monthly returns (only their CAGR enters the bar).
- A held name with no open on a trade date (halt) is valued at its last adjusted close.
