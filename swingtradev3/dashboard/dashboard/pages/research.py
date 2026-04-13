import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_PURPLE, ACCENT_CYAN, ACCENT_YELLOW
)

def research() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Research & Scans", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.button(
                    rx.icon("radar", size=16), 
                    "Trigger Market Scan", 
                    color_scheme="cyan", 
                    variant="solid"
                ),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            
            rx.text("Deep market analysis and signal generation will appear here.", color=TEXT_SECONDARY, margin_bottom="2rem"),
            
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.hstack(rx.icon("flame", color=ACCENT_YELLOW), rx.heading("Trending Sectors", size="4", color=TEXT_PRIMARY)),
                        rx.divider(border_color=BORDER_COLOR),
                        rx.text("Awaiting data point injection...", color=TEXT_SECONDARY),
                        align_items="start"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%",
                    height="300px"
                ),
                rx.card(
                    rx.vstack(
                        rx.hstack(rx.icon("target", color=ACCENT_CYAN), rx.heading("Top Setups", size="4", color=TEXT_PRIMARY)),
                        rx.divider(border_color=BORDER_COLOR),
                        rx.text("Awaiting data point injection...", color=TEXT_SECONDARY),
                        align_items="start"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%",
                    height="300px"
                ),
                columns="2",
                spacing="6",
                width="100%"
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem"
        )
    )
