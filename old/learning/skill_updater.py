from __future__ import annotations

from datetime import datetime

from swingtradev3.paths import STRATEGY_DIR


class SkillUpdater:
    def apply_staging(self) -> str:
        skill_path = STRATEGY_DIR / "SKILL.md"
        staging_path = STRATEGY_DIR / "SKILL.md.staging"
        skill = skill_path.read_text(encoding="utf-8")
        staging = staging_path.read_text(encoding="utf-8").strip()
        if not staging:
            return skill
        updated = f"{skill.rstrip()}\n\n## Monthly lesson {datetime.utcnow().date()}\n{staging}\n"
        skill_path.write_text(updated, encoding="utf-8")
        staging_path.write_text("# Pending monthly lessons\n", encoding="utf-8")
        return updated
