import reflex as rx
import httpx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState, FASTAPI_URL, API_KEY
from dashboard.styles import (
    CARD_BG,
    BORDER_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_RED,
    ACCENT_YELLOW,
    ACCENT_GREEN,
)


def failed_event_card(event_data: dict) -> rx.Component:
    """Display a single failed event with details."""
    handler_name = event_data.get("handler_name", "unknown")
    error_msg = event_data.get("error", "No error message")
    retry_count = event_data.get("retry_count", 0)
    max_retries = event_data.get("max_retries", 3)
    permanently_failed = event_data.get("permanently_failed", False)
    created_at = event_data.get("created_at", "")
    event_type = (
        event_data.get("event", {}).get("type", "unknown")
        if isinstance(event_data.get("event"), dict)
        else "unknown"
    )
    event_id = (
        event_data.get("event", {}).get("id", "")
        if isinstance(event_data.get("event"), dict)
        else ""
    )

    status_text = rx.cond(
        permanently_failed, "Permanently Failed", f"Retrying ({retry_count}/{max_retries})"
    )
    status_scheme = rx.cond(permanently_failed, "red", "yellow")

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("alert_triangle", color=ACCENT_RED, size=20),
                rx.heading(handler_name, size="6", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.badge(status_text, color_scheme=status_scheme, size="2"),
                width="100%",
                align_items="center",
            ),
            rx.text(f"Event Type: {event_type}", color=TEXT_SECONDARY, size="2"),
            rx.box(
                rx.text(error_msg, color=TEXT_PRIMARY, size="2", font_family="mono"),
                background_color="rgba(0,0,0,0.3)",
                padding="0.75rem",
                border_radius="6px",
                width="100%",
                margin_top="0.5rem",
            ),
            rx.hstack(
                rx.text(f"Created: {created_at}", color=TEXT_SECONDARY, size="1"),
                rx.spacer(),
                rx.button(
                    "Retry",
                    size="1",
                    variant="outline",
                    color_scheme="orange",
                    on_click=GlobalState.retry_failed_event(event_id),
                ),
                width="100%",
                margin_top="0.5rem",
            ),
            width="100%",
            spacing="2",
            padding="1rem",
            background_color=CARD_BG,
            border=BORDER_COLOR,
            border_width="1px",
            border_radius="8px",
        ),
        margin_bottom="1rem",
        width="100%",
    )


def failed_events() -> rx.Component:
    """Page displaying all failed events."""
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Failed Events", size="7", color=ACCENT_RED),
                rx.spacer(),
                rx.text("Event handlers that failed during execution", color=TEXT_SECONDARY),
                width="100%",
                align_items="center",
                margin_bottom="1rem",
            ),
            rx.cond(
                GlobalState.failed_events.length() > 0,
                rx.vstack(
                    rx.foreach(GlobalState.failed_events, lambda e: failed_event_card(e)),
                    width="100%",
                    spacing="0",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon("check", color=ACCENT_GREEN, size=48),
                        rx.heading("No Failed Events", size="5", color=ACCENT_GREEN),
                        rx.text("All event handlers are running smoothly", color=TEXT_SECONDARY),
                        align_items="center",
                        padding="3rem",
                        width="100%",
                    ),
                    background_color=CARD_BG,
                    border_radius="8px",
                ),
            ),
            width="100%",
            spacing="4",
            padding_bottom="4rem",
        )
    )
