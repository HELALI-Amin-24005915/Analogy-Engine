"""
Abstract base for pipeline filters (Pipe and Filter pattern).

Each agent is a Filter with a single responsibility and communicates
only via Pydantic data contracts.

Architectural constraint: All agents must respect the Triple-Layer Ontology
defined in core.ontology (STRUCTURE, FUNCTION, ATTRIBUTE). Cross-domain
alignment is only valid between identical labels: STRUCTURE<->STRUCTURE,
FUNCTION<->FUNCTION, ATTRIBUTE<->ATTRIBUTE.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents (filters).

    Input/Output contract: each agent receives data (from the previous filter or
    app) and returns a Pydantic model for the next stage. No shared internal
    state; configuration is injected via constructor. All concrete agents
    (Scout, Matcher, Critic, Architect, Visionary) respect the Triple-Layer
    Ontology defined in core.ontology (STRUCTURE, FUNCTION, ATTRIBUTE).
    """

    @abstractmethod
    async def process(self, data: Any) -> Any:
        """
        Process input data and return the result for the next filter.

        Args:
            data: Input conforming to the contract of the previous filter
                (e.g. str for Scout, dict with graph_a/graph_b for Matcher).

        Returns:
            Output conforming to this filter's contract (Pydantic model:
            LogicalPropertyGraph, AnalogyMapping, ValidatedHypothesis,
            ResearchReport, or str for Visionary).
        """
        ...
