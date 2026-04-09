from swingtradev3.config import cfg


def test_llm_roles_config_present() -> None:
    assert cfg.llm.roles.research.model
    assert cfg.llm.roles.execution.model
    assert cfg.llm.roles.analyst.model


def test_execution_block_contains_corporate_actions() -> None:
    assert cfg.execution.corporate_action_handling.auto_adjust_timeout_hours == 12
