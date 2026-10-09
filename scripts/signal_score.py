#!/usr/bin/env python3
"""Aggregate normalized market signals without treating missing data as zero."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_PILLAR_WEIGHTS = {
    "price_volume": 40.0,
    "derivatives": 30.0,
    "macro": 30.0,
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    return float(value)


def _label(score: float) -> str:
    if score >= 45:
        return "strong_bullish"
    if score >= 20:
        return "bullish"
    if score <= -45:
        return "strong_bearish"
    if score <= -20:
        return "bearish"
    return "neutral"


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    pillars = payload.get("pillars")
    if not isinstance(pillars, dict):
        raise ValueError("input must contain a 'pillars' object")

    names = list(DEFAULT_PILLAR_WEIGHTS)
    for name in pillars:
        if name not in names:
            names.append(name)

    results: dict[str, Any] = {}
    weighted_score = 0.0
    available_pillar_weight = 0.0
    total_pillar_weight = 0.0
    weighted_coverage = 0.0
    available_pillars = 0
    missing: list[str] = []

    for name in names:
        spec = pillars.get(name, {})
        if spec is None:
            spec = {}
        if not isinstance(spec, dict):
            raise ValueError(f"pillar '{name}' must be an object")
        pillar_weight = _number(
            spec.get("weight", DEFAULT_PILLAR_WEIGHTS.get(name, 0.0)),
            f"pillar '{name}' weight",
        )
        if pillar_weight < 0:
            raise ValueError(f"pillar '{name}' weight cannot be negative")
        total_pillar_weight += pillar_weight

        signals = spec.get("signals", [])
        if not isinstance(signals, list):
            raise ValueError(f"pillar '{name}' signals must be an array")

        requested_weight = 0.0
        observed_weight = 0.0
        subtotal = 0.0
        observations: list[dict[str, Any]] = []

        for index, signal in enumerate(signals):
            if not isinstance(signal, dict):
                raise ValueError(f"pillar '{name}' signal {index} must be an object")
            signal_name = str(signal.get("name", f"signal_{index + 1}"))
            weight = _number(signal.get("weight", 1.0), f"signal '{signal_name}' weight")
            if weight <= 0:
                raise ValueError(f"signal '{signal_name}' weight must be positive")
            requested_weight += weight
            available = signal.get("available", True) is not False and signal.get("score") is not None
            if not available:
                missing.append(f"{name}.{signal_name}")
                observations.append({"name": signal_name, "available": False, "weight": weight})
                continue

            score = _number(signal["score"], f"signal '{signal_name}' score")
            if score < -100 or score > 100:
                raise ValueError(f"signal '{signal_name}' score must be between -100 and 100")
            observed_weight += weight
            subtotal += score * weight
            observations.append(
                {
                    "name": signal_name,
                    "available": True,
                    "score": score,
                    "weight": weight,
                    "value": signal.get("value"),
                }
            )

        coverage = observed_weight / requested_weight if requested_weight else 0.0
        pillar_score = subtotal / observed_weight if observed_weight else None
        if pillar_score is not None and pillar_weight > 0:
            weighted_score += pillar_score * pillar_weight
            available_pillar_weight += pillar_weight
            available_pillars += 1
        weighted_coverage += coverage * pillar_weight

        results[name] = {
            "score": round(pillar_score, 2) if pillar_score is not None else None,
            "coverage": round(coverage, 4),
            "weight": pillar_weight,
            "signals": observations,
        }

    if total_pillar_weight <= 0:
        raise ValueError("total pillar weight must be positive")

    composite = weighted_score / available_pillar_weight if available_pillar_weight else None
    coverage = weighted_coverage / total_pillar_weight
    if coverage >= 0.75:
        confidence = "high"
    elif coverage >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "composite_score": round(composite, 2) if composite is not None else None,
        "bias": _label(composite) if composite is not None else "insufficient_data",
        "coverage": round(coverage, 4),
        "confidence": confidence,
        "available_pillars": available_pillars,
        "pillars": results,
        "missing": missing,
        "notes": [
            "Missing signals are excluded from the score and reduce coverage.",
            "The score is evidence direction, not win probability or investment advice.",
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
