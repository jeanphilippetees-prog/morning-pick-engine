# Factor definitions

_Copied from SPEC.md, section "Factor definitions". SPEC.md is the source; keep both in sync._

The live rubric uses judgment; the engine needs fixed formulas. These are starting definitions to test, not new rules: if one proves useless, the playbook's wording changes only through the normal proposal process.

| Factor | Point | Condition, using data to the close of t-1 |
| --- | --- | --- |
| Momentum | Trend (1) | close > SMA20 and SMA20 > SMA50 |
| Momentum | Thrust (1) | day return >= +2% on volume >= 1.5x its 20-day average |
| Setup | Room (1) | close <= 0.95 x the 52-week high, or a close at a new 52-week high (breakout) |
| Setup | Fits the stop (1) | ATR14 / close <= 4%, and close <= 1.10 x SMA20 (not stretched) |
| Market filter | Yes / No | XIC close > its SMA50 |
| Liquidity | Gate | 20-day average value traded >= $5M (small-cap >= $1M); price >= $5 (small-cap $1 to < $5) |

**Price score** = Momentum + Setup, 0-4. Backtest entries at thresholds 2, 3 and 4, each with and without the market filter. When more names qualify than free slots, rank by price score, then by 20-day value traded.

**Baseline that every result must beat:** random entries from the same universe on the same days, same count, same exits, 200 runs. A rule that can't beat random entries after costs has no edge, whatever its win rate.

News and Social can't be computed from prices; they stay in the live trial. Insider points wait for phase 5.
