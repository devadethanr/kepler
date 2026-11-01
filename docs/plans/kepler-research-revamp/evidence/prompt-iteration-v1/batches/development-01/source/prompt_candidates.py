"""Explicit evaluation candidates; the installed room keeps its selected prompt."""

from pathlib import Path

VARIANTS = ("baseline", "generic-baseline", "policy-v2", "format-v2", "combined-v2")


def evaluation_prompts(variant: str, instructions: str, task: str) -> tuple[str, str]:
    if variant == "baseline":
        return instructions, task
    if variant not in VARIANTS:
        raise ValueError("Unknown prompt candidate")
    root = Path(__file__).with_name("prompts")
    if variant in ("generic-baseline", "policy-v2"):
        task = (root / "contract-generic.md").read_text()
    if variant in ("policy-v2", "combined-v2"):
        instructions = (root / "evidence-v2.md").read_text()
    if variant in ("format-v2", "combined-v2"):
        task = (root / "contract-v2.md").read_text()
    return instructions, task
