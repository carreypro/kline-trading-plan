# Analysis framework

Use this reference for market analysis and score construction.

## Timeframe map

| Holding horizon | Execution | Context | Regime |
|---|---|---|---|
| Intraday, under 1 day | 5m or 15m | 1H | 4H |
| Swing, 1-7 days | 1H | 4H | 1D |
| Position, over 7 days | 4H | 1D | 1W |

Use closed candles for indicator decisions. A still-forming candle may be
reported separately but must not silently replace the last closed candle.

## Evidence order

1. Market structure: higher highs/lows, lower highs/lows, range, breakout, or
   failed breakout.
2. Trend: price relative to relevant moving averages and their slope.
3. Momentum: RSI/MACD or another independent momentum measure.
4. Volatility: ATR and volatility expansion/contraction.
5. Participation: volume relative to its recent baseline.
6. Derivatives: funding, OI change, basis, liquidations, and order-book state.
7. Macro/regime: broad risk context and market-cycle evidence.

Structure leads; indicators confirm or weaken the thesis. A candlestick pattern
without location, trend, and volume context is not a standalone setup.

## Normalized signal scores

Use a -100 to +100 scale:

| Score | Meaning |
|---:|---|
| +75 to +100 | exceptional bullish evidence |
| +40 to +74 | strong bullish evidence |
| +15 to +39 | mild bullish evidence |
| -14 to +14 | neutral or ambiguous |
| -39 to -15 | mild bearish evidence |
| -74 to -40 | strong bearish evidence |
| -100 to -75 | exceptional bearish evidence |

Scores express evidence direction, not win probability. Weight signals by
decision relevance and data quality. Keep correlated signals in one group or
reduce their weights.

Example input for `scripts/signal_score.py`:

```json
{
  "pillars": {
    "price_volume": {
      "signals": [
        {"name": "4H structure", "score": 55, "weight": 3, "value": "higher low"},
        {"name": "1H volume", "score": 20, "weight": 1, "value": "1.2x baseline"}
      ]
    },
    "derivatives": {
      "signals": [
        {"name": "funding", "score": -10, "weight": 1, "value": "slightly positive"},
        {"name": "open interest", "available": false, "weight": 2}
      ]
    },
    "macro": {"signals": []}
  }
}
```

The script excludes unavailable readings from the score and retains them in
coverage. Confidence is driven by coverage, freshness, agreement across
timeframes, and the distance between current price and the proposed trigger.

## Conflict rules

- Higher-timeframe structure overrides lower-timeframe momentum for directional
  bias; lower-timeframe evidence times the entry.
- Rising price plus falling OI can be a short-covering move, not fresh demand.
- Rising price plus extreme positive funding increases crowded-long risk.
- A breakout without volume or a close beyond the level remains unconfirmed.
- If spread or slippage consumes a material share of the stop distance, the
  plan is no-trade until liquidity improves.

## Freshness and provenance

Include the instrument, exchange, interval, last candle close time, and query
time. Mark a field stale when it is older than the decision timeframe or when
its source does not state an update time. Never merge readings from different
instruments as though they were one market.
