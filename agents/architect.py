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
from core.ontology import SIGNAL_STATE_AND_DECOUPLING
from core.schema import ActionPlan, ResearchReport, ValidatedHypothesis

try:
    import autogen
except ImportError:  # pragma: no cover - import-time fallback
    autogen = None


# Senior R&D Engineer persona: translate patterns into executable engineering solutions.
ARCHITECT_SYSTEM_PROMPT = (
    """You are a **Senior R&D Engineer**.
Your goal is not just to find similarities, but to *transfer* technology.
You must translate structural patterns from the Source Domain into executable
engineering solutions for the Target Domain.

### DIRECTIVE:
Transform a technical `AnalogyMapping` into an actionable **Engineering Report**
with concrete, testable technical steps. Avoid vague language. Use precise
technical terms (e.g. "gradient descent", "distributed ledger", "API rate limiting",
"PID control loop", "feedback mechanism").

### CONCRETE EXAMPLES:
- If the Source uses "biological homeostasis", propose a "PID Control Loop" or
  "Feedback Mechanism" for the Target.
- If the Source uses "swarm coordination", propose "Consensus Algorithm" or
  "Distributed State Machine".
- If the Source uses "chemical catalysis", propose "Reusable Middleware" or
  "Adapter Pattern".

### INSTRUCTIONS:

1. **Summary & Findings**: Synthesize the analogy and explain mechanism translations.

2. **Recommendation**: Expert verdict on this engineering direction.

3. **Action Plan (Critical)**:
   - **transferable_mechanisms**: Specific algorithms, formulas, or logic to copy
     from Source to Target (e.g. "Implement exponential backoff like TCP congestion control").
   - **technical_roadmap**: Step-by-step implementation guide
     (e.g. "Step 1: Define the loss function...", "Step 2: Implement the feedback loop...").
   - **key_metrics_to_track**: KPIs to measure success (e.g. "latency p99", "throughput").
   - **potential_pitfalls**: Technical risks (e.g. "oscillation in feedback loop").

### SIGNAL & STATE INTEGRITY / DECOUPLING:
"""
    + "\n\n"
    + SIGNAL_STATE_AND_DECOUPLING.strip()
    + """

### OUTPUT FORMAT:
Return ONLY a raw JSON object (no markdown, no code blocks):
{
    "summary": "High-level synthesis of the analogy and its engineering value.",
    "findings": [
        "First mechanism translation with technical detail...",
        "Second mechanism translation...",
        "Concrete hypothesis or experiment suggestion..."
    ],
    "recommendation": "Expert verdict on this engineering direction.",
    "action_plan": {
        "transferable_mechanisms": ["Specific algorithm or logic to copy...", "..."],
        "technical_roadmap": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
        "key_metrics_to_track": ["Metric 1", "Metric 2"],
        "potential_pitfalls": ["Technical risk 1", "Technical risk 2"]
    }
}
"""
)


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
            "Synthesize the following ValidatedHypothesis into an Engineering Report. "
            "Include summary, findings, recommendation, and a complete action_plan "
            "with transferable_mechanisms, technical_roadmap, key_metrics_to_track, "
            "and potential_pitfalls. Return ONLY the JSON object (no markdown).\n\n"
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
            findings = [
                str(it).strip() for it in findings_raw if it is not None and str(it).strip()
            ]
        elif isinstance(findings_raw, str):
            findings = [s.strip() for s in findings_raw.replace("\n", ",").split(",") if s.strip()]
        else:
            findings = []

        action_plan_data = data.get("action_plan")
        if isinstance(action_plan_data, dict):
            try:
                action_plan = ActionPlan.model_validate(action_plan_data)
            except Exception:
                action_plan = ActionPlan()
        else:
            action_plan = ActionPlan()

        return ResearchReport(
            hypothesis=hypothesis,
            summary=summary,
            findings=findings if findings else ["No structured findings extracted."],
            recommendation=recommendation,
            action_plan=action_plan,
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
            action_plan=ActionPlan(),
            properties={"fallback": True, "fallback_triggered": True, "error": reason},
        )
