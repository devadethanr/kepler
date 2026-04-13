import reflex as rx
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, ACCENT_PURPLE, ACCENT_GREEN, ACCENT_YELLOW, TEXT_SECONDARY, ACCENT_CYAN, ACCENT_RED
)
from dashboard.state import GlobalState

# CSS Animation for a glowing pulse effect
pulse_animation = """
@keyframes pulseGlow {
  0% { box-shadow: 0 0 0 0 rgba(76, 29, 149, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(76, 29, 149, 0); }
  100% { box-shadow: 0 0 0 0 rgba(76, 29, 149, 0); }
}
"""

def agent_node(name: str, icon_name: str, phase_trigger: str) -> rx.Component:
    """A visual node representing an agent in the pipeline."""
    # Determine if this node is currently active
    is_active = GlobalState.scheduler_phase.lower() == phase_trigger.lower()
    
    # Node colors based on active state
    bg_color = rx.cond(
        is_active,
        ACCENT_PURPLE,
        CARD_BG
    )
    
    border_color = rx.cond(
        is_active,
        ACCENT_PURPLE,
        BORDER_COLOR
    )
    
    icon_color = rx.cond(
        is_active,
        "#ffffff",
        TEXT_SECONDARY
    )
    
    text_color = rx.cond(
        is_active,
        "#ffffff",
        TEXT_PRIMARY
    )
    
    # The node UI
    return rx.vstack(
        rx.center(
            rx.icon(icon_name, size=24, color=icon_color),
            width="60px",
            height="60px",
            border_radius="50%",
            background_color=bg_color,
            border=f"2px solid {BORDER_COLOR}",
            border_color=border_color,
            style=rx.cond(
                is_active,
                {"animation": "pulseGlow 2s infinite"},
                {}
            ),
            transition="all 0.3s ease",
            z_index="2",
        ),
        rx.text(name, size="2", font_weight="bold", color=text_color, text_align="center"),
        align_items="center",
        width="100px"
    )

def pipeline_connector(is_active: bool = False) -> rx.Component:
    """The connecting line between agents."""
    return rx.box(
        width="40px",
        height="4px",
        background_color=rx.cond(is_active, ACCENT_PURPLE, BORDER_COLOR),
        margin_bottom="24px",  # Offset to align with circles
        transition="background-color 0.5s ease",
    )

def pipeline_flow() -> rx.Component:
    """The full pipeline visualization."""
    return rx.box(
        rx.html(f"<style>{pulse_animation}</style>"),
        rx.card(
            rx.vstack(
                rx.heading("System Pipeline", size="4", color=TEXT_PRIMARY, margin_bottom="1rem"),
                
                # We'll map out a static representation of the SwingTrade pipeline
                rx.hstack(
                    agent_node("Market Scanner", "radar", "scan"),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "filter"),
                    agent_node("Filter & Score", "filter", "filter"),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "analyze"),
                    agent_node("Deep Analyst", "brain", "analyze"),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "review"),
                    agent_node("Risk Manager", "shield-alert", "review"),
                    pipeline_connector(GlobalState.scheduler_phase.lower() == "execute"),
                    agent_node("Execution Engine", "zap", "execute"),
                    
                    align_items="center",
                    justify_content="center",
                    width="100%",
                    padding="1rem"
                ),
                width="100%"
            ),
            background_color=CARD_BG,
            border=f"1px solid {BORDER_COLOR}",
            border_radius="12px",
            padding="1.5rem",
            width="100%",
            margin_bottom="2rem"
        )
    )
