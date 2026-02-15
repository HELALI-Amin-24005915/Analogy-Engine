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

    Agents receive input data and return output data; no shared internal state.
    Configuration is injected via constructor.
    """

    @abstractmethod
    async def process(self, data: Any) -> Any:
        """
        Process input data and return the result for the next filter.

        Args:
            data: Input conforming to the contract of the previous filter.

        Returns:
            Output conforming to this filter's contract (Pydantic model).
        """
        ...
