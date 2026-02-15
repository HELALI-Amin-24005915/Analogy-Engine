"""
Scout Agent: Abstraction Filter.

Inputs raw text; outputs a structured LogicalPropertyGraph using an AutoGen
AssistantAgent. Every node is tagged with the Triple-Layer Ontology
(STRUCTURE, FUNCTION, or ATTRIBUTE); unknown node_type is normalized to STRUCTURE.
"""

import asyncio
import json
import re
from typing import Any

from pydantic import ValidationError

from agents.base import BaseAgent
from core.ontology import ONTOLOGY_TAXONOMY, VALID_NODE_TYPES
from core.schema import LogicalPropertyGraph

# Try autogen imports; fail at runtime if not installed
try:
    import autogen
except ImportError:
    autogen = None

SCOUT_SYSTEM_PROMPT = (
    "You are the Scout. Extract PURE LOGICAL STRUCTURES from text. "
    "Ignore grammatical fillers, pronouns (I, me, you, we), and literal verbs. "
    "NEVER extract human actors (I, me, person, user) as nodes. Replace them with their "
    "functional role (e.g. 'Agent', 'Observer', 'System_Controller'). "
    "Extract only HIGH-LEVEL LOGICAL CONCEPTS, ACTORS, and PROCESSES. "
    "Use substantive nouns for node labels (e.g. instead of 'I am searching for a solution', "
    "extract nodes like 'Subject' or 'Research_Process'). "
    "All node labels MUST be in PascalCase (e.g. 'InformationSharing' not 'information sharing'). "
    "\n\n"
    "TRIPLE-LAYER ONTOLOGY (mandatory): Every node MUST have node_type set to exactly one of: "
    "STRUCTURE, FUNCTION, or ATTRIBUTE. " + ONTOLOGY_TAXONOMY.strip() + "\n\n"
    "Output must be valid JSON matching the LogicalPropertyGraph schema: "
    '{"nodes": [{"id": "...", "label": "...", "node_type": "STRUCTURE" or "FUNCTION" or "ATTRIBUTE"}], '
    '"edges": [{"source": "node_id", "target": "node_id", "relation": "..."}]}. '
    "Return only the JSON object, no markdown or extra text."
)


class Scout(BaseAgent):
    """
    Abstraction filter: raw text -> LogicalPropertyGraph.

    Input: raw text (str) describing a domain. Output: LogicalPropertyGraph
    with nodes typed by the Triple-Layer Ontology (STRUCTURE, FUNCTION,
    ATTRIBUTE). Unknown or invalid node_type from the LLM is normalized to
    STRUCTURE. Uses an AutoGen AssistantAgent; LLM config is injected via
    constructor.
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
            def _is_term(msg: dict[str, Any]) -> bool:
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

        message = (
            "Extract the logical structure from the following text as JSON "
            "(LogicalPropertyGraph). Return only the JSON.\n\nText: "
        ) + text

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            # Use first reply from Scout (assistant) to get the extracted graph JSON
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Scout":
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    return str(content) if content else "{}"
            return "{}"

        content = await asyncio.to_thread(_run_chat)
        return self._parse_graph_response(content)

    @staticmethod
    def _to_pascal_case(s: str) -> str:
        """Convert a label to PascalCase.

        Args:
            s: Raw label string (e.g. 'information sharing' or 'some_label').

        Returns:
            PascalCase string (e.g. 'InformationSharing').
        """
        if not s or not s.strip():
            return s
        parts = re.sub(r"[_\s]+", " ", s.strip()).split()
        return "".join(p[:1].upper() + p[1:].lower() for p in parts if p)

    def _parse_graph_response(self, content: str) -> LogicalPropertyGraph:
        """Parse LLM response string into LogicalPropertyGraph.

        Strips markdown code fences if present. Node labels are converted to
        PascalCase. node_type is normalized to VALID_NODE_TYPES (STRUCTURE,
        FUNCTION, ATTRIBUTE); any other value is set to STRUCTURE.

        Args:
            content: Raw LLM response (JSON string, optionally wrapped in ```json).

        Returns:
            LogicalPropertyGraph with nodes and edges; empty graph on parse failure.
        """
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
            for node in obj.get("nodes", []):
                if isinstance(node, dict):
                    if "label" in node:
                        node["label"] = self._to_pascal_case(str(node["label"]))
                    # Normalize node_type to ontology: only STRUCTURE, FUNCTION, ATTRIBUTE
                    if node.get("node_type") not in VALID_NODE_TYPES:
                        node["node_type"] = "STRUCTURE"
            try:
                return LogicalPropertyGraph(**obj)
            except (ValidationError, TypeError):
                pass
        return LogicalPropertyGraph(nodes=[], edges=[])
