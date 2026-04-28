import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState
from dashboard.components.command_center import agent_card
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_PURPLE, ACCENT_GREEN, ACCENT_YELLOW, ACCENT_RED
)

def activity() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Agent Activity Log", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.badge("Live Stream Connected", color_scheme="green", size="3"),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            
            rx.text("Detailed logs and live execution traces for all agents in the pipeline.", color=TEXT_SECONDARY, margin_bottom="2rem"),
            
            rx.box(
                rx.foreach(
                    GlobalState.agent_activity,
                    lambda item: rx.box(
                        agent_card(item[0], item[1]),
                        margin_bottom="1rem"
                    )
                ),
                width="100%"
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem"
        )
    )
