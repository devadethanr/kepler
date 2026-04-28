import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_PURPLE, ACCENT_CYAN, ACCENT_YELLOW
)
from dashboard.components.command_center import agent_card

def setup_item(stock: rx.Var[dict]) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(stock["ticker"], font_weight="bold", size="3", color=TEXT_PRIMARY),
            rx.text(stock["setup_type"], size="1", color=TEXT_SECONDARY),
            align_items="start",
            spacing="0"
        ),
        rx.spacer(),
        rx.badge(
            stock["score"].to_string(), 
            color_scheme=rx.cond(stock["score"].to(int) >= 80, "green", "yellow"),
            variant="soft"
        ),
        width="100%",
        padding_y="0.5rem",
        border_bottom=f"1px solid {BORDER_COLOR}"
    )

def sector_item(sector: rx.Var[dict]) -> rx.Component:
    return rx.hstack(
        rx.text(sector["name"], color=TEXT_PRIMARY, size="3"),
        rx.spacer(),
        rx.badge(sector["count"].to_string(), " leads", variant="outline", color_scheme="cyan"),
        width="100%",
        padding_y="0.5rem",
        border_bottom=f"1px solid {BORDER_COLOR}"
    )

def research() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Research & Scans", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.button(
                    rx.icon(
                        rx.cond(GlobalState.is_scanning, "loader-2", "radar"),
                        size=16,
                        margin_right="2",
                        animation=rx.cond(GlobalState.is_scanning, "spin 2s linear infinite", "none")
                    ), 
                    rx.cond(GlobalState.is_scanning, "Scanning Market...", "Trigger Market Scan"), 
                    on_click=GlobalState.trigger_scan,
                    is_disabled=GlobalState.is_scanning,
                    color_scheme="cyan", 
                    variant="solid"
                ),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            
            rx.box(
                rx.cond(
                    GlobalState.is_scanning,
                    rx.text("Market scan in progress. Agents are analyzing intraday breakouts and sector rotation...", color=TEXT_SECONDARY),
                    rx.text(
                        "Last scan completed. ", 
                        GlobalState.latest_scan_result["qualified_count"].to_string(), 
                        " candidates identified.",
                        color=TEXT_SECONDARY
                    ),
                ),
                margin_bottom="2rem"
            ),
            rx.cond(
                GlobalState.agent_activity.length() > 0,
                rx.vstack(
                    rx.heading("Live Pipeline Execution", size="3", color=TEXT_PRIMARY, margin_bottom="1rem"),
                    rx.grid(
                        rx.foreach(
                            GlobalState.agent_activity,
                            lambda item: agent_card(item[0], item[1])
                        ),
                        columns=rx.breakpoints(initial="1", md="2", lg="3"),
                        spacing="4",
                        width="100%"
                    ),
                    width="100%",
                    margin_bottom="2rem",
                    padding="1.5rem",
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="12px",
                    background_color=CARD_BG,
                )
            ),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.hstack(rx.icon("flame", color=ACCENT_YELLOW), rx.heading("Trending Sectors", size="4", color=TEXT_PRIMARY)),
                        rx.divider(border_color=BORDER_COLOR, margin_y="1rem"),
                        rx.cond(
                            GlobalState.trending_sectors.length() > 0,
                            rx.vstack(
                                rx.foreach(GlobalState.trending_sectors, sector_item),
                                width="100%",
                                align_items="start"
                            ),
                            rx.center(
                                rx.text("No trending sectors identified in latest scan.", color=TEXT_SECONDARY, size="2"),
                                height="150px",
                                width="100%"
                            )
                        ),
                        align_items="start",
                        width="100%"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%",
                    min_height="300px"
                ),
                rx.card(
                    rx.vstack(
                        rx.hstack(rx.icon("target", color=ACCENT_CYAN), rx.heading("Top Setups", size="4", color=TEXT_PRIMARY)),
                        rx.divider(border_color=BORDER_COLOR, margin_y="1rem"),
                        rx.cond(
                            GlobalState.top_setups.length() > 0,
                            rx.vstack(
                                rx.foreach(GlobalState.top_setups, setup_item),
                                width="100%",
                                align_items="start"
                            ),
                            rx.center(
                                rx.text("Awaiting signal generation...", color=TEXT_SECONDARY, size="2"),
                                height="150px",
                                width="100%"
                            )
                        ),
                        align_items="start",
                        width="100%"
                    ),
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%",
                    min_height="300px"
                ),
                columns=rx.breakpoints(initial="1", md="2"),
                spacing="6",
                width="100%"
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem"
        )
    )
