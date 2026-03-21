from __future__ import annotations

from pathlib import Path

from swingtradev3.models import AccountState, StatsSnapshot
from swingtradev3.paths import STRATEGY_DIR


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class PromptBuilder:
    def build_research_messages(
        self,
        stock_context: dict[str, object],
        state: AccountState,
        stats: StatsSnapshot,
    ) -> list[dict[str, str]]:
        system_prompt = "\n\n".join(
            [
                _read_text(STRATEGY_DIR / "SKILL.md"),
                _read_text(STRATEGY_DIR / "research_program.md"),
                f"Open positions: {state.model_dump_json()}",
                f"Recent stats: {stats.model_dump_json()}",
            ]
        )
        user_prompt = (
            "Analyze this stock using the strategy documents and return only JSON with keys "
            "score, setup_type, entry_zone, stop_price, target_price, holding_days_expected, "
            "confidence_reasoning, risk_flags.\n\n"
            f"Stock context:\n{stock_context}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_analyst_messages(
        self,
        trades_payload: str,
        observations_payload: str,
        stats_payload: str,
    ) -> list[dict[str, str]]:
        system_prompt = "\n\n".join(
            [
                _read_text(STRATEGY_DIR / "SKILL.md"),
                _read_text(STRATEGY_DIR / "analyst_program.md"),
            ]
        )
        user_prompt = (
            "Review these trades and observations and propose at most three specific SKILL.md edits.\n\n"
            f"Trades:\n{trades_payload}\n\nObservations:\n{observations_payload}\n\nStats:\n{stats_payload}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
