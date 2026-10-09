---
name: kline-trading-plan
description: >-
  Analyze live crypto K-line, price-volume, market-structure, and derivatives
  evidence, then turn it into a conditional trading plan with exact entry,
  invalidation, targets, position sizing, leverage, and three risk tiers. Use
  when a user wants both market analysis and an actionable risk-managed plan,
  asks whether or how to trade a coin, or requests entry/stop/target/size
  levels. Do not use for placing orders, managing an existing account, or
  guaranteeing returns.
---

# K-Line Trading Plan

Combine technical evidence and risk construction in one auditable workflow.
This skill is read-only: never place, cancel, or amend an order unless the user
separately invokes an execution skill and explicitly authorizes the action.

## Choose the deliverable

- **Analysis only**: explain trend, structure, momentum, volatility, volume,
  derivatives, and invalidation. Do not invent account-specific sizing.
- **Plan**: add conditional entry, stop, targets, R:R, and scenario branches.
- **Sized plan**: also calculate units, notional, margin, and account risk. This
  requires account equity, maximum account risk, maximum margin allocation, and
  maximum leverage.

If the user requests a sized plan but omits risk inputs, collect market data
first, then ask for all missing risk inputs in one message. Do not delay useful
analysis while waiting for private account details. The user may provide a
hypothetical account size instead.

## 1. Resolve intent and instrument

Infer what is safe to infer and state it. Resolve:

- instrument ID and product: spot, perpetual swap, or dated future;
- direction: long, short, neutral, or let evidence decide;
- holding horizon and decision timeframe;
- plan currency and contract type;
- risk inputs for sizing, if requested.

Use exchange-native instrument IDs. For OKX, examples are `BTC-USDT`,
`BTC-USDT-SWAP`, and a listed dated-futures ID. Verify that the instrument
exists before analysis. Options require contract-specific Greeks and payoff
logic; provide analysis only unless those inputs are available.

## 2. Gather current evidence

Prefer read-only OKX market tools or the OKX CLI. Record source timestamps and
never present cached or example values as current.

Minimum useful data:

1. ticker and 24-hour volume;
2. candles for the execution timeframe plus at least two higher timeframes;
3. RSI, MACD, moving averages, ATR, and volume context;
4. support/resistance and recent swing structure;
5. for derivatives: funding, open interest, and order-book spread/imbalance.

Optional macro, liquidation, long/short, or whale data may improve context but
must be labeled by source. Missing optional data is not a zero signal. Exclude
it, reduce coverage, and explain the limitation.

For timeframe selection, evidence normalization, and conflict handling, read
[references/analysis-framework.md](references/analysis-framework.md).

## 3. Score evidence without hiding uncertainty

Organize observations into three pillars:

| Pillar | Default weight | Examples |
|---|---:|---|
| Price-volume | 40% | structure, trend, momentum, ATR, volume, patterns |
| Derivatives | 30% | funding, OI, basis, liquidations, order-book imbalance |
| Macro/regime | 30% | BTC dominance, broad risk regime, cycle indicators |

Assign each observed signal a score from -100 to +100 and a within-pillar
weight based on relevance. Use `scripts/signal_score.py` to calculate the
composite, coverage, and unavailable fields. Treat a low-coverage strong score
as low confidence, not as a strong recommendation.

Do not double-count correlated evidence. For example, EMA alignment and MACD
trend derived from the same candles should not each receive full independent
weight.

## 4. Convert evidence into a conditional setup

A valid setup needs all of the following:

- **Trigger**: a measurable event or entry zone, not "buy now" by default.
- **Invalidation**: a price beyond market structure, adjusted for volatility.
- **Targets**: technically defensible levels with net R:R after costs.
- **No-trade condition**: the event that makes waiting preferable.

When the requested direction conflicts with evidence, show both the requested
scenario and the evidence-led alternative. Do not force a directional plan.
When higher and lower timeframes conflict, either reduce size/confidence or wait
for alignment.

Read [references/plan-framework.md](references/plan-framework.md) when producing
a plan or sized plan.

## 5. Size the plan deterministically

For linear spot and USDT-margined products, run `scripts/risk_plan.py` with the
proposed levels and user limits. The script returns conservative, balanced,
and aggressive tiers while enforcing:

- maximum loss at the stop, including estimated fees and slippage;
- maximum margin allocation;
- maximum leverage;
- optional maximum notional exposure.

Do not use the linear calculator for inverse contracts or options. For those,
calculate from the exchange contract specification and clearly state the unit.
Never infer private account equity or silently choose a loss limit.

## 6. Present an auditable result

Return, in this order:

1. **Decision summary**: bias, confidence, coverage, and whether the setup is
   active, conditional, or no-trade.
2. **Evidence table**: timeframe/source, reading, direction, and timestamp.
3. **Setup**: trigger/entry zone, invalidation, targets, and no-trade condition.
4. **Three risk tiers**: units, notional, margin, leverage, stop loss in account
   currency and percent, and net R:R to each target.
5. **Scenario branches**: bullish, bearish, and range/stand-aside conditions.
6. **Data-quality note**: unavailable or stale fields and how they affect
   confidence.
7. **Risk notice**: informational analysis, not investment advice; execution
   remains the user's decision.

Use exact values where data supports them and formulas/placeholders where it
does not. Never fabricate a live price, signal, account balance, or fill.
