"""Explicit evaluation candidates; the installed room keeps its selected prompt."""

from pathlib import Path

VARIANTS = (
    "baseline",
    "generic-baseline",
    "policy-v2",
    "format-v2",
    "combined-v2",
    "policy-v3",
    "combined-v3",
    "combined-v4",
    "combined-v5",
    "combined-v6",
    "combined-v7",
)


def evaluation_prompts(variant: str, instructions: str, task: str) -> tuple[str, str]:
    if variant == "baseline":
        return instructions, task
    if variant not in VARIANTS:
        raise ValueError("Unknown prompt candidate")
    root = Path(__file__).with_name("prompts")
    if variant in ("generic-baseline", "policy-v2", "policy-v3"):
        task = (root / "contract-generic.md").read_text()
    if variant in ("policy-v2", "combined-v2"):
        instructions = (root / "evidence-v2.md").read_text()
    if variant in ("format-v2", "combined-v2"):
        task = (root / "contract-v2.md").read_text()
    if variant in ("policy-v3", "combined-v3"):
        instructions = (root / "evidence-v3.md").read_text()
    if variant == "combined-v3":
        task = (root / "contract-v3.md").read_text()
    if variant == "combined-v4":
        instructions = (root / "evidence-v4.md").read_text()
        task = (root / "contract-v4.md").read_text()
    if variant == "combined-v5":
        instructions = (root / "evidence-v5.md").read_text()
        task = (root / "contract-v5.md").read_text()
    if variant == "combined-v6":
        instructions = (root / "evidence-v2.md").read_text()
        task = (root / "contract-v6.md").read_text()
    if variant == "combined-v7":
        instructions = (root / "evidence-v7.md").read_text()
        task = (root / "contract-v7.md").read_text()
    return instructions, task
