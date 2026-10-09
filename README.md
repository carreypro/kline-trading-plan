# kline-trading-plan

An agent skill that joins multi-timeframe crypto technical analysis with a
deterministic, risk-capped trading plan.

It turns live K-line, price-volume, market-structure, and derivatives evidence
into:

- a three-pillar score with explicit data coverage;
- conditional entry, invalidation, targets, and no-trade rules;
- conservative, balanced, and aggressive position-sizing tiers;
- exact notional, margin, loss-at-stop, and net R:R calculations.

The skill is analysis-only and never authorizes order execution.

## Install

```bash
npx skills add https://github.com/carreypro/kline-trading-plan --skill kline-trading-plan
```

It works best with the OKX market-data tools or CLI available:

```bash
npm install -g @okx_ai/okx-trade-cli
```

No exchange credentials are needed for public market data. Keep execution and
account access in separate, explicitly authorized skills.

## Example prompts

```text
Use $kline-trading-plan to analyze BTC-USDT-SWAP and build a swing plan.
My hypothetical equity is 10,000 USDT, max loss is 1%, max margin is 20%,
and max leverage is 3x.
```

```text
用 $kline-trading-plan 分析 ETH-USDT-SWAP 的 1H/4H/1D 结构，只给条件单计划，
不需要账户仓位计算。
```

## Deterministic helpers

```bash
python3 scripts/signal_score.py --input signals.json
python3 scripts/risk_plan.py --input setup.json
```

Both scripts use Python's standard library only. `risk_plan.py` is for linear
spot and USDT-margined products; inverse contracts and options need their own
contract-specific sizing.

## Design provenance

The workflow combines the capability boundaries of the OKX Skills Marketplace
skills [**kline-indicator** by BokaChen](https://www.okx.com/en-us/agent-tradekit/skills/kline-indicator)
and [**trading-plan-generator**](https://www.okx.com/zh-hant/agent-tradekit/skills/trading-plan-generator).
This repository contains a new orchestration design and original helper
scripts; it does not republish either source skill's code.

## License

MIT. See [LICENSE](LICENSE).
