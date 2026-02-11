"""
Visualize an analogy mapping: two graphs side-by-side with matched nodes
highlighted and dashed lines showing the isomorphism.
"""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import ConnectionPatch

from core.schema import LogicalPropertyGraph, ResearchReport


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
    pos_a = nx.spring_layout(G_a, seed=42) if G_a.number_of_nodes() else {}
    pos_b = nx.spring_layout(G_b, seed=42) if G_b.number_of_nodes() else {}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

    # Colors for matched pairs (cycle through colormap)
    n_matches = max(len(node_matches), 1)
    cmap = plt.get_cmap("tab10")
    colors = cmap(np.linspace(0.0, 1.0, n_matches, endpoint=False))
    match_color_by_source = {m.source_id: colors[i] for i, m in enumerate(node_matches)}
    match_color_by_target = {m.target_id: colors[i] for i, m in enumerate(node_matches)}
    default_color = [0.85, 0.85, 0.85, 1.0]  # light gray

    node_colors_a = [match_color_by_source.get(n, default_color) for n in G_a.nodes()]
    node_colors_b = [match_color_by_target.get(n, default_color) for n in G_b.nodes()]

    # Draw graphs
    if G_a.number_of_nodes() > 0:
        nx.draw_networkx_nodes(G_a, pos_a, ax=ax1, node_color=node_colors_a, node_size=800)
        nx.draw_networkx_edges(G_a, pos_a, ax=ax1, arrows=True, arrowsize=15)
        labels_a = {n: G_a.nodes[n].get("label", n) for n in G_a.nodes()}
        nx.draw_networkx_labels(G_a, pos_a, labels_a, ax=ax1, font_size=8)
    ax1.set_title("Graph A (Source)")
    ax1.axis("off")

    if G_b.number_of_nodes() > 0:
        nx.draw_networkx_nodes(G_b, pos_b, ax=ax2, node_color=node_colors_b, node_size=800)
        nx.draw_networkx_edges(G_b, pos_b, ax=ax2, arrows=True, arrowsize=15)
        labels_b = {n: G_b.nodes[n].get("label", n) for n in G_b.nodes()}
        nx.draw_networkx_labels(G_b, pos_b, labels_b, ax=ax2, font_size=8)
    ax2.set_title("Graph B (Target)")
    ax2.axis("off")

    # Dashed lines between matched nodes across subplots
    for i, m in enumerate(node_matches):
        if m.source_id not in pos_a or m.target_id not in pos_b:
            continue
        xy_a = (float(pos_a[m.source_id][0]), float(pos_a[m.source_id][1]))
        xy_b = (float(pos_b[m.target_id][0]), float(pos_b[m.target_id][1]))
        conn = ConnectionPatch(
            xy_a,
            xy_b,
            coordsA=ax1.transData,
            coordsB=ax2.transData,
            linestyle="--",
            color=colors[i],
            alpha=0.7,
        )
        fig.add_artist(conn)

    plt.tight_layout()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
