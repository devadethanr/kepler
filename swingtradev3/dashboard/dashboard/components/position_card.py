import reflex as rx
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_GREEN, ACCENT_RED, ACCENT_BLUE, ACCENT_PURPLE
)

def position_card(pos: rx.Var[dict]) -> rx.Component:
    pnl = pos["current_price"].to(float) - pos["entry_price"].to(float)
    pnl_abs = pnl * pos["quantity"].to(float)
    pnl_pct = (pnl / pos["entry_price"].to(float)) * 100
    
    is_positive = pnl >= 0
    pnl_color = rx.cond(is_positive, ACCENT_GREEN, ACCENT_RED)
    
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(pos["ticker"], font_weight="bold", size="5", color=TEXT_PRIMARY),
                    rx.badge(pos["sector"], color_scheme="blue", size="1"),
                    align_items="start",
                    spacing="1"
                ),
                rx.spacer(),
                rx.vstack(
                    rx.text(
                        rx.cond(is_positive, "+", ""),
                        "₹", ((pnl_abs.to(float) * 100).to(int).to(float) / 100).to_string(),
                        color=pnl_color,
                        font_weight="bold",
                        size="4"
                    ),
                    rx.text(
                        ((pnl_pct.to(float) * 100).to(int).to(float) / 100).to_string(), "%",
                        color=pnl_color,
                        size="2"
                    ),
                    align_items="end",
                    spacing="0"
                ),
                width="100%"
            ),
            rx.divider(border_color=BORDER_COLOR, margin_y="0.5rem"),
            rx.grid(
                rx.vstack(
                    rx.text("Qty", color=TEXT_SECONDARY, size="1"),
                    rx.text(pos["quantity"].to_string(), color=TEXT_PRIMARY, font_weight="semibold"),
                    align_items="start",
                    spacing="1"
                ),
                rx.vstack(
                    rx.text("Entry", color=TEXT_SECONDARY, size="1"),
                    rx.text("₹", pos["entry_price"].to_string(), color=TEXT_PRIMARY, font_weight="semibold"),
                    align_items="start",
                    spacing="1"
                ),
                rx.vstack(
                    rx.text("Current", color=TEXT_SECONDARY, size="1"),
                    rx.text("₹", pos["current_price"].to_string(), color=TEXT_PRIMARY, font_weight="semibold"),
                    align_items="start",
                    spacing="1"
                ),
                columns="3",
                spacing="4",
                width="100%"
            ),
            width="100%",
            spacing="2"
        ),
        background_color=CARD_BG,
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="1rem",
        transition="transform 0.2s ease-in-out",
        _hover={
            "transform": "translateY(-4px)",
            "border_color": ACCENT_BLUE,
        }
    )
