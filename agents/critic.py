"""
Critic Agent: Verification Filter.

Inputs AnalogyMapping, outputs ValidatedHypothesis using an AutoGen AssistantAgent.
"""

import asyncio
import json
import re
from typing import Any

from pydantic import ValidationError

from agents.base import BaseAgent
from core.schema import AnalogyMapping, ValidatedHypothesis

# Try autogen imports; fail at runtime if not installed
try:
    import autogen
except ImportError:  # pragma: no cover - import-time fallback
    autogen = None


CRITIC_SYSTEM_PROMPT = """You are the Critic. Your mission is to evaluate the logical consistency
of the AnalogyMapping provided by the Matcher.

You MUST REJECT (set is_consistent to false and list in issues) if ANY node_match has a categorical
mismatch: source_ontology and target_ontology must be identical (STRUCTURE<->STRUCTURE, FUNCTION<->FUNCTION,
ATTRIBUTE<->ATTRIBUTE only). If you see e.g. STRUCTURE mapped to FUNCTION, or source_ontology != target_ontology
for any pair, reject and report explicitly: "Categorical mismatch: [X] (source) mapped to [Y] (target) for node ...".

Check for:
1. Ontological alignment: For each node_match, source_ontology MUST equal target_ontology.
2. Structural Isomorphism: Do the connected nodes play the same role (e.g., both are causes or both are effects)?
3. Functional Plausibility: Does each mapping 'source -> target' make sense for a human?

OUTPUT FORMAT:
Return ONLY a JSON object with the following fields:
{
  "is_consistent": true or false,
  "issues": ["list of specific logical flaws or categorical mismatches"],
  "confidence": 0.0
}

Do NOT use markdown code fences. Return only the raw JSON object."""


class Critic(BaseAgent):
    """
    Verification filter: AnalogyMapping -> ValidatedHypothesis.

    Uses an AutoGen AssistantAgent to judge whether an analogy mapping is
    structurally and functionally plausible.
    """

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        """
        Initialize the Critic with injected LLM configuration.

        Args:
            llm_config: AutoGen llm_config (e.g. from core.config.build_llm_config()).
        """
        self._llm_config = llm_config or {}
        self._assistant: Any = None
        self._user_proxy: Any = None

        if autogen is not None:
            self._assistant = autogen.AssistantAgent(
                name="Critic",
                llm_config=self._llm_config,
                system_message=CRITIC_SYSTEM_PROMPT,
            )

            def _is_term(msg: dict[str, Any]) -> bool:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                content = (
                    msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                )
                return name == "Critic" and bool(content)

            self._user_proxy = autogen.UserProxyAgent(
                name="UserProxy_Critic",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                is_termination_msg=_is_term,
            )

    async def process(self, data: Any) -> ValidatedHypothesis:
        """
        Verify the logical consistency of an analogy mapping.

        Args:
            data: AnalogyMapping (or dict) from the Matcher.

        Returns:
            ValidatedHypothesis with consistency and issues.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Critic.")

        mapping = AnalogyMapping.model_validate(data)

        payload = mapping.model_dump()
        mapping_json = json.dumps(payload, indent=2)

        message = (
            "Evaluate the following AnalogyMapping for structural isomorphism and "
            "functional plausibility. Return ONLY a JSON object containing "
            "is_consistent, issues, and confidence.\n\n"
            f"{mapping_json}"
        )

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Critic":
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    return str(content) if content else "{}"
            return "{}"

        content = await asyncio.to_thread(_run_chat)
        return self._parse_response(content, mapping)

    def _parse_response(self, content: str, mapping: AnalogyMapping) -> ValidatedHypothesis:
        """Parse LLM response into a ValidatedHypothesis."""
        content = content.strip()

        # Default hypothesis if anything goes wrong
        fallback = ValidatedHypothesis(
            mapping=mapping,
            is_consistent=True,
            issues=["Critic failed to parse or validate response."],
            confidence=0.0,
            properties={"fallback": True},
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
            print(f"Critic JSON decode error: {exc}")
            print(f"Raw content (truncated): {content[:200]}...")
            return fallback

        if not isinstance(obj, dict):
            return fallback

        # Extract fields with safe defaults
        try:
            is_consistent = bool(obj.get("is_consistent", True))
            issues_raw = obj.get("issues", [])
            if not isinstance(issues_raw, list):
                issues = [str(issues_raw)]
            else:
                issues = [str(it) for it in issues_raw]
            confidence = float(obj.get("confidence", 0.0))
        except (TypeError, ValueError, ValidationError):  # pragma: no cover - defensive
            return fallback

        # Programmatic reinforcement: reject on categorical mismatch if source_ontology != target_ontology
        for i, match in enumerate(mapping.node_matches):
            src_ont = match.source_ontology
            tgt_ont = match.target_ontology
            if src_ont is not None and tgt_ont is not None and src_ont != tgt_ont:
                is_consistent = False
                issues.append(
                    f"Categorical mismatch: [{src_ont}] (source) mapped to [{tgt_ont}] (target) "
                    f"for match {i} (source_id={match.source_id}, target_id={match.target_id})."
                )

        return ValidatedHypothesis(
            mapping=mapping,
            is_consistent=is_consistent,
            issues=issues,
            confidence=confidence,
            properties={"critic_raw": obj},
        )
