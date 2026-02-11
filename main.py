"""
Analogy-Engine: Pipe and Filter pipeline entry point.

Orchestrates the flow: Data -> Scout -> Matcher -> Critic -> Architect -> Result.
Configuration is injected; no hardcoded secrets.
"""

import asyncio

from agents import Architect, Critic, Matcher, Scout
from core.config import build_llm_config, get_config
from core.schema import ResearchReport


def run_pipeline(
    raw_text: str,
    *,
    scout: Scout | None = None,
    matcher: Matcher | None = None,
    critic: Critic | None = None,
    architect: Architect | None = None,
) -> ResearchReport:
    """
    Run the full pipeline: text -> Scout -> Matcher -> Critic -> Architect -> ResearchReport.

    Dependencies (agents) are injected; if not provided, they are created
    using config from the environment.

    Args:
        raw_text: Input scientific or logical text to analyze.
        scout: Optional Scout instance (else created with injected config).
        matcher: Optional Matcher instance.
        critic: Optional Critic instance.
        architect: Optional Architect instance.

    Returns:
        ResearchReport from the Architect (final filter).
    """
    llm_config = build_llm_config()

    if scout is None:
        scout = Scout(llm_config=llm_config)
    if matcher is None:
        matcher = Matcher(llm_config=llm_config)
    if critic is None:
        critic = Critic(llm_config=llm_config)
    if architect is None:
        architect = Architect(llm_config=llm_config)

    async def _run() -> ResearchReport:
        # Filter 1: Abstraction
        graph = await scout.process(raw_text)
        # Filter 2: Transformation (stub: same graph twice for single-text run)
        mapping = await matcher.process({"graph_a": graph, "graph_b": graph})
        # Filter 3: Verification
        hypothesis = await critic.process(mapping)
        # Filter 4: Synthesis
        report = await architect.process(hypothesis)
        return report

    return asyncio.run(_run())


async def run_dual_domain_test() -> None:
    """
    Run a dual-domain test:
    1. Scout analyzes a hydraulics text (source domain).
    2. Scout analyzes an electronics text (target domain).
    3. Matcher finds an analogy between the two graphs.
    4. Critic evaluates the mapping and can trigger a refinement.
    """
    llm_config = build_llm_config()
    scout = Scout(llm_config=llm_config)
    matcher = Matcher(llm_config=llm_config)
    critic = Critic(llm_config=llm_config)

    text_source = (
        "In a pipe, high pressure creates a flow of water, but a narrow section restricts it."
    )
    text_target = (
        "In a circuit, high voltage drives an electric current, while a resistor limits it."
    )

    # Filter 1: Abstraction for each domain
    graph_a = await scout.process(text_source)
    graph_b = await scout.process(text_target)

    # Filter 2: Transformation (analogy between two domains)
    mapping = await matcher.process({"graph_a": graph_a, "graph_b": graph_b})

    # Filter 3: Verification by Critic (first pass)
    hypothesis = await critic.process(mapping)

    # Simple 1-turn debate loop
    if (not hypothesis.is_consistent) or (hypothesis.confidence < 0.8):
        print("⚠️ CRITIC ISSUES:")
        for issue in hypothesis.issues:
            print(f"- {issue}")

        # Ask Matcher to refine the analogy using critic feedback
        refined_mapping = await matcher.process(
            {
                "graph_a": graph_a,
                "graph_b": graph_b,
                "previous_mapping": mapping.model_dump(),
                "critic_feedback": {
                    "is_consistent": hypothesis.is_consistent,
                    "issues": hypothesis.issues,
                    "confidence": hypothesis.confidence,
                },
            }
        )
        refined_hypothesis = await critic.process(refined_mapping)

        print("Final ValidatedHypothesis after refinement:")
        print(refined_hypothesis.model_dump_json(indent=2))
    else:
        print("Final ValidatedHypothesis (no refinement needed):")
        print(hypothesis.model_dump_json(indent=2))


def main() -> None:
    """Initialize config and run the dual-domain analogy test."""
    # Validate configuration (raises if AZURE_OPENAI_API_KEY or ENDPOINT missing)
    get_config()

    asyncio.run(run_dual_domain_test())


if __name__ == "__main__":
    main()
