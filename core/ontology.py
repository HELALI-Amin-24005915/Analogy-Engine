"""
Triple-Layer Ontology: canonical taxonomy for analogy research.

This module is the single source of truth for ontological classification.
All agents (Scout, Matcher, Critic, Architect, Visionary) depend on these
definitions; this module depends on nothing (Clean Architecture core).

Use these constants in agent system prompts to enforce categorical consistency
and prevent cross-domain mapping hallucinations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.schema import AnalogyMapping, LogicalPropertyGraph

# ---------------------------------------------------------------------------
# 1. Ontological classification (the "clean" taxonomy)
# ---------------------------------------------------------------------------

ONTOLOGY_TAXONOMY = """
Every node extracted from any domain MUST be tagged with exactly one of these three labels:

- [STRUCTURE]: Physical components or entities (The "What"). Examples: Hardware, Cells, Servers, Neurons, Cables, Sensors, Databases.

- [FUNCTION]: Actions, processes, or logic (The "How"). Examples: Signal transmission, Learning, Data routing, Encoding, Decoding, Consensus, Replication.

- [ATTRIBUTE]: Performance metrics or abstract qualities (The "Cost/Value"). Examples: Latency, Energy, Scalability, Throughput, Reliability, Accuracy.
"""

# ---------------------------------------------------------------------------
# 2. Strict alignment rules (cross-domain mapping)
# ---------------------------------------------------------------------------

ALIGNMENT_RULES = """
Strict alignment rules for cross-domain mapping. Alignments are ONLY valid between identical labels:

- ALLOWED: [STRUCTURE] <-> [STRUCTURE]
- ALLOWED: [FUNCTION] <-> [FUNCTION]
- ALLOWED: [ATTRIBUTE] <-> [ATTRIBUTE]

- FORBIDDEN: [STRUCTURE] <-> [FUNCTION]   (e.g. do not map an Axon to a Multiplication)
- FORBIDDEN: [STRUCTURE] <-> [ATTRIBUTE]  (e.g. do not map a component to Energy consumption)
- FORBIDDEN: [FUNCTION] <-> [ATTRIBUTE]   (e.g. do not map a process to a metric)

Any mapping that violates these rules is a categorical mismatch and must be rejected.
"""

# ---------------------------------------------------------------------------
# 3. Polymorphism principle (align by role, not by name)
# ---------------------------------------------------------------------------

POLYMORPHISM_RULE = """
Polymorphism principle: Mappings are defined by ontological ROLE (STRUCTURE / FUNCTION / ATTRIBUTE), not by name or domain. The same "interface" (e.g. STRUCTURE) can have many "implementations" across domains (e.g. Neuron, Cable, Server). When matching nodes, align by type (same ontological label), not by lexical similarity. A STRUCTURE in domain A must map to a STRUCTURE in domain B that plays the same structural role, even if the concrete entities have different names.
"""

# ---------------------------------------------------------------------------
# 4. Signal & state integrity + decoupling (for Architect)
# ---------------------------------------------------------------------------

SIGNAL_STATE_AND_DECOUPLING = """
Signal & state integrity: When the analogy involves mapping discrete events (e.g. spikes, packets, tokens) to continuous states (e.g. conductance, voltage, rate), identify or propose an Interface Adapter (encoding/decoding logic) and mention it in the action plan.

Decoupling: The core analogy (business rules, transferable mechanisms) must remain independent of implementation details (specific hardware, I/O, or platform). Describe patterns so they can be applied regardless of the concrete technology.
"""

# ---------------------------------------------------------------------------
# 5. Combined block for agent prompts (Scout, Matcher, Critic)
# ---------------------------------------------------------------------------

ONTOLOGY_FULL = (
    ONTOLOGY_TAXONOMY.strip()
    + "\n\n"
    + ALIGNMENT_RULES.strip()
    + "\n\n"
    + POLYMORPHISM_RULE.strip()
)

# Valid node_type values for programmatic validation
VALID_NODE_TYPES = frozenset({"STRUCTURE", "FUNCTION", "ATTRIBUTE"})


def check_ontology_alignment(
    mapping: "AnalogyMapping",
    graph_a: "LogicalPropertyGraph",
    graph_b: "LogicalPropertyGraph",
) -> tuple[bool, list[str]]:
    """Check that every node_match aligns same ontological type (STRUCTURE/FUNCTION/ATTRIBUTE).

    Returns (True, []) if all pairs have matching node_type, else (False, list of issue strings).
    Missing nodes are skipped (no issue) to avoid false positives from ID mismatches.
    """
    from core.schema import AnalogyMapping, LogicalPropertyGraph

    if (
        not isinstance(mapping, AnalogyMapping)
        or not isinstance(graph_a, LogicalPropertyGraph)
        or not isinstance(graph_b, LogicalPropertyGraph)
    ):
        return (False, ["Invalid input types for ontology alignment check."])
    nodes_a = {n.id: n for n in graph_a.nodes}
    nodes_b = {n.id: n for n in graph_b.nodes}
    issues: list[str] = []
    for match in mapping.node_matches:
        node_a = nodes_a.get(match.source_id)
        node_b = nodes_b.get(match.target_id)
        if node_a is None or node_b is None:
            continue
        if node_a.node_type != node_b.node_type:
            issues.append(
                f"Categorical mismatch: [{node_a.node_type}] (source) mapped to "
                f"[{node_b.node_type}] (target) for source_id={match.source_id}, target_id={match.target_id}."
            )
    return (len(issues) == 0, issues)
