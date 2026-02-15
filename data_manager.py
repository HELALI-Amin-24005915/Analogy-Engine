"""
Static demo data for Analogy-Engine Archive/Demo Mode.

High-quality scientific analogy examples displayed when no Azure OpenAI
credentials are provided. Used for hot-swap UX: Demo vs Live mode.
"""

from core.schema import ActionPlan, AnalogyMapping, ResearchReport, ValidatedHypothesis

# High-quality scientific analogy examples (doctoral-level)
EXISTING_DATA: list[dict] = [
    {
        "input_query": "Biological neural networks (synaptic plasticity, STDP) | Memristor-based neuromorphic architectures",
        "summary": "Deep structural analogy between biological learning and neuromorphic hardware: synaptic plasticity and spike-timing-dependent plasticity (STDP) map to memristive conductance updates and analog computation with ultra-low energy. Transferable mechanisms include local learning rules and temporal coding.",
        "findings": [
            "Synaptic weights in biology correspond to memristor conductance; both exhibit non-volatile plasticity.",
            "STDP temporal windows align with pulse-width modulation schemes in resistive RAM.",
            "Biological dendritic integration has analogies in crossbar array summation.",
            "Energy per synaptic event in biology (~10 fJ) approaches memristive switching limits.",
        ],
        "recommendation": "Pursue hybrid architectures where biological principles (sparsity, event-driven computation) guide circuit design; validate with neuroscience benchmarks (e.g., MNIST, temporal tasks) and measure energy-delay product.",
        "action_plan": {
            "transferable_mechanisms": [
                "Local STDP-like update rules for memristor arrays",
                "Temporal coding schemes (rate vs. timing) for inference",
                "Sparse connectivity and pruning inspired by synaptic elimination",
            ],
            "technical_roadmap": [
                "Design memristor crossbar with programmable STDP window",
                "Implement spike encoding/decoding for sensor inputs",
                "Benchmark against biological accuracy and power budgets",
                "Integrate with digital co-processor for hybrid control",
            ],
            "key_metrics_to_track": [
                "Energy per synaptic operation (pJ/fJ)",
                "Classification accuracy on neuromorphic benchmarks",
                "Plasticity retention over cycles (endurance)",
            ],
            "potential_pitfalls": [
                "Device variability and drift; need calibration loops",
                "Limited dynamic range of analog weights",
                "Scaling to large networks without yield loss",
            ],
        },
        "confidence": 0.91,
        "stored_at": "2025-01-15T14:30:00Z",
        "sources": [
            "https://arxiv.org/abs/2104.13267",
            "https://www.nature.com/articles/s41598-021-94960-5",
            "https://ieeexplore.ieee.org/document/9360332",
        ],
    },
    {
        "input_query": "Blockchain (distributed ledger, consensus) | Medieval merchant ledgers and guild trust systems",
        "summary": "Blockchain technology re-instantates historical trust mechanisms: decentralized ledgers, witness-based consensus, and immutable records mirror medieval guild ledgers, notary practices, and communal verification. The analogy reveals that 'trustless' systems still rely on social and procedural trust, now encoded in protocol.",
        "findings": [
            "Consensus (PoW/PoS) parallels witness and guild seal verification in medieval trade.",
            "Immutable append-only chains resemble notarized ledger books and chained entries.",
            "Tokenization and smart contracts echo bills of exchange and conditional agreements.",
            "Sybil resistance in blockchain mirrors guild membership and reputation networks.",
        ],
        "recommendation": "Use the analogy to design governance and dispute-resolution layers; study historical failure modes (fraud, ledger splits) to anticipate blockchain edge cases. Emphasize human-in-the-loop for high-stakes decisions.",
        "action_plan": {
            "transferable_mechanisms": [
                "Multi-signature and threshold schemes inspired by guild co-signing",
                "Reputation and slashing derived from historical ostracism mechanisms",
                "Escrow and conditional release analogous to bills of exchange",
            ],
            "technical_roadmap": [
                "Map consensus rules to explicit trust assumptions and failure modes",
                "Design governance layers with clear upgrade and rollback paths",
                "Implement dispute resolution oracles with human arbitrators",
                "Document social and technical trust boundaries",
            ],
            "key_metrics_to_track": [
                "Time to finality and dispute resolution latency",
                "Governance participation and proposal throughput",
                "Incident response and fork/recovery procedures",
            ],
            "potential_pitfalls": [
                "Over-reliance on 'trustless' rhetoric; hidden trust in devs and clients",
                "Governance capture and plutocracy in token-weighted voting",
                "Regulatory mismatch with historical legal frameworks",
            ],
        },
        "confidence": 0.88,
        "stored_at": "2025-02-01T09:15:00Z",
        "sources": [
            "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2874536",
            "https://www.sciencedirect.com/science/article/pii/S0165176519302356",
        ],
    },
    {
        "input_query": "Natural ecosystems (resilience, redundancy, emergence) | Microservices and distributed systems",
        "summary": "Ecosystems and microservice architectures share principles of resilience through diversity, redundancy, and emergent behavior. Species niches and food webs map to service boundaries and dependency graphs; biodiversity and keystone species inform redundancy and critical path design; succession and invasion dynamics inform scaling and failure propagation.",
        "findings": [
            "Redundancy and diversity in species roles parallel multi-instance and multi-region deployments.",
            "Keystone species and critical services both require extra protection and monitoring.",
            "Cascading failures in ecosystems (e.g., extinction cascades) mirror dependency and blast-radius issues.",
            "Ecosystem succession and recovery inspire blue-green and canary deployment strategies.",
        ],
        "recommendation": "Adopt ecological metrics (diversity indices, resilience curves) for system design; use circuit breakers and bulkheads inspired by compartmentalization; design for graceful degradation and recovery rather than only prevention.",
        "action_plan": {
            "transferable_mechanisms": [
                "Circuit breakers and bulkheads as ecological compartmentalization",
                "Health checks and chaos engineering as 'stress tests' for ecosystem stability",
                "Auto-scaling and backpressure as predator-prey and carrying-capacity dynamics",
            ],
            "technical_roadmap": [
                "Map service dependency graph to ecological network analysis",
                "Define SLIs/SLOs with recovery time and diversity metrics",
                "Implement chaos experiments with controlled failure injection",
                "Review and iterate on blast radius and runbooks",
            ],
            "key_metrics_to_track": [
                "Service diversity and redundancy coverage",
                "Mean time to recovery (MTTR) and degradation curves",
                "Dependency depth and critical path exposure",
            ],
            "potential_pitfalls": [
                "Over-optimization for stability at the cost of innovation velocity",
                "Ignoring human and organizational factors in 'ecological' design",
                "Treating analogies as literal blueprints; domain differences matter",
            ],
        },
        "confidence": 0.89,
        "stored_at": "2025-02-10T16:45:00Z",
        "sources": [
            "https://arxiv.org/abs/1803.02796",
            "https://dl.acm.org/doi/10.1145/3098274.3098282",
        ],
    },
]


def get_existing_data() -> list[ResearchReport]:
    """
    Return the static list of demo analogy reports as ResearchReport instances.

    Used in Demo/Archive Mode when no Azure OpenAI API key is provided.
    """
    reports: list[ResearchReport] = []
    for raw in EXISTING_DATA:
        ap = raw["action_plan"]
        action_plan = ActionPlan(
            transferable_mechanisms=ap["transferable_mechanisms"],
            technical_roadmap=ap["technical_roadmap"],
            key_metrics_to_track=ap["key_metrics_to_track"],
            potential_pitfalls=ap["potential_pitfalls"],
        )
        hypothesis = ValidatedHypothesis(
            mapping=AnalogyMapping(
                graph_a_id="demo_a",
                graph_b_id="demo_b",
                node_matches=[],
                edge_mappings=[],
                score=raw["confidence"],
                explanation=raw["summary"],
                properties={},
            ),
            is_consistent=True,
            issues=[],
            confidence=raw["confidence"],
            properties={},
        )
        report = ResearchReport(
            hypothesis=hypothesis,
            summary=raw["summary"],
            findings=raw["findings"],
            recommendation=raw["recommendation"],
            action_plan=action_plan,
            sources=raw["sources"],
            input_query=raw["input_query"],
            properties={"stored_at": raw["stored_at"]},
        )
        reports.append(report)
    return reports
