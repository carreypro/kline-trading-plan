# Plan framework

Use this reference when converting analysis into a plan.

## Required plan inputs

Market inputs:

- verified instrument and product type;
- direction or scenario;
- entry zone and trigger;
- stop/invalidation price;
- one or more targets;
- estimated fee and slippage per side.

Sizing inputs:

- account equity in the quote currency;
- maximum account loss percent for this idea;
- maximum margin allocation percent;
- maximum leverage;
- optional maximum notional exposure percent.

Treat account risk and margin allocation as different caps. Leverage changes
margin required, but it must not increase the accepted stop loss.

## Level construction

For a long, the stop must be below the worst entry price. For a short, it must
be above the worst entry price. Place invalidation beyond a structural level
with enough volatility allowance to avoid treating ordinary noise as thesis
failure. State the structure and the ATR multiple used.

Targets should correspond to liquidity, prior swing levels, measured moves, or
another inspectable method. Reject a target when net reward after estimated
costs is non-positive.

## Position sizing

For a linear instrument:

```text
risk_budget = account_equity * max_account_risk_pct * tier_fraction
loss_per_unit = abs(entry_worst - stop) + estimated_round_trip_cost_per_unit
units_by_risk = risk_budget / loss_per_unit
units_by_margin = account_equity * max_margin_pct * tier_margin_fraction
                  * tier_leverage / entry_worst
final_units = min(units_by_risk, units_by_margin, optional_notional_cap)
```

Use the worst price in the entry zone: its upper boundary for a long and lower
boundary for a short. Round down to the exchange lot size after calculation;
recompute actual risk after rounding.

Do not estimate liquidation price without the exchange's margin mode, contract
specification, maintenance-margin tier, and existing position context.

## Tier semantics

- **Conservative**: half of the maximum risk budget and margin allocation; 1x
  leverage unless the product requires otherwise.
- **Balanced**: three quarters of the maximum risk budget and margin allocation;
  no more than 2x leverage.
- **Aggressive**: may use the full user-defined caps. "Aggressive" never means
  exceeding them.

The tiers are exposure choices for the same valid setup, not three unrelated
predictions. If the setup is invalid, all tiers become no-trade.

## Output checklist

For each tier include:

- entry basis and trigger;
- units and unit definition;
- notional exposure, margin required, and leverage;
- stop price, loss at stop, and percent of equity;
- targets and net R:R;
- cap that constrained size;
- thesis invalidation and time stop.

Also show a no-trade branch. Common no-trade reasons include low data coverage,
conflicting higher timeframes, insufficient R:R, stale price, abnormal spread,
or an event risk that invalidates technical levels.
