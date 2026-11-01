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

# Retain frozen experiment paths while giving the final candidates stable filenames.
PROMPT_FILE_RENAMES = {
    "contract-v2.md": "contract-analyst.md",
    "evidence-v2.md": "evidence-analyst.md",
    "contract-v7.md": "contract-agent.md",
    "evidence-v7.md": "evidence-agent.md",
}


def prompt_path(name: str) -> Path:
    return Path(__file__).with_name("prompts") / PROMPT_FILE_RENAMES.get(name, name)


def evaluation_prompts(variant: str, instructions: str, task: str) -> tuple[str, str]:
    if variant == "baseline":
        return instructions, task
    if variant not in VARIANTS:
        raise ValueError("Unknown prompt candidate")
    if variant in ("generic-baseline", "policy-v2", "policy-v3"):
        task = prompt_path("contract-generic.md").read_text()
    if variant in ("policy-v2", "combined-v2"):
        instructions = prompt_path("evidence-v2.md").read_text()
    if variant in ("format-v2", "combined-v2"):
        task = prompt_path("contract-v2.md").read_text()
    if variant in ("policy-v3", "combined-v3"):
        instructions = prompt_path("evidence-v3.md").read_text()
    if variant == "combined-v3":
        task = prompt_path("contract-v3.md").read_text()
    if variant == "combined-v4":
        instructions = prompt_path("evidence-v4.md").read_text()
        task = prompt_path("contract-v4.md").read_text()
    if variant == "combined-v5":
        instructions = prompt_path("evidence-v5.md").read_text()
        task = prompt_path("contract-v5.md").read_text()
    if variant == "combined-v6":
        instructions = prompt_path("evidence-v2.md").read_text()
        task = prompt_path("contract-v6.md").read_text()
    if variant == "combined-v7":
        instructions = prompt_path("evidence-v7.md").read_text()
        task = prompt_path("contract-v7.md").read_text()
    return instructions, task
