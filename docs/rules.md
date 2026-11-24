# Rules to simulate (Morning Pick playbook v2.4)

## Entry
- Signal is known before the open of day t, using data up to the close of day t-1.
- Buy limit = close(t-1) x 1.005, good for day t only.
- Fill: open(t) <= limit -> fill at open(t); else low(t) <= limit -> fill at limit; else Missed.
- Main account: up to 3 positions, each sized min(cash, equity / 3), whole shares, cost 0.30% round trip.
- Shadow: up to 3 positions, equal weight, no cash limit. Small-cap: same, cost 1% round trip.
- Skip a ticker already open or pending in the same book.

## Base exit
- Stop = fill x 0.95. Target = fill x 1.08.
- Fill day (session 1): only the stop counts; low <= stop -> exit at stop.
- Each later session, in order:
  1. open <= stop -> exit at open (Gap stop)
  2. open >= target -> exit at open (Gap target)
  3. low <= stop -> exit at stop (Stop), even if high >= target the same day
  4. high >= target -> exit at target (Target)
  5. session 10 -> exit at close (Time stop)
- Net return = exit / fill - 1 - cost.

## Exit variants (same entry, same 10-session limit, same cost)
- Trail: no target. Stop = max(fill x 0.95, highest high through the prior session x 0.94). Gap and stop-first rules as base.
- Breakeven: base, but once any session's high >= fill x 1.04, from the next session the stop = fill.
- ATR: stop = fill - 2 x ATR14, target = fill + 3 x ATR14 (ATR14 as of the close before the signal).
- News-exit: not backtestable without historical news; skip in the backtester.
- Also test time stops of 5 and 15 sessions with base stops and targets.

## Benchmark
- XIC.TO buy and hold over the same period (primary), and XIC's return over each trade's own window (secondary).

## Metrics per book and variant
- Trades, trades per week, win rate, average win, average loss, net expectancy, profit factor, max drawdown, % exits by reason, average holding days, % of days invested, CAGR vs XIC.
- Every metric reported for in-sample 2016-2022 and out-of-sample 2023-today, side by side.
