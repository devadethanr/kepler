"""Knowledge Graph visualization using Plotly + NetworkX."""

import plotly.graph_objects as go
import networkx as nx
from typing import List, Dict


def create_knowledge_graph_figure(
    nodes: List[Dict], edges: List[Dict], dim: int = 3, dark_theme: bool = True
) -> go.Figure:
    """Create a 2D or 3D network graph visualization."""
    G = nx.Graph()

    valid_nodes = set()
    for node in nodes:
        node_id = node.get("id", "")
        if node_id:
            G.add_node(node_id, group=node.get("group", "entity"))
            valid_nodes.add(node_id)

    for edge in edges:
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source and target and source in valid_nodes and target in valid_nodes:
            G.add_edge(source, target)

    if G.number_of_nodes() == 0:
        return _create_empty_figure(dark_theme)

    pos = nx.spring_layout(G, dim=dim, seed=42, k=0.5)

    bg_color = "#0d1117" if dark_theme else "white"
    text_color = "white" if dark_theme else "black"
    edge_color = "#374151" if dark_theme else "#888888"

    traces = []

    for e in G.edges():
        if e[0] not in pos or e[1] not in pos:
            continue
        x = [pos[e[0]][0], pos[e[1]][0], None]
        y = [pos[e[0]][1], pos[e[1]][1], None]
        if dim == 3:
            z = [pos[e[0]][2], pos[e[1]][2], None]
            traces.append(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="lines",
                    line=dict(color=edge_color, width=2),
                    hoverinfo="none",
                )
            )
        else:
            traces.append(
                go.Scatter(
                    x=x, y=y, mode="lines", line=dict(color=edge_color, width=2), hoverinfo="none"
                )
            )

    node_ids = list(G.nodes())
    x = [pos[n][0] for n in node_ids if n in pos]
    y = [pos[n][1] for n in node_ids if n in pos]

    colors = []
    for n in node_ids:
        if n not in pos:
            continue
        group = G.nodes[n].get("group", "")
        if group == "stock":
            colors.append("#00d4aa")
        elif group == "sector":
            colors.append("#a855f7")
        else:
            colors.append("#6b7280")

    if dim == 3:
        z = [pos[n][2] for n in node_ids if n in pos]
        traces.append(
            go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode="markers",
                marker=dict(size=15, color=colors, line=dict(width=1, color="white")),
                text=node_ids,
                hoverinfo="text",
            )
        )
    else:
        traces.append(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                marker=dict(size=15, color=colors, line=dict(width=1, color="white")),
                text=node_ids,
                hoverinfo="text",
            )
        )

    layout = go.Layout(
        title=dict(text="", x=0.5, font=dict(color=text_color, size=20)),
        showlegend=False,
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=text_color),
        margin=dict(l=0, r=0, b=0, t=40),
    )

    if dim == 3:
        layout.scene = dict(
            xaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            yaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            zaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            bgcolor=bg_color,
        )

    return go.Figure(data=traces, layout=layout)


def _create_empty_figure(dark: bool = True) -> go.Figure:
    """Create empty figure when no data."""
    bg = "#0d1117" if dark else "white"
    color = "white" if dark else "black"
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font=dict(color=color),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        annotations=[
            dict(
                text="No graph data available",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color=color),
            )
        ],
    )
    return fig
