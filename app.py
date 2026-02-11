"""
Analogy-Engine: AI Research Workbench — Streamlit UI.

Run with: streamlit run app.py
"""

import asyncio
import contextlib
import queue
import sys
import threading
from pathlib import Path
from typing import Any

import streamlit as st

from agents import Architect, Critic, Librarian, Matcher, Scout, Visionary
from core.config import build_llm_config, get_config
from core.schema import ResearchReport
from scripts.visualize_analogy import draw_analogy

try:
    from streamlit.runtime.scriptrunner_utils.script_run_context import (
        add_script_run_ctx,
        get_script_run_ctx,
    )
except ImportError:
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
    except ImportError:
        get_script_run_ctx = None  # type: ignore[assignment]
        add_script_run_ctx = None  # type: ignore[assignment]


class QueueLogWriter:
    """Writes to a queue (for later display) and echoes to terminal. No Streamlit calls."""

    def __init__(self, log_queue: "queue.Queue[str]") -> None:
        self._queue = log_queue

    def write(self, s: str) -> int:
        if s:
            self._queue.put(s)
        out = sys.stdout
        if out is not None:
            out.write(s)
        return len(s)

    def flush(self) -> None:
        if sys.stdout is not None:
            sys.stdout.flush()


# Default domain texts (Hydraulics / Electronics example)
DEFAULT_SOURCE = (
    "In a pipe, high pressure creates a flow of water, but a narrow section restricts it."
)
DEFAULT_TARGET = (
    "In a circuit, high voltage drives an electric current, while a resistor limits it."
)

# Session state keys
KEY_ACTIVE_REPORT = "active_report"  # dict (model_dump) or None


def init_session_state() -> None:
    if KEY_ACTIVE_REPORT not in st.session_state:
        st.session_state[KEY_ACTIVE_REPORT] = None


def _drain_and_show(log_queue: "queue.Queue[str]", log_placeholder: Any, buffer: list[str]) -> None:
    """Drain log_queue into buffer and update the Streamlit placeholder (main thread only)."""
    try:
        while True:
            buffer.append(log_queue.get_nowait())
    except queue.Empty:
        pass
    if buffer and log_placeholder is not None:
        log_placeholder.code("".join(buffer), language="text")


def run_pipeline(
    text_source: str,
    text_target: str,
    log_placeholder: Any | None = None,
    log_queue: "queue.Queue[str] | None" = None,
) -> None:
    """Run Scout -> Matcher -> Critic (optional refine) -> Architect, then save and store.
    When log_placeholder and log_queue are set, stdout is captured to the queue and the
    placeholder is updated from the main thread after each step (no ScriptRunContext).
    """
    get_config()
    llm_config = build_llm_config()
    scout = Scout(llm_config=llm_config)
    matcher = Matcher(llm_config=llm_config)
    critic = Critic(llm_config=llm_config)
    architect = Architect(llm_config=llm_config)
    librarian = Librarian()

    use_queue = log_placeholder is not None and log_queue is not None
    if use_queue and log_queue is not None:
        writer = QueueLogWriter(log_queue)
        stdout_ctx: contextlib.AbstractContextManager[Any] = contextlib.redirect_stdout(writer)
        stderr_ctx: contextlib.AbstractContextManager[Any] = contextlib.redirect_stderr(writer)
    else:
        stdout_ctx = contextlib.nullcontext()
        stderr_ctx = contextlib.nullcontext()

    log_buffer: list[str] = []

    with stdout_ctx, stderr_ctx:
        with st.status("Running analysis...", expanded=True) as status:
            status.update(label="Scouting...", state="running")
            graph_a = asyncio.run(scout.process(text_source))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            graph_b = asyncio.run(scout.process(text_target))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            status.update(label="Matching...", state="running")
            mapping = asyncio.run(matcher.process({"graph_a": graph_a, "graph_b": graph_b}))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            status.update(label="Critiquing...", state="running")
            hypothesis = asyncio.run(critic.process(mapping))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            if (not hypothesis.is_consistent) or (hypothesis.confidence < 0.8):
                refined_mapping = asyncio.run(
                    matcher.process(
                        {
                            "graph_a": graph_a,
                            "graph_b": graph_b,
                            "previous_mapping": mapping.model_dump(),
                            "critic_feedback": {
                                "is_consistent": hypothesis.is_consistent,
                                "issues": hypothesis.issues,
                                "confidence": hypothesis.confidence,
                            },
                        }
                    )
                )
                final_hypothesis = asyncio.run(critic.process(refined_mapping))
                if use_queue and log_queue is not None:
                    _drain_and_show(log_queue, log_placeholder, log_buffer)
            else:
                final_hypothesis = hypothesis

            status.update(label="Synthesizing...", state="running")
            report = asyncio.run(architect.process(final_hypothesis))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

    report.properties["graph_a"] = graph_a.model_dump()
    report.properties["graph_b"] = graph_b.model_dump()
    draw_analogy(report, output_path="assets/maps/current_display.png")
    librarian.store_report(report)
    st.session_state[KEY_ACTIVE_REPORT] = report.model_dump(mode="json")


def main() -> None:
    st.set_page_config(
        page_title="Analogy-Engine",
        page_icon="",
        layout="wide",
    )
    init_session_state()

    try:
        get_config()
    except Exception as e:
        st.error(f"Configuration error: {e}. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT.")
        st.stop()

    librarian = Librarian()
    all_reports = librarian.get_all_reports()
    all_reports = list(reversed(all_reports))  # most recent first

    with st.sidebar:
        st.title("Knowledge Base")
        st.metric("Total Reports", len(all_reports))
        st.divider()
        if all_reports:
            st.caption("Cliquez sur un rapport pour l'afficher.")
            for i, (report, meta) in enumerate(all_reports):
                stored = meta.stored_at
                ts = (
                    stored.strftime("%Y-%m-%d %H:%M")
                    if hasattr(stored, "strftime")
                    else str(stored)[:19]
                )
                summary = (report.summary or "(no summary)")[:45]
                label = f"{ts} — {summary}..."
                if st.button(label, key=f"kb_load_{i}", use_container_width=True):
                    st.session_state[KEY_ACTIVE_REPORT] = report.model_dump(mode="json")
                    st.rerun()
        else:
            st.caption("No past analogies yet. Run an analysis to build the knowledge base.")

    st.title("Analogy-Engine: AI Research Workbench")
    st.markdown(
        "Compare two domains (e.g. hydraulics vs. electronics), or use Researcher Mode "
        "to discover analogies for your problem."
    )
    st.divider()

    tab_dual, tab_researcher = st.tabs(["Dual Domain", "Researcher Mode"])

    with tab_dual:
        st.subheader("Dual Domain")
        st.caption("Enter a source and a target domain to find the analogy between them.")
        text_source = st.text_area(
            "Source Domain",
            value=DEFAULT_SOURCE,
            height=100,
            help="Text describing the source domain.",
            key="dual_source",
        )
        text_target = st.text_area(
            "Target Domain",
            value=DEFAULT_TARGET,
            height=100,
            help="Text describing the target domain.",
            key="dual_target",
        )

        if st.button("Launch Analysis", key="btn_dual"):
            with st.expander("📝 Reasoning Process", expanded=True):
                log_area = st.empty()
            log_queue_dual: queue.Queue[str] = queue.Queue()
            ctx = get_script_run_ctx() if get_script_run_ctx is not None else None
            original_start = threading.Thread.start
            if ctx is not None and add_script_run_ctx is not None:

                def _patched_start(self: threading.Thread) -> None:
                    add_script_run_ctx(self, ctx)
                    original_start(self)

                threading.Thread.start = _patched_start  # type: ignore[method-assign]
            try:
                run_pipeline(
                    text_source.strip() or DEFAULT_SOURCE,
                    text_target.strip() or DEFAULT_TARGET,
                    log_placeholder=log_area,
                    log_queue=log_queue_dual,
                )
            except Exception as e:
                st.error(str(e))
            finally:
                threading.Thread.start = original_start  # type: ignore[method-assign]
            st.rerun()

    with tab_researcher:
        st.subheader("Researcher Mode")
        st.caption(
            "Describe your problem; the Visionary will suggest a far-removed source domain, "
            "then the full pipeline runs to build the analogy."
        )
        problem_text = st.text_area(
            "Describe your current problem or research topic",
            value="",
            height=120,
            placeholder=(
                "Comment transférer instantanément l'information entre deux points "
                "distants sans support physique ?"
            ),
            help="Formulez en concepts (sujet, objectif, phénomène) pour de meilleurs résultats.",
            key="researcher_problem",
        )

        if st.button("Discover Analogies", key="btn_researcher"):
            problem = problem_text.strip()
            if not problem:
                st.warning("Please describe your problem or research topic.")
            else:
                with st.expander("📝 Reasoning Process", expanded=True):
                    log_area_res = st.empty()
                log_queue_res: queue.Queue[str] = queue.Queue()
                ctx = get_script_run_ctx() if get_script_run_ctx is not None else None
                original_start = threading.Thread.start
                if ctx is not None and add_script_run_ctx is not None:

                    def _patched_start_res(self: threading.Thread) -> None:
                        add_script_run_ctx(self, ctx)
                        original_start(self)

                    threading.Thread.start = _patched_start_res  # type: ignore[method-assign]
                try:
                    get_config()
                    llm_config = build_llm_config()
                    visionary = Visionary(llm_config=llm_config)
                    writer_res = QueueLogWriter(log_queue_res)
                    with (
                        contextlib.redirect_stdout(writer_res),
                        contextlib.redirect_stderr(writer_res),
                    ):
                        with st.status("Visionary suggesting source domain...", expanded=True):
                            suggested_source = asyncio.run(visionary.process(problem))
                    if suggested_source:
                        st.info(f"**Visionary suggests looking at:** {suggested_source}")
                        run_pipeline(
                            suggested_source,
                            problem,
                            log_placeholder=log_area_res,
                            log_queue=log_queue_res,
                        )
                    else:
                        st.error("Visionary did not return a source suggestion.")
                except Exception as e:
                    st.error(str(e))
                finally:
                    threading.Thread.start = original_start  # type: ignore[method-assign]
                st.rerun()

    active_raw = st.session_state.get(KEY_ACTIVE_REPORT)
    if active_raw is not None:
        try:
            active_report = ResearchReport.model_validate(active_raw)
        except Exception:
            active_report = None
    else:
        active_report = None

    if active_report is not None:
        st.divider()
        # Redraw the graph from stored trace (graph_a, graph_b) so we don't depend on saved images
        map_path = Path("assets/maps/current_display.png")
        if active_report.properties.get("graph_a") and active_report.properties.get("graph_b"):
            draw_analogy(active_report, output_path=str(map_path))
        if map_path.exists():
            st.image(str(map_path), width="stretch")
        else:
            st.caption("No graph data to display for this report.")
        st.metric(
            "Critic's Confidence Score",
            f"{active_report.hypothesis.confidence:.2f}",
        )
        st.subheader("Research Report")
        st.write("**Summary**")
        st.write(active_report.summary or "(none)")
        st.write("**Findings**")
        for f in active_report.findings:
            st.write(f"- {f}")
        if not active_report.findings:
            st.write("(none)")
        st.write("**Recommendation**")
        st.write(active_report.recommendation or "(none)")


if __name__ == "__main__":
    main()
