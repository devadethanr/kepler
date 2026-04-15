import reflex as rx
from dashboard.state import GlobalState
from dashboard.components.pipeline_flow import pipeline_flow
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_GREEN, ACCENT_BLUE, ACCENT_CYAN, ACCENT_RED,
    ACCENT_GREEN_DIM, ACCENT_PURPLE, ACCENT_YELLOW
)

def status_badge(status: rx.Var) -> rx.Component:
    status_str = status.to(str).lower()
    color = rx.match(
        status_str,
        ("running", ACCENT_GREEN),
        ("idle", ACCENT_PURPLE),
        ("error", ACCENT_RED),
        TEXT_SECONDARY
    )
    bg = rx.match(
        status_str,
        ("running", ACCENT_GREEN_DIM),
        ("idle", "rgba(88, 166, 255, 0.15)"),
        ("error", "rgba(255, 68, 68, 0.15)"),
        BORDER_COLOR
    )
        
    return rx.badge(
        rx.icon("circle", size=10, fill="currentColor", margin_right="2"),
        status.to(str).upper(),
        color=color,
        background_color=bg,
        border_radius="full",
        padding="0.2rem 0.6rem",
        font_weight="bold",
        font_size="0.75rem"
    )

def agent_card(agent_name: rx.Var[str], state_agent: rx.Var[dict]) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(agent_name, font_weight="bold", size="4"),
                rx.text(state_agent["last_event"], color=TEXT_SECONDARY, size="2", max_width="250px", overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
                align_items="start",
                spacing="2"
            ),
            rx.spacer(),
            status_badge(state_agent["status"]),
            width="100%",
            align_items="center"
        ),
        # A subtle pulse animation if running
        animation=rx.cond(
            state_agent["status"].to(str) == "running",
            "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            "none"
        ),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        background_color=CARD_BG,
        padding="1rem",
        margin_bottom="1rem"
    )

def overview_metric(title: str, value: any, icon_tag: str, color: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon_tag, size=24, color=color),
                padding="0.75rem",
                background_color=f"{color}20",  # Translucent background
                border_radius="12px"
            ),
            rx.vstack(
                rx.text(title, color=TEXT_SECONDARY, size="2"),
                rx.text(value, font_weight="bold", size="5"),
                align_items="start",
                spacing="1"
            ),
            spacing="4"
        ),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        background_color=CARD_BG,
        padding="1.5rem",
        flex="1"
    )

def command_center() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Command Center", size="7", color=TEXT_PRIMARY),
            rx.spacer(),
            rx.badge(GlobalState.scheduler_phase.upper(), color_scheme="purple", size="2"),
            width="100%",
            align_items="center",
            margin_bottom="2rem"
        ),
        
        # Top Metrics
        rx.hstack(
            overview_metric("Open Positions", GlobalState.portfolio_summary["open_positions_count"].to_string(), "briefcase", ACCENT_PURPLE),
            overview_metric("Total Invested", rx.text("₹", GlobalState.portfolio_summary["total_invested"]), "wallet", ACCENT_YELLOW),
            overview_metric("Overall PNL", rx.text("₹", GlobalState.portfolio_summary["total_pnl"]), "pie-chart", ACCENT_GREEN),
            width="100%",
            spacing="4",
            margin_bottom="2rem"
        ),
        
        pipeline_flow(),
        
        # Next Section: Agent Activity & System Health
        rx.grid(
            rx.vstack(
                rx.hstack(
                    rx.icon("activity", color=TEXT_PRIMARY),
                    rx.heading("Live Agent Activity", size="5", color=TEXT_PRIMARY),
                    align_items="center",
                    spacing="2"
                ),
                rx.divider(border_color=BORDER_COLOR, margin_y="1rem"),
                rx.foreach(
                    GlobalState.agent_activity,
                    lambda item: agent_card(item[0], item[1])
                ),
                width="100%",
                background_color=CARD_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="1.5rem"
            ),
            # Empty right space or another widget
            rx.vstack(
                rx.hstack(
                    rx.icon("server", color=TEXT_PRIMARY),
                    rx.heading("System Health", size="5", color=TEXT_PRIMARY),
                    align_items="center",
                    spacing="2"
                ),
                rx.divider(border_color=BORDER_COLOR, margin_y="1rem"),
                rx.text("All systems operational. WebSockets connected.", color=TEXT_SECONDARY),
                width="100%",
                background_color=CARD_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="1.5rem"
            ),
            columns="2",
            spacing="6",
            width="100%"
        ),
        
        width="100%",
        max_width="1200px"
    )
