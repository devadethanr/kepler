import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState
from dashboard.components.position_list import position_list
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
                    rx.icon("refresh-cw", size=16, margin_right="2"), 
                    "Sync Account", 
                    on_click=GlobalState.fetch_initial_data,
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
                        rx.heading(rx.text(GlobalState.positions.length(), " positions"), size="4", color=TEXT_PRIMARY)
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Unrealized P&L", color=TEXT_SECONDARY),
                        rx.heading(
                            rx.text("₹", GlobalState.portfolio_summary["unrealized_pnl"]), 
                            size="4", 
                            color=rx.cond(GlobalState.portfolio_summary["unrealized_pnl"].to(float) >= 0, ACCENT_GREEN, ACCENT_RED)
                        )
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Available Margin", color=TEXT_SECONDARY),
                        rx.heading(rx.text("₹", GlobalState.portfolio_summary["cash_inr"]), size="4", color=ACCENT_YELLOW)
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
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.heading("Sector Exposure", size="4", color=TEXT_PRIMARY),
                        rx.plotly(data=GlobalState.sector_exposure_fig, height="250px", width="100%"),
                        width="100%",
                        align_items="center"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.heading("Risk Utilization", size="4", color=TEXT_PRIMARY),
                        rx.plotly(data=GlobalState.risk_utilization_fig, height="250px", width="100%"),
                        width="100%",
                        align_items="center"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%"
                ),
                columns=rx.breakpoints(initial="1", md="2"),
                spacing="4",
                width="100%",
                margin_bottom="2rem"
            ),
            rx.vstack(
                rx.heading("Active Trades", size="5", color=TEXT_PRIMARY, margin_bottom="1rem"),
                position_list(),
                width="100%",
                align_items="start"
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem"
        )
    )
