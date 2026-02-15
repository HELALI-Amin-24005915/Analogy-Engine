"""
Visionary Agent: Suggests a far-removed source domain for a given target problem.

Given a target problem, outputs a 2-sentence description of a source domain
(nature, history, or another science) that shares the same logical structure.
"""

import asyncio
from typing import Any

from agents.base import BaseAgent

try:
    import autogen
except ImportError:
    autogen = None

VISIONARY_SYSTEM_PROMPT = """You are the Visionary. Given a target problem, suggest a
far-removed Source Domain (e.g., from nature, history, or a different science) that
shares the same underlying logical structure.

Frame the suggestion in terms of structures (entities, components), functions (processes, mechanisms), and attributes (metrics, qualities) where relevant, so that downstream analysis can align domains by ontological type.

Output exactly a 2-sentence description of this source domain. Write in plain prose,
no bullet points or JSON. The first sentence introduces the domain; the second
describes the key mechanism or structure that mirrors the target problem."""


class Visionary(BaseAgent):
    """
    Suggests an analogous source domain for a target problem.

    Input: problem description (str).
    Output: 2-sentence source domain description (str).
    """

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        """
        Initialize the Visionary with injected LLM configuration.

        Args:
            llm_config: AutoGen llm_config (e.g. from core.config.build_llm_config()).
        """
        self._llm_config = llm_config or {}
        self._assistant: Any = None
        self._user_proxy: Any = None
        if autogen is not None:
            self._assistant = autogen.AssistantAgent(
                name="Visionary",
                llm_config=self._llm_config,
                system_message=VISIONARY_SYSTEM_PROMPT,
            )

            def _is_term(msg: dict[str, Any]) -> bool:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                return name == "Visionary" and bool(
                    msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                )

            self._user_proxy = autogen.UserProxyAgent(
                name="UserProxy_Visionary",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                is_termination_msg=_is_term,
            )

    async def process(self, data: Any) -> str:
        """
        Suggest a source domain that shares the logical structure of the target problem.

        Args:
            data: Target problem or research topic (str).

        Returns:
            A 2-sentence description of the suggested source domain.
        """
        if autogen is None:
            raise RuntimeError("autogen is not installed; cannot run Visionary.")
        problem = str(data).strip()
        if not problem:
            return ""

        message = (
            "Given the following target problem or research topic, suggest a far-removed "
            "source domain (from nature, history, or another science) that shares the same "
            "underlying logical structure. Output exactly 2 sentences for this source domain.\n\n"
            f"Target problem: {problem}"
        )

        def _run_chat() -> str:
            self._user_proxy.initiate_chat(self._assistant, message=message)
            chat_key = list(self._user_proxy.chat_messages.keys())[0]
            messages = self._user_proxy.chat_messages[chat_key]
            for msg in messages:
                name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                if name == "Visionary":
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    return str(content).strip() if content else ""
            return ""

        return await asyncio.to_thread(_run_chat)
