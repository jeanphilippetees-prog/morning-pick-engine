# Systematic strategies to simulate (study v1)

Research only. These are slower, price-only strategies tested next to the daily playbook; they do not change
docs/rules.md, the playbook backtest or anything the live trial uses. Written before any code or result
(PM brief "systematic strategy study", run as branch phase-2d-systematic because phase-2b was already used).

## Shared settings

- **Universe:** the point-in-time regular book from phase 1 v2: at the signal close, close >= $5, 20-day
  average value traded >= $5M, at most 4 zero-volume days in the last 20, volume on the signal day, and a
  60-session lookback free of blocking flags (v2: bad prints and unconfirmed level shifts). No small-caps.
- **Calendar:** the signal is computed at the close of the last XIC session of each month (month-end). Trades
  happen at the open of the next session. Signals use only data up to that close.
- **Prices:** ranks and returns use dividend-and-split-adjusted prices. A trade at the open uses the adjusted
  open = open x (adj_close / close) of that day. The trend filter uses XIC's split-adjusted month-end close.
- **Costs:** 0.15% of traded value per side (0.30% round trip). Unchanged positions cost nothing; resizing an
  existing position to equal weight costs 0.15% of the value traded.
- **Cash** earns 0% (conservative). Sensitivity: XBB (iShares Core Canadian Universe Bond) as the off-asset
  instead of cash, if its data is clean.
- **Periods:** in-sample = months starting 2017-2022, out-of-sample = months starting 2023-today. Momentum needs
  12 months of history, so the first signal is the first month-end with it.
- **Measurement:** holdings are marked every session (adjusted closes) for drawdown, Sharpe uses monthly
  returns (open of the first session after a month-end to the next), annualized x sqrt(12), 0% risk-free.

## Strategies

- **A. XIC buy and hold** (benchmark): bought at the first trade date, held, dividends reinvested (adj prices).
- **B. XIC + trend filter:** at each month-end, hold XIC for the next month if XIC's month-end close is above
  the average of its last 10 month-end closes (this one included); otherwise cash. Checked monthly only.
- **C. Momentum:** rank eligible names by the 12-1 return: adj close at the month-end 1 month ago / adj close
  at the month-end 12 months ago - 1 (the latest month is skipped). Hold the top 10, equal weight. Buffer: a
  name already held stays while it ranks in the top 20. Fill the remaining slots with the best-ranked names
  not held. Rebalance monthly to equal weight.
- **D. C + B's filter:** when the filter is off, the whole book goes to cash (or XBB in the sensitivity).

**Primary configuration = D exactly as written.**

Pre-registered sensitivity runs (all reported, none chosen): top 5 (buffer top 10) and top 20 (buffer top 40),
buffer = twice the hold count; no buffer; 6-1 lookback (adj close 1 month ago / 6 months ago - 1); XBB instead
of cash.

## Baselines and the pass bar

- **Random baseline for C and D:** each month the eligible names are shuffled into a random ranking and the
  identical selection runs (same count, same buffer rule, same filter, same costs). 200 runs; mean and
  5th-95th percentiles. Random runs are measured on monthly returns (only their CAGR enters the bar).
- **Pass bar (out-of-sample), fixed before any result:** net CAGR above the random 95th percentile AND
  (CAGR above XIC's OR Sharpe above XIC's with a max drawdown no worse than XIC's). In-sample is reported next
  to it; a pass in only one period is not a pass.

## Realism check at Phil's size

- Primary D and top-5 D with a $1,000 start, whole shares at the actual open price, leftover cash idle; a name
  whose one share costs more than its equal-weight slot is not bought (its slot stays in cash). Dividends are
  paid in cash. Reported next to the weight-based version: CAGR gap, average cash drag, names missed.
- Historical replay (not a forecast): months to grow $1,000 to $10,000 with $0 / $250 / $500 added each month,
  applying A's and D's historical monthly returns in order.
