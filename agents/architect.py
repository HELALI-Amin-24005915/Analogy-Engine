"""
Architect Agent: Research Synthesis.

Transforms a validated analogy mapping into a comprehensive research report,
translating abstract connections into concrete scientific or engineering insights.
"""

import asyncio
import json
import re
from typing import Any

from agents.base import BaseAgent
from core.schema import ResearchReport, ValidatedHypothesis

try:
    import autogen
except ImportError:  # pragma: no cover - import-time fallback
    autogen = None


# Prompt designed to force "translation" of mechanisms rather than mere comparison.
ARCHITECT_SYSTEM_PROMPT = """You are the **Chief Research Architect**.
Your goal is to transform a technical `AnalogyMapping` into a strategic, pedagogical, and actionable **Research Report**.

The researcher has found a structural link between a Source Domain and a Target Problem.
You must explain **how** the mechanisms of the Source can solve the Problem of the Target.

### INSTRUCTIONS:

1.  **Deep Insight**:
    - Explain *why* the Source Domain offers a relevant solution to the Target.
    - Go beyond surface similarities. Identify the core principle (e.g., "Decentralized regulation," "Structural redundancy").

2.  **Translation of Mechanisms (Crucial)**:
    - Do not just list the node matches. **Translate the process**.
    - Example: If the Scout found 'Cleaner Fish' (Source) matches 'Maintenance Bots' (Target), explain: *"Just as cleaner fish autonomously remove parasites without harming the host, maintenance bots could use specific recognition patterns to target rust without stopping the assembly line."*

3.  **Actionable Findings**:
    - Formulate concrete discoveries.
    - Suggest a specific new angle of research or a hypothesis to test based on the analogy.

4.  **Scientific Recommendation**:
    - Provide an expert opinion on the validity and potential of this research avenue.

### OUTPUT FORMAT:
You must return ONLY a raw JSON object (no markdown formatting, no code blocks) with the following structure:
{
    "summary": "A high-level synthesis of the analogy and its value.",
    "findings": [
        "Detailed paragraph explaining the first mechanism translation...",
        "Detailed paragraph explaining the second mechanism translation...",
        "A concrete hypothesis or experiment suggestion..."
    ],
    "recommendation": "Final expert verdict on this research direction."
}
"""


class Architect(BaseAgent):
    """
    Architect Agent using AutoGen to synthesize research reports.
    """

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        """
        Initialize the Architect agent.

        Args:
            llm_config: Configuration for the LLM (e.g. from core.config.build_llm_config()).
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
        Synthesize a ResearchReport from a ValidatedHypothesis (or dict).

        Args:
            data: ValidatedHypothesis or dict from the Critic.

        Returns:
            ResearchReport with summary, findings, and recommendation.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Architect.")

        hypothesis = ValidatedHypothesis.model_validate(data)

        context_data = {
            "mapping": hypothesis.mapping.model_dump(),
            "critic_confidence": hypothesis.confidence,
            "critic_issues": hypothesis.issues,
            "is_consistent": hypothesis.is_consistent,
        }
        prompt = (
            "Synthesize the following ValidatedHypothesis into a research report. "
            "Apply Deep Insight, Translation of Mechanisms, Actionable Findings, and Scientific Recommendation. "
            "Return ONLY the JSON object (no markdown).\n\n"
            f"{json.dumps(context_data, indent=2)}"
        )

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=prompt)
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
        """
        Extract JSON from the LLM response and build ResearchReport.
        Robust to markdown, leading/trailing text, and malformed JSON.
        """
        content = (content or "").strip()
        if not content:
            return self._create_fallback_report(hypothesis, "No response from LLM.")

        # Remove markdown code blocks
        cleaned_text = re.sub(r"```json\s*", "", content, flags=re.DOTALL)
        cleaned_text = re.sub(r"```", "", cleaned_text)
        cleaned_text = cleaned_text.strip()

        # Extract first balanced {...} block (handles nested braces in strings)
        start = cleaned_text.find("{")
        if start < 0:
            return self._create_fallback_report(hypothesis, "No JSON object found.")
        depth = 0
        in_string = False
        escape = False
        quote_char = ""
        i = start
        while i < len(cleaned_text):
            c = cleaned_text[i]
            if escape:
                escape = False
                i += 1
                continue
            if in_string and c == "\\":
                escape = True
                i += 1
                continue
            if not in_string:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        json_str = cleaned_text[start : i + 1]
                        break
                elif c in ("'", '"'):
                    in_string = True
                    quote_char = c
            elif c == quote_char:
                in_string = False
            i += 1
        else:
            json_str = cleaned_text[start:]

        # Clean common LLM quirks
        json_str = (
            json_str.replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u00a0", " ")
        )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return self._create_fallback_report(hypothesis, f"JSON decode error: {e}")

        if not isinstance(data, dict):
            return self._create_fallback_report(hypothesis, "Response is not a JSON object.")

        summary = str(data.get("summary") or "").strip() or "Summary generation failed."
        recommendation = (
            str(data.get("recommendation") or "").strip() or "No recommendation provided."
        )
        findings_raw = data.get("findings", [])
        if isinstance(findings_raw, list):
            findings = [str(it).strip() for it in findings_raw if it is not None and str(it).strip()]
        elif isinstance(findings_raw, str):
            findings = [
                s.strip()
                for s in findings_raw.replace("\n", ",").split(",")
                if s.strip()
            ]
        else:
            findings = []

        return ResearchReport(
            hypothesis=hypothesis,
            summary=summary,
            findings=findings if findings else ["No structured findings extracted."],
            recommendation=recommendation,
            properties={"architect_raw": data},
        )

    def _create_fallback_report(
        self, hypothesis: ValidatedHypothesis, reason: str
    ) -> ResearchReport:
        """Create a safe fallback report if generation or parsing fails."""
        return ResearchReport(
            hypothesis=hypothesis,
            summary=f"Automated synthesis failed. ({reason})",
            findings=[
                "The system could not parse the Architect's response.",
                "Please review the raw logs or the Critic's evaluation directly.",
            ],
            recommendation="Manual review required.",
            properties={"fallback": True, "fallback_triggered": True, "error": reason},
        )
