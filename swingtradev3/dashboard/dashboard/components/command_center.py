import reflex as rx
from dashboard.state import GlobalState
from dashboard.components.pipeline_flow import pipeline_flow
from dashboard.styles import (
    CARD_BG,
    BORDER_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_GREEN,
    ACCENT_BLUE,
    ACCENT_CYAN,
    ACCENT_RED,
    ACCENT_GREEN_DIM,
    ACCENT_PURPLE,
    ACCENT_YELLOW,
)


def format_inr(value: float) -> str:
    """Format value as Indian Rupee with commas."""
    if value is None:
        return "₹0"
    prefix = "+" if value >= 0 else ""
    return f"{prefix}₹{value:,.0f}"


def status_badge(status: rx.Var) -> rx.Component:
    status_str = status.to(str).lower()
    color = rx.match(
        status_str,
        ("running", ACCENT_GREEN),
        ("idle", ACCENT_PURPLE),
        ("completed", ACCENT_CYAN),
        ("error", ACCENT_RED),
        TEXT_SECONDARY,
    )
    bg = rx.match(
        status_str,
        ("running", ACCENT_GREEN_DIM),
        ("idle", "rgba(168, 85, 247, 0.15)"),
        ("completed", "rgba(0, 212, 170, 0.15)"),
        ("error", "rgba(255, 68, 68, 0.15)"),
        BORDER_COLOR,
    )
    return rx.badge(
        rx.icon("circle", size=10, fill="currentColor", margin_right="4px"),
        status.to(str).upper(),
        color=color,
        background_color=bg,
        border_radius="full",
        padding="4px 10px",
        font_weight="bold",
        font_size="0.7rem",
    )


def agent_card(agent_name: rx.Var[str], state_agent: rx.Var[dict]) -> rx.Component:
    return rx.link(
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.text(agent_name, font_weight="600", size="3", color=TEXT_PRIMARY),
                    rx.text(
                        state_agent["last_event"],
                        color=TEXT_SECONDARY,
                        size="2",
                        max_width="280px",
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                status_badge(state_agent["status"]),
                align_items="center",
            ),
            animation=rx.cond(
                state_agent["status"].to(str) == "running",
                "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "none",
            ),
            border=f"1px solid {BORDER_COLOR}",
            border_radius="10px",
            background_color=CARD_BG,
            padding="1rem",
            margin_bottom="0.75rem",
            _hover={"background_color": "rgba(255,255,255,0.05)"},
        ),
        href="/activity",
        underline="none",
    )


def metric_card(
    title: str, value: str, icon_tag: str, color: str, subtext: str = ""
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon_tag, size=20, color=color),
                    padding="8px",
                    background_color=f"{color}15",
                    border_radius="8px",
                ),
                rx.text(title, color=TEXT_SECONDARY, size="2"),
                spacing="3",
                align_items="center",
            ),
            rx.text(value, font_weight="bold", size="6", color=TEXT_PRIMARY),
            rx.text(subtext, color=TEXT_SECONDARY, size="1") if subtext else rx.fragment(),
            align_items="start",
            spacing="2",
        ),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        background_color=CARD_BG,
        padding="1.25rem",
        flex="1",
        min_width="180px",
    )


def failed_events_banner() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.cond(
                GlobalState.failed_events_count > 0,
                rx.icon("triangle_alert", size=18, color=ACCENT_RED),
                rx.icon("check_check", size=18, color=ACCENT_GREEN),
            ),
            rx.text(
                f"{GlobalState.failed_events_count} failed event(s)",
                color=rx.cond(GlobalState.failed_events_count > 0, ACCENT_RED, TEXT_SECONDARY),
                font_weight="500",
            ),
            rx.spacer(),
            rx.link(
                rx.button("View", size="1", variant="outline", color_scheme="gray"),
                href="/failed-events",
                underline="none",
            ),
            spacing="3",
            align_items="center",
        ),
        background_color=rx.cond(
            GlobalState.failed_events_count > 0, "rgba(255, 68, 68, 0.1)", "rgba(16, 185, 129, 0.1)"
        ),
        border=f"1px solid {rx.cond(GlobalState.failed_events_count > 0, ACCENT_RED, ACCENT_GREEN)}",
        border_radius="8px",
        padding="1rem",
        margin_bottom="1.5rem",
    )


def next_task_display() -> rx.Component:
    return rx.cond(
        GlobalState.next_scheduled_task != "",
        rx.box(
            rx.hstack(
                rx.icon("clock", size=16, color=TEXT_SECONDARY),
                rx.text("Next:", color=TEXT_SECONDARY, size="2"),
                rx.text(
                    GlobalState.next_scheduled_task, color=TEXT_PRIMARY, size="2", font_weight="500"
                ),
                spacing="2",
                align_items="center",
            ),
            background_color=CARD_BG,
            border=f"1px solid {BORDER_COLOR}",
            border_radius="8px",
            padding="0.75rem 1rem",
        ),
        rx.box(
            rx.hstack(
                rx.icon("clock", size=16, color=TEXT_SECONDARY),
                rx.text("No upcoming tasks", color=TEXT_SECONDARY, size="2"),
                spacing="2",
                align_items="center",
            ),
            background_color=CARD_BG,
            border=f"1px solid {BORDER_COLOR}",
            border_radius="8px",
            padding="0.75rem 1rem",
        ),
    )


def command_center() -> rx.Component:
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading("Command Center", size="7", color=TEXT_PRIMARY),
            rx.spacer(),
            rx.hstack(
                rx.badge(
                    GlobalState.scheduler_phase.upper(),
                    color_scheme="purple",
                    size="2",
                    padding="6px 12px",
                ),
                next_task_display(),
                spacing="3",
                align_items="center",
            ),
            width="100%",
            align_items="center",
            margin_bottom="1.5rem",
            flex_wrap="wrap",
            gap="1rem",
        ),
        # Failed Events Banner
        failed_events_banner(),
        # Top Metrics Row
        rx.grid(
            metric_card(
                "Open Positions",
                GlobalState.portfolio_summary["open_positions_count"].to_string(),
                "briefcase",
                ACCENT_PURPLE,
                "Active trades",
            ),
            metric_card(
                "Total Invested",
                GlobalState.formatted_total_invested,
                "wallet",
                ACCENT_YELLOW,
                "Market value",
            ),
            metric_card(
                "Today's P&L",
                GlobalState.formatted_total_pnl,
                rx.cond(
                    GlobalState.portfolio_summary["total_pnl"].to(float) >= 0,
                    "trending_up",
                    "trending_down",
                ),
                GlobalState.pnl_color,
                "Realized + Unrealized",
            ),
            columns="4",
            gap="1rem",
            width="100%",
            margin_bottom="2rem",
        ),
        # Pipeline Flow
        rx.box(
            rx.hstack(
                rx.icon("git-branch", size=18, color=TEXT_PRIMARY),
                rx.text("Research Pipeline", size="4", font_weight="600", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.hstack(
                    rx.icon("zap", size=14, color=ACCENT_GREEN),
                    rx.text(
                        f"{GlobalState.running_agents_count} running",
                        color=ACCENT_GREEN,
                        font_weight="500",
                        size="2",
                    ),
                    spacing="1",
                    align_items="center",
                ),
                spacing="2",
                align_items="center",
                margin_bottom="1rem",
            ),
            pipeline_flow(),
            width="100%",
            margin_bottom="1rem",
        ),
        # Agent Activity & System Health
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("activity", size=18, color=TEXT_PRIMARY),
                        rx.text(
                            "Live Agent Activity", size="4", font_weight="600", color=TEXT_PRIMARY
                        ),
                        spacing="2",
                        margin_bottom="1rem",
                    ),
                    rx.divider(border_color=BORDER_COLOR),
                    rx.cond(
                        GlobalState.agent_activity.length() > 0,
                        rx.vstack(
                            rx.foreach(
                                GlobalState.agent_activity,
                                lambda item: agent_card(item[0], item[1]),
                            ),
                            spacing="0",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.icon("clock", size=32, color=TEXT_SECONDARY),
                                rx.text(
                                    "No active agents",
                                    color=TEXT_SECONDARY,
                                    size="3",
                                    margin_top="0.5rem",
                                ),
                                align_items="center",
                            ),
                            padding="2rem",
                            width="100%",
                        ),
                    ),
                    align_items="stretch",
                    spacing="1",
                ),
                width="100%",
                background_color=CARD_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="1.5rem",
            ),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("server", size=18, color=TEXT_PRIMARY),
                        rx.text("System Health", size="4", font_weight="600", color=TEXT_PRIMARY),
                        spacing="2",
                        margin_bottom="1rem",
                    ),
                    rx.divider(border_color=BORDER_COLOR),
                    rx.vstack(
                        rx.hstack(
                            rx.icon("check-circle", size=16, color=ACCENT_GREEN),
                            rx.text("API Gateway", color=TEXT_PRIMARY, size="3"),
                            rx.spacer(),
                            rx.text("Online", color=ACCENT_GREEN, size="2"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.icon("check-circle", size=16, color=ACCENT_GREEN),
                            rx.text("Event Bus", color=TEXT_PRIMARY, size="3"),
                            rx.spacer(),
                            rx.text("Active", color=ACCENT_GREEN, size="2"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.icon("check-circle", size=16, color=ACCENT_GREEN),
                            rx.text("Scheduler", color=TEXT_PRIMARY, size="3"),
                            rx.spacer(),
                            rx.text("Running", color=ACCENT_GREEN, size="2"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.icon("check-circle", size=16, color=ACCENT_GREEN),
                            rx.text("SSE Stream", color=TEXT_PRIMARY, size="3"),
                            rx.spacer(),
                            rx.text("Connected", color=ACCENT_GREEN, size="2"),
                            width="100%",
                        ),
                        spacing="3",
                        align_items="stretch",
                    ),
                    align_items="stretch",
                    spacing="1",
                ),
                width="100%",
                background_color=CARD_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="1.5rem",
            ),
            columns="2",
            gap="1.5rem",
            width="100%",
        ),
        width="100%",
        spacing="0",
        padding="2rem",
    )
