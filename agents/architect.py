"""
Architect Agent: Synthesis Filter.

Inputs ValidatedHypothesis, outputs ResearchReport using an AutoGen AssistantAgent.
"""

import asyncio
import json
import re
from typing import Any

from agents.base import BaseAgent
from core.schema import ResearchReport, ValidatedHypothesis

# Try autogen imports; fail at runtime if not installed
try:
    import autogen
except ImportError:  # pragma: no cover - import-time fallback
    autogen = None


ARCHITECT_SYSTEM_PROMPT = """You are the Architect. Your mission is to synthesize the results
of an analogy research process.

Input: A ValidatedHypothesis (containing the analogy mapping and critic's issues).
Output: A JSON object with summary, findings, and recommendation.

Tasks:
1. 'summary': Write a clear, pedagogical paragraph explaining the analogy
   (e.g., 'X is like Y because...').
2. 'findings': List the strong points where the analogy works perfectly.
3. 'recommendation': Provide a final verdict on whether this analogy
   is useful for teaching.

Format: Return ONLY a JSON object with these fields:
{
  "summary": "...",
  "findings": ["...", "..."],
  "recommendation": "..."
}
Do NOT use markdown code fences. Return only the raw JSON object."""


class Architect(BaseAgent):
    """
    Synthesis filter: ValidatedHypothesis -> ResearchReport.

    Uses an AutoGen AssistantAgent to turn the validated hypothesis
    into a readable research report (summary, findings, recommendation).
    """

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        """
        Initialize the Architect with injected LLM configuration.

        Args:
            llm_config: AutoGen llm_config (e.g. from core.config.build_llm_config()).
        """
        self._llm_config = llm_config or {}
        self._assistant: Any = None
        self._user_proxy: Any = None

        if autogen is not None:
            self._assistant = autogen.AssistantAgent(
                name="Architect",
                llm_config=self._llm_config,
                system_message=ARCHITECT_SYSTEM_PROMPT,
            )

            def _is_term(msg: dict[str, Any]) -> bool:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                content = (
                    msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                )
                return name == "Architect" and bool(content)

            self._user_proxy = autogen.UserProxyAgent(
                name="UserProxy_Architect",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                is_termination_msg=_is_term,
            )

    async def process(self, data: Any) -> ResearchReport:
        """
        Produce a research report from a validated hypothesis.

        Args:
            data: ValidatedHypothesis (or dict) from the Critic.

        Returns:
            ResearchReport with summary, findings, and recommendation.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Architect.")

        hypothesis = ValidatedHypothesis.model_validate(data)

        payload = hypothesis.model_dump()
        hypothesis_json = json.dumps(payload, indent=2)

        message = (
            "Synthesize the following ValidatedHypothesis into a research report. "
            "Return ONLY a JSON object with 'summary', 'findings', and 'recommendation'.\n\n"
            f"{hypothesis_json}"
        )

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Architect":
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    return str(content) if content else "{}"
            return "{}"

        content = await asyncio.to_thread(_run_chat)
        return self._parse_response(content, hypothesis)

    def _parse_response(self, content: str, hypothesis: ValidatedHypothesis) -> ResearchReport:
        """Parse LLM response into a ResearchReport."""
        content = content.strip()

        fallback = ResearchReport(
            hypothesis=hypothesis,
            summary="",
            findings=[],
            recommendation="",
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
            print(f"Architect JSON decode error: {exc}")
            print(f"Raw content (truncated): {content[:200]}...")
            return fallback

        if not isinstance(obj, dict):
            return fallback

        summary = str(obj.get("summary", "") or "")
        recommendation = str(obj.get("recommendation", "") or "")
        findings_raw = obj.get("findings", [])
        if not isinstance(findings_raw, list):
            findings = [str(findings_raw)] if findings_raw else []
        else:
            findings = [str(it) for it in findings_raw]

        return ResearchReport(
            hypothesis=hypothesis,
            summary=summary,
            findings=findings,
            recommendation=recommendation,
            properties={"architect_raw": obj},
        )
