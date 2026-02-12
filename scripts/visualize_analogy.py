"""
Visualize an analogy mapping: two graphs side-by-side with matched nodes
highlighted and dashed lines showing the isomorphism.

Uses a dark theme with gradient-like node colors for a polished, professional look.
"""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import ConnectionPatch, FancyBboxPatch

from core.schema import LogicalPropertyGraph, ResearchReport

# Dark-theme palette
_BG_COLOR = "#0E1117"
_SUBPLOT_BG = "#1A1F2E"
_TITLE_COLOR = "#E2E8F0"
_LABEL_COLOR = "#FAFAFA"
_EDGE_COLOR = "#4A5568"
_EDGE_LABEL_COLOR = "#9CA3AF"
_DEFAULT_NODE = "#2D3748"

# Vibrant matched-pair palette (colorblind-friendly)
_MATCH_PALETTE = [
    "#0078D4",  # blue
    "#50E6FF",  # cyan
    "#9B59B6",  # purple
    "#2ECC71",  # green
    "#E67E22",  # orange
    "#E74C3C",  # red
    "#F1C40F",  # yellow
    "#1ABC9C",  # teal
    "#E84393",  # pink
    "#6C5CE7",  # indigo
]


def draw_analogy(report: ResearchReport, output_path: str = "assets/analogy_map.png") -> None:
    """
    Draw Graph A and Graph B in two subplots, highlight matching nodes with
    the same color, and draw dashed lines between matched nodes across plots.

    Expects report.properties to contain "graph_a" and "graph_b" (model_dump
    of LogicalPropertyGraph) when graphs were attached by the caller.
    """
    graph_a_data = report.properties.get("graph_a")
    graph_b_data = report.properties.get("graph_b")
    if not graph_a_data or not graph_b_data:
        return
    graph_a = LogicalPropertyGraph.model_validate(graph_a_data)
    graph_b = LogicalPropertyGraph.model_validate(graph_b_data)

    mapping = report.hypothesis.mapping
    node_matches = mapping.node_matches

    # Build networkx digraphs
    G_a: nx.DiGraph[Any] = nx.DiGraph()
    for n in graph_a.nodes:
        G_a.add_node(n.id, label=n.label)
    for e in graph_a.edges:
        G_a.add_edge(e.source, e.target, relation=e.relation)

    G_b: nx.DiGraph[Any] = nx.DiGraph()
    for n in graph_b.nodes:
        G_b.add_node(n.id, label=n.label)
    for e in graph_b.edges:
        G_b.add_edge(e.source, e.target, relation=e.relation)

    if G_a.number_of_nodes() == 0 and G_b.number_of_nodes() == 0:
        return

    # Layouts
    pos_a = nx.spring_layout(G_a, seed=42, k=2.0) if G_a.number_of_nodes() else {}
    pos_b = nx.spring_layout(G_b, seed=42, k=2.0) if G_b.number_of_nodes() else {}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor(_BG_COLOR)

    # Colors for matched pairs
    match_color_by_source: dict[str, str] = {}
    match_color_by_target: dict[str, str] = {}
    for i, m in enumerate(node_matches):
        color = _MATCH_PALETTE[i % len(_MATCH_PALETTE)]
        match_color_by_source[m.source_id] = color
        match_color_by_target[m.target_id] = color

    node_colors_a = [match_color_by_source.get(n, _DEFAULT_NODE) for n in G_a.nodes()]
    node_colors_b = [match_color_by_target.get(n, _DEFAULT_NODE) for n in G_b.nodes()]

    for ax in (ax1, ax2):
        ax.set_facecolor(_SUBPLOT_BG)
        # Rounded subplot border
        border = FancyBboxPatch(
            (-1.35, -1.35),
            2.7,
            2.7,
            boxstyle="round,pad=0.05",
            edgecolor="#2D3748",
            facecolor="none",
            linewidth=1.5,
            transform=ax.transData,
        )
        ax.add_patch(border)

    # Draw graphs
    _draw_graph(G_a, pos_a, ax1, node_colors_a)
    ax1.set_title(
        "Source Domain (A)",
        color=_TITLE_COLOR,
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax1.axis("off")

    _draw_graph(G_b, pos_b, ax2, node_colors_b)
    ax2.set_title(
        "Target Domain (B)",
        color=_TITLE_COLOR,
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax2.axis("off")

    # Dashed lines between matched nodes across subplots
    for i, m in enumerate(node_matches):
        if m.source_id not in pos_a or m.target_id not in pos_b:
            continue
        xy_a = (float(pos_a[m.source_id][0]), float(pos_a[m.source_id][1]))
        xy_b = (float(pos_b[m.target_id][0]), float(pos_b[m.target_id][1]))
        color = _MATCH_PALETTE[i % len(_MATCH_PALETTE)]
        conn = ConnectionPatch(
            xy_a,
            xy_b,
            coordsA=ax1.transData,
            coordsB=ax2.transData,
            linestyle="--",
            linewidth=1.8,
            color=color,
            alpha=0.6,
        )
        fig.add_artist(conn)

    # Title & confidence badge
    confidence = report.hypothesis.confidence
    fig.suptitle(
        f"Analogy Map · Confidence {confidence:.0%}",
        color=_TITLE_COLOR,
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )

    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=_BG_COLOR)
    plt.close()


def _draw_graph(
    graph: "nx.DiGraph[Any]",
    pos: dict[str, Any],
    ax: Any,
    node_colors: list[str],
) -> None:
    """Draw nodes, edges, and labels for a single graph subplot."""
    if graph.number_of_nodes() == 0:
        return

    # Nodes with white edge for contrast
    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=1000,
        edgecolors="#FAFAFA",
        linewidths=1.5,
    )

    # Edges
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        arrows=True,
        arrowsize=18,
        edge_color=_EDGE_COLOR,
        width=1.5,
        style="solid",
        connectionstyle="arc3,rad=0.1",
    )

    # Node labels
    labels = {n: graph.nodes[n].get("label", n) for n in graph.nodes()}
    nx.draw_networkx_labels(
        graph,
        pos,
        labels,
        ax=ax,
        font_size=8,
        font_color=_LABEL_COLOR,
        font_weight="bold",
    )

    # Edge labels (relation type)
    edge_labels = nx.get_edge_attributes(graph, "relation")
    if edge_labels:
        nx.draw_networkx_edge_labels(
            graph,
            pos,
            edge_labels,
            ax=ax,
            font_size=6,
            font_color=_EDGE_LABEL_COLOR,
            bbox={"alpha": 0},
        )
