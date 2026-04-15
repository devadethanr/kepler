import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState
from dashboard.styles import (
    CARD_BG,
    BORDER_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_GREEN,
    ACCENT_RED,
)


def simple_approval_card(approval: dict) -> rx.Component:
    ticker = approval.get("ticker", "—")
    score = approval.get("score", 0)
    stop_price = approval.get("stop_price", 0)
    target_price = approval.get("target_price", 0)

    return rx.box(
        rx.hstack(
            rx.heading(ticker, size="6", color=TEXT_PRIMARY),
            rx.badge(f"Stop: ₹{stop_price}", color_scheme="red", size="1"),
            rx.badge(f"Target: ₹{target_price}", color_scheme="green", size="1"),
            rx.spacer(),
            rx.text(f"Score: {score}", color=TEXT_SECONDARY, size="2"),
            width="100%",
            align_items="center",
        ),
        rx.hstack(
            rx.button(
                "✅ Approve",
                color_scheme="green",
                size="2",
                on_click=GlobalState.approve_trade(ticker),
            ),
            rx.button(
                "❌ Reject",
                color_scheme="red",
                size="2",
                variant="outline",
                on_click=GlobalState.reject_trade(ticker),
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
        margin_bottom="0.5rem",
    )


def simple_approved_card(approval: dict) -> rx.Component:
    ticker = approval.get("ticker", "—")
    approved = approval.get("approved", False)

    return rx.box(
        rx.hstack(
            rx.cond(
                approved,
                rx.badge("Approved", color_scheme="green", size="1"),
                rx.badge("Rejected", color_scheme="red", size="1"),
            ),
            rx.heading(ticker, size="5", color=TEXT_PRIMARY),
            rx.spacer(),
            width="100%",
            align_items="center",
        ),
        width="100%",
        spacing="2",
        padding="0.75rem",
        background_color=CARD_BG,
        border=BORDER_COLOR,
        border_width="1px",
        border_radius="6px",
        margin_bottom="0.5rem",
    )


def approvals() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Pending Approvals", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.badge(
                    f"{GlobalState.pending_approvals.length()} Pending",
                    color_scheme="blue",
                    size="3",
                ),
                rx.cond(
                    GlobalState.sse_connected,
                    rx.badge("Live", color_scheme="green", size="1"),
                    rx.badge("Connecting...", color_scheme="yellow", size="1"),
                ),
                width="100%",
                align_items="center",
                margin_bottom="1rem",
            ),
            rx.text(
                "Review and approve Deep Analyst trade recommendations.",
                color=TEXT_SECONDARY,
                margin_bottom="1rem",
            ),
            rx.cond(
                GlobalState.pending_approvals.length() > 0,
                rx.vstack(
                    rx.foreach(GlobalState.pending_approvals, lambda a: simple_approval_card(a)),
                    width="100%",
                    spacing="0",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon("circle_check", size=48, color=TEXT_SECONDARY),
                        rx.heading(
                            "All Caught Up", size="5", color=ACCENT_GREEN, margin_top="1rem"
                        ),
                        rx.text(
                            "No trade decisions waiting for your approval.",
                            color=TEXT_SECONDARY,
                        ),
                        align_items="center",
                    ),
                    width="100%",
                    padding="4rem",
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="12px",
                    text_align="center",
                    margin_bottom="2rem",
                ),
            ),
            rx.cond(
                GlobalState.approved_approvals.length() > 0,
                rx.box(
                    rx.heading(
                        "Recently Approved", size="5", color=TEXT_PRIMARY, margin_top="1rem"
                    ),
                    rx.vstack(
                        rx.foreach(
                            GlobalState.approved_approvals,
                            lambda a: simple_approved_card(a),
                        ),
                        width="100%",
                        spacing="0",
                    ),
                    width="100%",
                ),
                rx.box(),
            ),
            rx.cond(
                GlobalState.rejected_approvals.length() > 0,
                rx.box(
                    rx.heading(
                        "Recently Rejected", size="5", color=TEXT_PRIMARY, margin_top="1rem"
                    ),
                    rx.vstack(
                        rx.foreach(
                            GlobalState.rejected_approvals,
                            lambda a: simple_approved_card(a),
                        ),
                        width="100%",
                        spacing="0",
                    ),
                    width="100%",
                ),
                rx.box(),
            ),
            width="100%",
            spacing="4",
            padding_bottom="4rem",
        )
    )
