import reflex as rx
from dashboard.components.sidebar import layout
from dashboard.state import GlobalState
from dashboard.styles import (
    CARD_BG,
    BORDER_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_PURPLE,
    ACCENT_CYAN,
)


def node_item(node: rx.Var[dict]) -> rx.Component:
    return rx.hstack(
        rx.icon("circle", size=12, color=ACCENT_CYAN),
        rx.text(node["id"], color=TEXT_PRIMARY),
        rx.spacer(),
        rx.text(node.get("category", "unknown"), color=TEXT_SECONDARY, font_size="sm"),
        width="100%",
        padding="0.5rem",
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
                    on_click=GlobalState.fetch_knowledge_graph,
                    color_scheme="purple",
                    variant="surface",
                ),
                width="100%",
                align_items="center",
                margin_bottom="1rem",
            ),
            rx.text(
                "Interactive visualization of contextual memories and entities. Click nodes to explore connections.",
                color=TEXT_SECONDARY,
                margin_bottom="1.5rem",
            ),
            rx.cond(
                GlobalState.knowledge_graph_nodes.length() > 0,
                rx.vstack(
                    rx.grid(
                        rx.card(
                            rx.vstack(
                                rx.text("Nodes", color=TEXT_SECONDARY),
                                rx.heading(
                                    rx.text(GlobalState.knowledge_graph_nodes.length()),
                                    size="4",
                                    color=ACCENT_CYAN,
                                ),
                            ),
                            background_color=CARD_BG,
                            border=f"1px solid {BORDER_COLOR}",
                            width="100%",
                        ),
                        rx.card(
                            rx.vstack(
                                rx.text("Edges", color=TEXT_SECONDARY),
                                rx.heading(
                                    rx.text(GlobalState.knowledge_graph_edges.length()),
                                    size="4",
                                    color=ACCENT_PURPLE,
                                ),
                            ),
                            background_color=CARD_BG,
                            border=f"1px solid {BORDER_COLOR}",
                            width="100%",
                        ),
                        rx.card(
                            rx.vstack(
                                rx.text("Regime", color=TEXT_SECONDARY),
                                rx.heading(
                                    GlobalState.scheduler_phase, size="4", color=TEXT_PRIMARY
                                ),
                            ),
                            background_color=CARD_BG,
                            border=f"1px solid {BORDER_COLOR}",
                            width="100%",
                        ),
                        columns="3",
                        width="100%",
                        gap="1rem",
                        margin_bottom="1rem",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("box", size=16),
                            rx.cond(GlobalState.graph_dimension == "3d", "2D View", "3D View"),
                            on_click=GlobalState.toggle_graph_dimension,
                            color_scheme="cyan",
                            variant="outline",
                        ),
                        rx.cond(
                            GlobalState.graph_dimension == "3d",
                            rx.text("Current: 2D", color=TEXT_SECONDARY, align="center"),
                            rx.text("Current: 3D", color=TEXT_SECONDARY, align="center"),
                        ),
                        width="100%",
                        margin_bottom="1rem",
                    ),
                    rx.box(
                        rx.plotly(data=GlobalState.knowledge_graph_figure),
                        width="100%",
                        height="600px",
                        border=f"1px solid {BORDER_COLOR}",
                        border_radius="12px",
                        overflow="hidden",
                    ),
                    width="100%",
                    spacing="4",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon("git-commit-horizontal", size=48, color=ACCENT_PURPLE),
                        rx.heading(
                            "Graph Engine Initializing",
                            size="5",
                            color=TEXT_PRIMARY,
                            margin_top="1rem",
                        ),
                        rx.text(
                            "Click 'Rebuild Graph' to load knowledge graph data.",
                            color=TEXT_SECONDARY,
                        ),
                        align_items="center",
                    ),
                    width="100%",
                    padding="6rem",
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="12px",
                    text_align="center",
                ),
            ),
            rx.cond(
                GlobalState.knowledge_graph_nodes.length() > 0,
                rx.box(
                    rx.vstack(
                        rx.heading(
                            "Recent Entities", size="5", color=TEXT_PRIMARY, margin_bottom="1rem"
                        ),
                        rx.foreach(
                            GlobalState.knowledge_graph_nodes,
                            node_item,
                        ),
                    ),
                    width="100%",
                    padding="2rem",
                    background_color=CARD_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="12px",
                    margin_top="1.5rem",
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="6",
            padding_bottom="4rem",
        )
    )
