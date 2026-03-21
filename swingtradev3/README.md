# swingtradev3

Autonomous swing-trading research and execution system for Indian equities.

This repository follows the v6 design document and is organized around:

- `research_agent` for nightly scanning and morning briefing
- `execution_agent` for approvals, entries, GTT lifecycle, and reconciliation
- shared `backtest`, `paper`, and `live` adapters behind `trading.mode`

## Quick start

1. Create `swingtradev3/.env` from `.env.example`.
2. Review and update `config.yaml`.
3. Install dependencies from `requirements.txt`.
4. Run tests with `pytest`.
5. Start a backtest with `python main.py --mode backtest`.

## Current status

The repository contains the normalized config, persistent state contracts, paper execution core,
research/execution scaffolding, and tests for the shared engine behavior. External services such as
Kite, Telegram, and LLM providers are integrated via adapters and require credentials to run live.
