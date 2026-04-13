import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_GREEN, ACCENT_RED, ACCENT_BLUE
)

def approvals() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Pending Approvals", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.badge("0 Pending", color_scheme="blue", size="3"),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            
            rx.text("Review and approve Deep Analyst trade recommendations here.", color=TEXT_SECONDARY, margin_bottom="2rem"),
            
            rx.box(
                rx.vstack(
                    rx.icon("circle-check", size=48, color=TEXT_SECONDARY),
                    rx.heading("All Caught Up", size="5", color=TEXT_PRIMARY, margin_top="1rem"),
                    rx.text("There are no trade decisions waiting for your approval right now.", color=TEXT_SECONDARY),
                    align_items="center",
                ),
                width="100%",
                padding="4rem",
                background_color=CARD_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                text_align="center"
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem"
        )
    )
