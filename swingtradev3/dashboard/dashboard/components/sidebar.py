import reflex as rx

from dashboard.styles import CARD_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PURPLE

def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Kepler AI", size="6", color=TEXT_PRIMARY, margin_bottom="2rem"),
            rx.link(rx.hstack(rx.icon("home"), rx.text("Command Center")), href="/", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            rx.link(rx.hstack(rx.icon("pie-chart"), rx.text("Portfolio")), href="/portfolio", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            rx.link(rx.hstack(rx.icon("search"), rx.text("Research")), href="/research", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            rx.link(rx.hstack(rx.icon("circle-check"), rx.text("Approvals")), href="/approvals", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            rx.link(rx.hstack(rx.icon("share-2"), rx.text("Knowledge Graph")), href="/knowledge", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            rx.link(rx.hstack(rx.icon("activity"), rx.text("Agent Activity")), href="/activity", color=TEXT_SECONDARY, _hover={"color": ACCENT_PURPLE}),
            
            align_items="start",
            spacing="4"
        ),
        width="250px",
        height="100vh",
        background_color=CARD_BG,
        border_right=f"1px solid {BORDER_COLOR}",
        padding="2rem",
        position="fixed",
        left="0px",
        top="0px",
        z_index="5"
    )

def layout(page_content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            page_content,
            margin_left="250px",
            padding="2rem",
            width="calc(100vw - 250px)",
            min_height="100vh",
        ),
        align_items="start"
    )
