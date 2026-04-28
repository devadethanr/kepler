import reflex as rx
from dashboard.styles import (
    CARD_BG,
    BORDER_COLOR,
    TEXT_PRIMARY,
    ACCENT_PURPLE,
    ACCENT_GREEN,
    ACCENT_YELLOW,
    TEXT_SECONDARY,
    ACCENT_CYAN,
    ACCENT_RED,
    ACCENT_GREEN_DIM,
)
from dashboard.state import GlobalState

pulse_animation = """
@keyframes pulseGlow {
  0% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.6); }
  70% { box-shadow: 0 0 0 15px rgba(139, 92, 246, 0); }
  100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
}
@keyframes flowPulse {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}
@keyframes slideIn {
  from { transform: translateY(-10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
"""


def pipeline_node(name: str, icon_name: str, is_active: bool) -> rx.Component:
    """A visual node representing a pipeline stage."""
    bg = rx.cond(is_active, ACCENT_PURPLE, CARD_BG)
    border = rx.cond(is_active, ACCENT_PURPLE, BORDER_COLOR)
    icon_col = rx.cond(is_active, "#ffffff", TEXT_SECONDARY)
    text_col = rx.cond(is_active, "#ffffff", TEXT_PRIMARY)

    return rx.vstack(
        rx.center(
            rx.icon(icon_name, size=22, color=icon_col),
            width="56px",
            height="56px",
            border_radius="50%",
            background_color=bg,
            border=f"2px solid {border}",
            style=rx.cond(is_active, {"animation": "pulseGlow 2s infinite"}, {}),
            transition="all 0.3s ease",
            z_index="2",
        ),
        rx.text(
            name, size="1", font_weight="600", color=text_col, text_align="center", max_width="80px"
        ),
        align_items="center",
        spacing="2",
    )


def pipeline_connector(is_active: bool) -> rx.Component:
    """Animated connector between pipeline stages."""
    return rx.box(
        width="30px",
        height="3px",
        background_color=rx.cond(is_active, ACCENT_PURPLE, BORDER_COLOR),
        style=rx.cond(is_active, {"animation": "flowPulse 1.5s infinite"}, {}),
        transition="all 0.3s ease",
    )


def active_agents_badge() -> rx.Component:
    """Show list of currently running agents as animated badges."""
    return rx.cond(
        GlobalState.running_agents_count > 0,
        rx.vstack(
            rx.text(
                "Running Agents",
                size="2",
                color=TEXT_SECONDARY,
                font_weight="600",
                margin_bottom="0.5rem",
            ),
            rx.box(
                rx.hstack(
                    rx.foreach(
                        GlobalState.agent_activity,
                        lambda item: rx.cond(
                            item[1]["status"].to(str) == "running",
                            rx.badge(
                                rx.hstack(
                                    rx.icon("loader_circle", size=12, color=ACCENT_GREEN),
                                    rx.text(item[0], size="1", color=ACCENT_GREEN),
                                    spacing="1",
                                ),
                                background_color=ACCENT_GREEN_DIM,
                                border_color=ACCENT_GREEN,
                                border_width="1px",
                                padding="4px 8px",
                                border_radius="full",
                            ),
                            rx.fragment(),
                        ),
                    ),
                    spacing="2",
                    flex_wrap="wrap",
                ),
                width="100%",
            ),
            spacing="1",
            align_items="start",
            margin_top="1rem",
            padding="1rem",
            background_color="rgba(0,0,0,0.2)",
            border_radius="8px",
        ),
        rx.box(
            rx.hstack(
                rx.icon("check_check", size=16, color=ACCENT_GREEN),
                rx.text("All agents idle", size="2", color=TEXT_SECONDARY),
                spacing="2",
                align_items="center",
            ),
            margin_top="1rem",
            padding="1rem",
            background_color="rgba(16, 185, 129, 0.1)",
            border_radius="8px",
        ),
    )


def pipeline_flow() -> rx.Component:
    """The full dynamic pipeline visualization."""
    return rx.box(
        rx.html(f"<style>{pulse_animation}</style>"),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("System Pipeline", size="4", color=TEXT_PRIMARY),
                    rx.spacer(),
                    rx.hstack(
                        rx.box(
                            width="8px",
                            height="8px",
                            border_radius="full",
                            background_color=rx.cond(
                                GlobalState.running_agents_count > 0, ACCENT_GREEN, TEXT_SECONDARY
                            ),
                            style=rx.cond(
                                GlobalState.running_agents_count > 0,
                                {"animation": "pulseGlow 2s infinite"},
                                {},
                            ),
                        ),
                        rx.text(
                            rx.cond(
                                GlobalState.running_agents_count > 0,
                                f"{GlobalState.running_agents_count} active",
                                "Idle",
                            ),
                            size="2",
                            color=rx.cond(
                                GlobalState.running_agents_count > 0, ACCENT_GREEN, TEXT_SECONDARY
                            ),
                            font_weight="500",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    width="100%",
                    margin_bottom="1rem",
                ),
                rx.hstack(
                    pipeline_node(
                        "Scanner", "radar", GlobalState.scheduler_phase.lower() == "scan"
                    ),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "scan"),
                    pipeline_node(
                        "Filter", "filter", GlobalState.scheduler_phase.lower() == "filter"
                    ),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "filter"),
                    pipeline_node(
                        "Analyst", "brain", GlobalState.scheduler_phase.lower() == "analyze"
                    ),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "analyze"),
                    pipeline_node(
                        "Risk", "shield-check", GlobalState.scheduler_phase.lower() == "review"
                    ),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "review"),
                    pipeline_node(
                        "Execute", "zap", GlobalState.scheduler_phase.lower() == "execute"
                    ),
                    align_items="center",
                    justify_content="center",
                    width="100%",
                    spacing="0",
                ),
                active_agents_badge(),
                width="100%",
            ),
            background_color=CARD_BG,
            border=f"1px solid {BORDER_COLOR}",
            border_radius="12px",
            padding="1.5rem",
            width="100%",
        ),
    )
