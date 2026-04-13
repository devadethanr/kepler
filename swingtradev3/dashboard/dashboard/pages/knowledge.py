import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.styles import (
    CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, 
    ACCENT_PURPLE, ACCENT_CYAN
)

def knowledge() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Knowledge Graph", size="7", color=TEXT_PRIMARY),
                rx.spacer(),
                rx.button(
                    rx.icon("share-2", size=16), 
                    "Rebuild Graph", 
                    color_scheme="purple", 
                    variant="surface"
                ),
                width="100%",
                align_items="center",
                margin_bottom="2rem"
            ),
            
            rx.text("Visualization of contextual memories and entities.", color=TEXT_SECONDARY, margin_bottom="2rem"),
            
            rx.box(
                rx.vstack(
                    rx.icon("git-commit-horizontal", size=48, color=ACCENT_PURPLE),
                    rx.heading("Graph Engine Initializing", size="5", color=TEXT_PRIMARY, margin_top="1rem"),
                    rx.text("Connect the React Force Graph library here to visualize memories in 2D/3D space.", color=TEXT_SECONDARY),
                    align_items="center",
                ),
                width="100%",
                padding="6rem",
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
