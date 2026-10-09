#!/usr/bin/env python3
"""Create capped three-tier sizing for a linear crypto trade setup."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_TIERS = (
    {"name": "conservative", "risk_fraction": 0.50, "margin_fraction": 0.50, "leverage_cap": 1.0},
    {"name": "balanced", "risk_fraction": 0.75, "margin_fraction": 0.75, "leverage_cap": 2.0},
    {"name": "aggressive", "risk_fraction": 1.00, "margin_fraction": 1.00, "leverage_cap": None},
)


def _number(payload: dict[str, Any], key: str, *, minimum: float | None = None) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{key}' must be a number")
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"'{key}' must be at least {minimum}")
    return value


def _round_down(value: float, step: float) -> float:
    if step <= 0:
        raise ValueError("'lot_size' must be positive")
    return math.floor((value + 1e-15) / step) * step


def _clean(value: float) -> float:
    return round(value, 10)


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    direction = str(payload.get("direction", "")).lower()
    if direction not in {"long", "short"}:
        raise ValueError("'direction' must be 'long' or 'short'")
    product = str(payload.get("product", "swap")).lower()
    if product not in {"spot", "swap", "futures"}:
        raise ValueError("'product' must be spot, swap, or futures")

    entry_low = _number(payload, "entry_low", minimum=0.0)
    entry_high = _number(payload, "entry_high", minimum=0.0)
    if entry_low <= 0 or entry_high < entry_low:
        raise ValueError("entry prices must satisfy 0 < entry_low <= entry_high")
    entry = entry_high if direction == "long" else entry_low
    stop = _number(payload, "stop_loss", minimum=0.0)
    if stop <= 0:
        raise ValueError("'stop_loss' must be positive")
    if direction == "long" and stop >= entry:
        raise ValueError("a long stop must be below the worst entry price")
    if direction == "short" and stop <= entry:
        raise ValueError("a short stop must be above the worst entry price")

    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("'targets' must be a non-empty array")
    targets = []
    for index, raw in enumerate(raw_targets):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"target {index + 1} must be a number")
        target = float(raw)
        valid = target > entry if direction == "long" else target < entry
        if not valid:
            raise ValueError(f"target {index + 1} is on the wrong side of the worst entry")
        targets.append(target)

    equity = _number(payload, "account_equity", minimum=0.0)
    max_risk_pct = _number(payload, "max_account_risk_pct", minimum=0.0)
    max_margin_pct = _number(payload, "max_margin_pct", minimum=0.0)
    max_leverage = _number(payload, "max_leverage", minimum=1.0)
    if equity <= 0 or max_risk_pct <= 0 or max_margin_pct <= 0:
        raise ValueError("equity and percentage caps must be positive")
    if product == "spot":
        max_leverage = 1.0

    max_notional_pct = payload.get("max_notional_pct")
    if max_notional_pct is not None:
        if isinstance(max_notional_pct, bool) or not isinstance(max_notional_pct, (int, float)):
            raise ValueError("'max_notional_pct' must be a number")
        max_notional_pct = float(max_notional_pct)
        if max_notional_pct <= 0:
            raise ValueError("'max_notional_pct' must be positive")

    fee_bps = float(payload.get("fee_bps_per_side", 5.0))
    slippage_bps = float(payload.get("slippage_bps_per_side", 3.0))
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee and slippage estimates cannot be negative")
    lot_size = float(payload.get("lot_size", 0.00000001))

    stop_distance = abs(entry - stop)
    round_trip_cost = entry * 2.0 * (fee_bps + slippage_bps) / 10000.0
    loss_per_unit = stop_distance + round_trip_cost
    target_rows = []
    for target in targets:
        gross_reward = target - entry if direction == "long" else entry - target
        net_reward = gross_reward - round_trip_cost
        target_rows.append(
            {
                "price": target,
                "gross_reward_per_unit": _clean(gross_reward),
                "net_reward_per_unit": _clean(net_reward),
                "net_rr": _clean(net_reward / loss_per_unit),
            }
        )

    tier_specs = payload.get("tiers", list(DEFAULT_TIERS))
    if not isinstance(tier_specs, list) or not tier_specs:
        raise ValueError("'tiers' must be a non-empty array")

    tiers = []
    for raw_tier in tier_specs:
        if not isinstance(raw_tier, dict):
            raise ValueError("each tier must be an object")
        name = str(raw_tier.get("name", "tier"))
        risk_fraction = float(raw_tier.get("risk_fraction", 1.0))
        margin_fraction = float(raw_tier.get("margin_fraction", 1.0))
        leverage_cap = raw_tier.get("leverage_cap")
        leverage = max_leverage if leverage_cap is None else min(max_leverage, float(leverage_cap))
        if not 0 < risk_fraction <= 1 or not 0 < margin_fraction <= 1 or leverage < 1:
            raise ValueError(f"tier '{name}' has invalid fractions or leverage")

        risk_budget = equity * max_risk_pct / 100.0 * risk_fraction
        margin_budget = equity * max_margin_pct / 100.0 * margin_fraction
        units_by_risk = risk_budget / loss_per_unit
        units_by_margin = margin_budget * leverage / entry
        candidates = {"risk_cap": units_by_risk, "margin_cap": units_by_margin}
        if max_notional_pct is not None:
            candidates["notional_cap"] = equity * max_notional_pct / 100.0 / entry
        limiting_cap = min(candidates, key=candidates.get)
        units = _round_down(candidates[limiting_cap], lot_size)
        notional = units * entry
        margin_required = notional / leverage
        loss_at_stop = units * loss_per_unit

        tiers.append(
            {
                "name": name,
                "units": _clean(units),
                "unit_definition": "base-asset units for a linear instrument",
                "entry_worst": entry,
                "leverage": _clean(leverage),
                "notional": _clean(notional),
                "margin_required": _clean(margin_required),
                "loss_at_stop_including_costs": _clean(loss_at_stop),
                "account_risk_pct": _clean(loss_at_stop / equity * 100.0),
                "risk_budget": _clean(risk_budget),
                "limiting_cap": limiting_cap,
                "targets": [
                    {
                        **row,
                        "estimated_net_pnl": _clean(units * row["net_reward_per_unit"]),
                    }
                    for row in target_rows
                ],
            }
        )

    return {
        "direction": direction,
        "product": product,
        "entry_zone": [entry_low, entry_high],
        "sizing_entry": entry,
        "stop_loss": stop,
        "stop_distance": _clean(stop_distance),
        "estimated_round_trip_cost_per_unit": _clean(round_trip_cost),
        "loss_per_unit_including_costs": _clean(loss_per_unit),
        "caps": {
            "account_equity": equity,
            "max_account_risk_pct": max_risk_pct,
            "max_margin_pct": max_margin_pct,
            "max_leverage": max_leverage,
            "max_notional_pct": max_notional_pct,
        },
        "tiers": tiers,
        "warnings": [
            "Linear sizing only; do not use for inverse contracts or options.",
            "Liquidation price is not estimated.",
            "Round-trip costs are estimates; verify exchange fees, spread, lot size, and contract multiplier.",
            "This calculation is informational and not investment advice.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to input JSON, or - for stdin")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = calculate(json.loads(text))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
