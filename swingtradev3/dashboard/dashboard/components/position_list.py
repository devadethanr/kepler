import reflex as rx
from dashboard.state import GlobalState
from dashboard.components.position_card import position_card
from dashboard.styles import TEXT_SECONDARY

def position_list() -> rx.Component:
    return rx.box(
        rx.cond(
            GlobalState.positions.length() > 0,
            rx.grid(
                rx.foreach(
                    GlobalState.positions,
                    lambda pos: position_card(pos)
                ),
                columns=rx.breakpoints(
                    initial="1",
                    sm="2",
                    md="3",
                    lg="3",
                ),
                spacing="4",
                width="100%"
            ),
            rx.center(
                rx.vstack(
                    rx.icon("briefcase", size=48, color=TEXT_SECONDARY, opacity=0.3),
                    rx.text("No active positions tracked in current session", color=TEXT_SECONDARY, size="3"),
                    spacing="4",
                    padding_y="4rem"
                ),
                width="100%"
            )
        ),
        width="100%"
    )
