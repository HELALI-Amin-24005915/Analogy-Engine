"""
Scout Agent: Abstraction Filter.

Inputs raw text, outputs structured LogicalPropertyGraph using AutoGen AssistantAgent.
"""

import asyncio
import json
import re
from typing import Any

from core.schema import LogicalPropertyGraph
from pydantic import ValidationError

from agents.base import BaseAgent


# Try autogen imports; fail at runtime if not installed
try:
    import autogen
except ImportError:
    autogen = None  # type: ignore[assignment]

SCOUT_SYSTEM_PROMPT = (
    "You are the Scout. Extract PURE LOGICAL STRUCTURES from text. "
    "Output must be valid JSON matching the LogicalPropertyGraph schema: "
    '{"nodes": [{"id": "...", "label": "...", "node_type": "..."}], '
    '"edges": [{"source": "node_id", "target": "node_id", "relation": "..."}]}. '
    "Return only the JSON object, no markdown or extra text."
)


class Scout(BaseAgent):
    """
    Abstraction filter: raw text -> LogicalPropertyGraph.

    Uses an AutoGen AssistantAgent to extract logical structures.
    Configuration (LLM) is injected via constructor.
    """

    def __init__(self, llm_config: dict[str, Any]) -> None:
        """
        Initialize the Scout with injected LLM configuration.

        Args:
            llm_config: AutoGen llm_config (e.g. from core.config.build_llm_config()).
        """
        self._llm_config = llm_config
        self._assistant: Any = None
        self._user_proxy: Any = None
        if autogen is not None:
            self._assistant = autogen.AssistantAgent(
                name="Scout",
                llm_config=llm_config,
                system_message=SCOUT_SYSTEM_PROMPT,
            )
            # Terminate after first reply from Scout so we only parse one JSON response
            def _is_term(msg: dict) -> bool:
                return msg.get("name") == "Scout" and bool(msg.get("content"))

            self._user_proxy = autogen.UserProxyAgent(
                name="UserProxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                is_termination_msg=_is_term,
            )

    async def process(self, data: Any) -> LogicalPropertyGraph:
        """
        Extract a logical property graph from raw text.

        Args:
            data: Raw input text (str) to analyze.

        Returns:
            LogicalPropertyGraph extracted from the text.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Scout.")
        text = str(data).strip()
        if not text:
            return LogicalPropertyGraph(nodes=[], edges=[])

        message = f"Extract the logical structure from the following text as JSON (LogicalPropertyGraph). Return only the JSON.\n\nText: {text}"

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            # Use first reply from Scout (assistant) to get the extracted graph JSON
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Scout":
                    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                    return str(content) if content else "{}"
            return "{}"

        content = await asyncio.to_thread(_run_chat)
        return self._parse_graph_response(content)

    def _parse_graph_response(self, content: str) -> LogicalPropertyGraph:
        """Parse LLM response string into LogicalPropertyGraph."""
        content = content.strip()
        # Remove markdown code block if present
        if "```json" in content:
            content = re.sub(r"^.*?```json\s*", "", content)
        if "```" in content:
            content = re.sub(r"\s*```.*$", "", content)
        content = content.strip()
        if not content:
            return LogicalPropertyGraph(nodes=[], edges=[])
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            return LogicalPropertyGraph(nodes=[], edges=[])
        if isinstance(obj, dict) and ("nodes" in obj or "edges" in obj):
            try:
                return LogicalPropertyGraph(**obj)
            except (ValidationError, TypeError):
                pass
        return LogicalPropertyGraph(nodes=[], edges=[])
