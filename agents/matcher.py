"""
Matcher Agent: Transformation Filter.

Inputs Graph A & B, outputs AnalogyMapping (isomorphism search) using AutoGen.
"""

import asyncio
import json
import re
from typing import Any

from pydantic import ValidationError

from agents.base import BaseAgent
from core.schema import AnalogyMapping, LogicalPropertyGraph

# Try autogen imports; fail at runtime if not installed
try:
    import autogen
except ImportError:  # pragma: no cover - import-time fallback
    autogen = None


MATCHER_SYSTEM_PROMPT = """You are the Matcher. Your goal is to find structural
isomorphisms between two LogicalPropertyGraphs.

1. Analyze roles, not just names (e.g., if X causes Y in Graph A, and P causes
   Q in Graph B, then X mirrors P).
2. For each mapping, provide a concise 'reasoning' explaining the functional
   equivalence.
3. Provide a global 'explanation' summarizing the analogy.
4. Assign a confidence 'score' from 0.0 to 1.0.
5. If you receive 'critic_feedback' and a 'previous_mapping', use them to
   REFINE your analogy and fix the specific issues mentioned.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching the AnalogyMapping schema:
{
  "graph_a_id": "source_graph_id",
  "graph_b_id": "target_graph_id",
  "node_matches": [
    {
      "source_id": "id_from_A",
      "target_id": "id_from_B",
      "reasoning": "Both elements act as the driving force..."
    }
  ],
  "edge_mappings": [],
  "score": 0.95,
  "explanation": "The analogy holds because..."
}
IMPORTANT: Keep 'edge_mappings' as an empty list [] to ensure schema validation
passes. Do not attempt to map edges for now.
Do NOT output markdown code blocks (like ```json), just the raw JSON string.
"""


class Matcher(BaseAgent):
    """
    Transformation filter: two LogicalPropertyGraphs -> AnalogyMapping.

    Uses an AutoGen AssistantAgent to identify structural correspondences
    (nodes and edges) and provide reasoning and a global explanation.
    """

    def __init__(self, llm_config: dict[str, Any]) -> None:
        """
        Initialize the Matcher with injected LLM configuration.

        Args:
            llm_config: AutoGen llm_config (e.g. from core.config.build_llm_config()).
        """
        self._llm_config = llm_config
        self._assistant: Any = None
        self._user_proxy: Any = None

        if autogen is not None:
            self._assistant = autogen.AssistantAgent(
                name="Matcher",
                llm_config=llm_config,
                system_message=MATCHER_SYSTEM_PROMPT,
            )

            # Terminate after first reply from Matcher so we only parse one JSON response
            def _is_term(msg: dict[str, Any]) -> bool:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                content = (
                    msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                )
                return name == "Matcher" and bool(content)

            self._user_proxy = autogen.UserProxyAgent(
                name="UserProxy_Matcher",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                is_termination_msg=_is_term,
            )

    async def process(self, data: Any) -> AnalogyMapping:
        """
        Compute an analogy mapping between two graphs using an LLM.

        Args:
            data: A tuple/list (graph_a, graph_b) or a dict with keys
                  "graph_a" and "graph_b".

        Returns:
            AnalogyMapping describing node/edge correspondences and reasoning.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Matcher.")

        graph_a, graph_b = self._parse_input(data)

        # Serialize graphs (and optional refinement context) to JSON for the prompt
        payload: dict[str, Any] = {
            "graph_a": graph_a.model_dump(),
            "graph_b": graph_b.model_dump(),
        }
        # Optionally include previous mapping and critic feedback for refinement
        if isinstance(data, dict):
            if "previous_mapping" in data:
                payload["previous_mapping"] = data["previous_mapping"]
            if "critic_feedback" in data:
                payload["critic_feedback"] = data["critic_feedback"]
        input_payload = json.dumps(payload, indent=2)

        message = (
            "Find the analogy between these two logical property graphs. "
            "Return ONLY a JSON object matching the AnalogyMapping schema.\n\n"
            f"{input_payload}"
        )

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            # Use first reply from Matcher (assistant) to get the mapping JSON
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Matcher":
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    return str(content) if content else "{}"
            return "{}"

        content = await asyncio.to_thread(_run_chat)
        return self._parse_mapping_response(content, id_a="graph_a", id_b="graph_b")

    def _parse_input(self, data: Any) -> tuple[LogicalPropertyGraph, LogicalPropertyGraph]:
        """Extract (graph_a, graph_b) from pipeline input."""
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            raw_a, raw_b = data[0], data[1]
        elif isinstance(data, dict) and "graph_a" in data and "graph_b" in data:
            raw_a, raw_b = data["graph_a"], data["graph_b"]
        else:
            raise ValueError("Matcher expects (graph_a, graph_b) or dict with graph_a and graph_b.")

        graph_a = self._ensure_graph(raw_a)
        graph_b = self._ensure_graph(raw_b)
        return graph_a, graph_b

    def _ensure_graph(self, value: Any) -> LogicalPropertyGraph:
        """Normalize input to a LogicalPropertyGraph instance."""
        if isinstance(value, LogicalPropertyGraph):
            return value
        return LogicalPropertyGraph.model_validate(value)

    def _parse_mapping_response(self, content: str, id_a: str, id_b: str) -> AnalogyMapping:
        """Parse LLM response string into AnalogyMapping."""
        content = content.strip()

        # Fallback mapping if anything goes wrong
        fallback = AnalogyMapping(
            graph_a_id=id_a,
            graph_b_id=id_b,
            node_matches=[],
            edge_mappings=[],
            score=0.0,
            explanation="Failed to parse Matcher response.",
        )

        if not content:
            return fallback

        # Remove markdown code block if present
        if "```json" in content:
            content = re.sub(r"^.*?```json\s*", "", content, flags=re.DOTALL)
        if "```" in content:
            content = re.sub(r"\s*```.*$", "", content, flags=re.DOTALL)

        content = content.strip()
        if not content:
            return fallback

        try:
            obj = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            print(f"Matcher JSON decode error: {exc}")
            print(f"Raw content (truncated): {content[:200]}...")
            return fallback

        if not isinstance(obj, dict):
            return fallback

        # Ensure required identifiers are present
        obj.setdefault("graph_a_id", id_a)
        obj.setdefault("graph_b_id", id_b)

        # Safety sanitizer: edge_mappings must be list of (str, str) tuples
        if "edge_mappings" in obj and isinstance(obj["edge_mappings"], list):
            valid = all(
                isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(e, str) for e in x)
                for x in obj["edge_mappings"]
            )
            if not valid:
                obj["edge_mappings"] = []

        try:
            return AnalogyMapping.model_validate(obj)
        except (ValidationError, TypeError) as exc:  # pragma: no cover - defensive
            print(f"Matcher validation error: {exc}")
            print(f"Raw object: {obj}")
            return fallback
