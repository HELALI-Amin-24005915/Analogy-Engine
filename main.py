"""
Analogy-Engine: Pipe and Filter pipeline entry point.

Orchestrates the flow: Data -> Scout -> Matcher -> Critic -> Architect -> Result.
Configuration is injected; no hardcoded secrets.
"""

import asyncio
from typing import Any

from core.config import build_llm_config, get_config
from core.schema import ResearchReport

from agents import Architect, Critic, Matcher, Scout


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


def main() -> None:
    """Initialize config, run pipeline with a test query, print result."""
    # Validate configuration (raises if AZURE_OPENAI_API_KEY or ENDPOINT missing)
    get_config()

    test_query = (
        "Analyze the logic of: 'In fluid dynamics, high pressure causes flow unless restricted.'"
    )
    report = run_pipeline(test_query)
    print("Pipeline result (ResearchReport):")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
