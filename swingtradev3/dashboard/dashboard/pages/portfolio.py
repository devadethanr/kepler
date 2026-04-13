import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_GREEN, ACCENT_PURPLE, ACCENT_YELLOW, ACCENT_RED
)

def portfolio() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Portfolio Manager", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=16), 
                    "Sync Account", 
                    color_scheme="purple", 
                    variant="solid"
                ),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.text("Holdings", color=TEXT_SECONDARY),
                        rx.heading("0 positions", size="4", color=TEXT_PRIMARY)
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Unrealized P&L", color=TEXT_SECONDARY),
                        rx.heading("₹0.00", size="4", color=ACCENT_GREEN)
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Available Margin", color=TEXT_SECONDARY),
                        rx.heading("₹0.00", size="4", color=ACCENT_YELLOW)
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="2rem"
            ),
            rx.box(
                rx.heading("Active Trades", size="5", color=TEXT_PRIMARY, margin_bottom="1rem"),
                rx.text("No active trades found. Waiting for execution events...", color=TEXT_SECONDARY),
                width="100%",
                padding="2rem",
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
