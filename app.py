"""
Analogy-Engine: AI Research Workbench — Streamlit UI.

Run with: streamlit run app.py
"""

import asyncio
import contextlib
import io
import queue
import sys
import threading
import traceback
from collections.abc import Coroutine
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

import streamlit as st
from fpdf import FPDF  # type: ignore[import-untyped]

from agents import Architect, Critic, Librarian, Matcher, Scout, Visionary
from core.config import build_llm_config, build_llm_config_from_input, get_config
from core.ontology import check_ontology_alignment as _check_ontology_alignment
from core.schema import (
    ResearchReport,
    ValidatedHypothesis,
)
from data_manager import get_existing_data
from scripts.visualize_analogy import draw_analogy

_T = TypeVar("_T")

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
        # Garder la référence à la vraie sortie (évite récursion quand stdout nous redirige ici)
        self._real_stdout = sys.__stdout__

    def write(self, s: str) -> int:
        if s:
            self._queue.put(s)
        if self._real_stdout is not None:
            self._real_stdout.write(s)
        return len(s)

    def flush(self) -> None:
        if self._real_stdout is not None:
            self._real_stdout.flush()


# Default domain texts (Hydraulics / Electronics example)
DEFAULT_SOURCE = (
    "In a pipe, high pressure creates a flow of water, but a narrow section restricts it."
)
DEFAULT_TARGET = (
    "In a circuit, high voltage drives an electric current, while a resistor limits it."
)

# Session state keys
KEY_ACTIVE_REPORT = "active_report"  # dict (model_dump) or None
KEY_ACTIVE_REPORT_ID = "active_report_id"  # MongoDB ObjectId for delete


def _get_live_llm_config() -> dict[str, Any]:
    """Build LLM config from sidebar inputs if set, otherwise from .env (local)."""
    api_key = (st.session_state.get("user_api_key") or "").strip()
    endpoint = (st.session_state.get("user_endpoint") or "").strip()
    if api_key and endpoint:
        deployment = st.session_state.get("user_deployment", "gpt-4o")
        return build_llm_config_from_input(api_key, endpoint, deployment)
    return build_llm_config()


def init_session_state() -> None:
    if KEY_ACTIVE_REPORT not in st.session_state:
        st.session_state[KEY_ACTIVE_REPORT] = None
    if KEY_ACTIVE_REPORT_ID not in st.session_state:
        st.session_state[KEY_ACTIVE_REPORT_ID] = None


def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Exécute une coroutine de façon compatible Streamlit (évite conflit event loop)."""
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        raise


def collect_sources(
    query: str,
    filter_academic: bool,
    filter_rd: bool,
    filter_noise: bool,
) -> list[str]:
    """Collect source URLs via DuckDuckGo search with enhanced query operators."""
    enhanced_query = query.strip()
    if filter_academic:
        enhanced_query += (
            ' (filetype:pdf "thesis" OR site:arxiv.org OR site:ieeexplore.ieee.org OR site:*.edu)'
        )
    if filter_rd:
        enhanced_query += ' ("white paper" OR site:*.gov OR "technical report")'
    if filter_noise:
        enhanced_query += (
            " -site:reddit.com -site:quora.com -site:youtube.com"
            " -site:facebook.com -site:twitter.com -inurl:news"
        )
    # DuckDuckGo returns 0 results for queries > ~500 chars (log: query_len 674 -> 0 results)
    if len(enhanced_query) > 400:
        enhanced_query = enhanced_query[:397] + "..."
    try:
        from ddgs import DDGS

        ddgs = DDGS()
        results = list(ddgs.text(enhanced_query, max_results=15))
        return list(dict.fromkeys(r.get("href", "") for r in results if r.get("href")))
    except Exception:
        return []


def _drain_and_show(log_queue: "queue.Queue[str]", log_placeholder: Any, buffer: list[str]) -> None:
    """Drain log_queue into buffer and update the Streamlit placeholder (main thread only)."""
    try:
        while True:
            buffer.append(log_queue.get_nowait())
    except queue.Empty:
        pass
    if buffer and log_placeholder is not None:
        log_placeholder.code("".join(buffer), language="text")


def _export_filename(extension: str) -> str:
    """Generate a timestamp-based filename for export."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"analogy_report_{ts}.{extension}"


def generate_markdown(report: ResearchReport, include_sources: bool = False) -> str:
    """Format ResearchReport as a well-structured Markdown string."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Analogy Engine - Research Report",
        "",
        "## Summary",
        report.summary.strip() if report.summary else "N/A",
        "",
    ]
    graph_path = Path("assets/maps/last_analogy_graph.png")
    if graph_path.exists():
        lines.extend(
            [
                "### 📊 Visual Mapping",
                "",
                "![Analogy Mapping](assets/maps/last_analogy_graph.png)",
                "",
            ]
        )
    lines.extend(["## Findings", ""])
    if report.findings:
        for f in report.findings:
            lines.append(f"- {f}")
    else:
        lines.append("N/A")
    rec = report.recommendation.strip() if report.recommendation else "N/A"
    lines.extend(["", "## Recommendation", rec, ""])

    ap = report.action_plan
    lines.extend(["## Engineering Action Plan", ""])
    lines.extend(["### Transferable Mechanisms", ""])
    if ap.transferable_mechanisms:
        for m in ap.transferable_mechanisms:
            lines.append(f"- {m}")
    else:
        lines.append("N/A")
    lines.extend(["", "### Technical Roadmap", ""])
    if ap.technical_roadmap:
        for i, step in enumerate(ap.technical_roadmap, 1):
            lines.append(f"{i}. {step}")
    else:
        lines.append("N/A")
    lines.extend(["", "### Key Metrics to Track", ""])
    if ap.key_metrics_to_track:
        for m in ap.key_metrics_to_track:
            lines.append(f"- {m}")
    else:
        lines.append("N/A")
    lines.extend(["", "### Potential Pitfalls", ""])
    if ap.potential_pitfalls:
        for p in ap.potential_pitfalls:
            lines.append(f"- {p}")
    else:
        lines.append("N/A")

    if include_sources and report.sources:
        lines.extend(["", "## Sources", ""])
        for url in report.sources:
            lines.append(f"- [{url}]({url})")

    lines.extend(["", f"*Generated on {ts}*"])
    return "\n".join(lines)


def _sanitize_for_ascii(text: str) -> str:
    """Replace non-ASCII chars with '?' for PDF when no Unicode font available."""
    return "".join(c if ord(c) < 128 else "?" for c in text)


def generate_pdf(report: ResearchReport, include_sources: bool = False) -> bytes:
    """Create a PDF document from the ResearchReport. Returns bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(25, 25, 25)

    # Try Unicode font; fall back to Helvetica + sanitization
    unicode_ok = False
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        str(Path.home() / ".local/share/fonts/DejaVuSans.ttf"),
    ]:
        if Path(font_path).exists():
            try:
                pdf.add_font("DejaVu", "", font_path)
                unicode_ok = True
                break
            except Exception:
                pass

    # Usable width: A4 210mm - left 25 - right 25 = 160mm
    w = 160
    line_height = 7

    def _write(s: str) -> None:
        text = s if unicode_ok else _sanitize_for_ascii(s)
        pdf.multi_cell(w, line_height, text, new_x="LMARGIN", new_y="NEXT")

    bullet = "\u2022" if unicode_ok else "-"

    def _section_title(title: str) -> None:
        if unicode_ok:
            pdf.set_font("DejaVu", "", 14)
        else:
            pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(40, 40, 40)
        _write(title)
        if unicode_ok:
            pdf.set_font("DejaVu", "", 11)
        else:
            pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def _hline() -> None:
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
        pdf.ln(4)

    if unicode_ok:
        pdf.set_font("DejaVu", "", 18)
    else:
        pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    _write("Analogy Engine - Research Report")
    pdf.set_font_size(11)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    _section_title("Summary")
    _write(report.summary.strip() if report.summary else "N/A")
    pdf.ln(8)

    graph_path = Path("assets/maps/last_analogy_graph.png")
    if graph_path.exists():
        try:
            pdf.image(str(graph_path), x=pdf.l_margin, y=pdf.get_y(), w=160)
            # Advance Y so Findings does not overlap (w=160mm; reserve space for scaled height)
            pdf.ln(100)
        except Exception:
            pass

    _hline()

    _section_title("Findings")
    if report.findings:
        for f in report.findings:
            _write(f"  {bullet}  {f}")
    else:
        _write("N/A")
    pdf.ln(8)
    _hline()

    _section_title("Recommendation")
    _write(report.recommendation.strip() if report.recommendation else "N/A")
    pdf.ln(10)
    _hline()

    if unicode_ok:
        pdf.set_font("DejaVu", "", 14)
    else:
        pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(40, 40, 40)
    _write("Engineering Action Plan")
    pdf.set_font_size(11)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    ap = report.action_plan

    _section_title("Transferable Mechanisms")
    if ap.transferable_mechanisms:
        for m in ap.transferable_mechanisms:
            _write(f"  {bullet}  {m}")
    else:
        _write("N/A")
    pdf.ln(6)

    _section_title("Technical Roadmap")
    if ap.technical_roadmap:
        for i, step in enumerate(ap.technical_roadmap, 1):
            _write(f"  {i}. {step}")
    else:
        _write("N/A")
    pdf.ln(6)

    _section_title("Key Metrics to Track")
    if ap.key_metrics_to_track:
        for m in ap.key_metrics_to_track:
            _write(f"  {bullet}  {m}")
    else:
        _write("N/A")
    pdf.ln(6)

    _section_title("Potential Pitfalls")
    if ap.potential_pitfalls:
        for p in ap.potential_pitfalls:
            _write(f"  {bullet}  {p}")
    else:
        _write("N/A")

    if include_sources and report.sources:
        pdf.ln(8)
        _hline()
        _section_title("Sources")
        for url in report.sources:
            _write(url)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _drain_milestones(
    milestone_queue: "queue.Queue[str]",
    milestone_placeholder: Any,
    buffer: list[str],
) -> None:
    """Drain milestone queue into buffer and update placeholder with timestamped log."""
    try:
        while True:
            buffer.append(milestone_queue.get_nowait())
    except queue.Empty:
        pass
    if buffer and milestone_placeholder is not None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        lines = [f"[{ts}] {m}" for m in buffer]
        milestone_placeholder.code("\n".join(lines), language="text")


def run_pipeline(
    llm_config: dict[str, Any],
    text_source: str,
    text_target: str,
    *,
    filter_academic: bool = False,
    filter_rd: bool = False,
    filter_noise: bool = True,
    log_placeholder: Any | None = None,
    log_queue: "queue.Queue[str] | None" = None,
    milestone_placeholder: Any | None = None,
    milestone_queue: "queue.Queue[str] | None" = None,
) -> None:
    """Run Scout -> Matcher -> Critic (optional refine) -> Architect, then save and store.
    llm_config must be built from build_llm_config_from_input() in Live mode.
    When log_placeholder and log_queue are set, stdout is captured to the queue and the
    placeholder is updated from the main thread after each step (no ScriptRunContext).
    When milestone_placeholder and milestone_queue are set, agent milestones are shown in the console.
    """
    scout = Scout(llm_config=llm_config)
    matcher = Matcher(llm_config=llm_config)
    critic = Critic(llm_config=llm_config)
    architect = Architect(llm_config=llm_config)
    librarian = Librarian()

    use_queue = log_placeholder is not None and log_queue is not None
    use_milestones = milestone_placeholder is not None and milestone_queue is not None
    if use_queue and log_queue is not None:
        writer = QueueLogWriter(log_queue)
        stdout_ctx: contextlib.AbstractContextManager[Any] = contextlib.redirect_stdout(writer)
        stderr_ctx: contextlib.AbstractContextManager[Any] = contextlib.redirect_stderr(writer)
    else:
        stdout_ctx = contextlib.nullcontext()
        stderr_ctx = contextlib.nullcontext()

    log_buffer: list[str] = []
    milestone_buffer: list[str] = []

    def _milestone(msg: str) -> None:
        if use_milestones and milestone_queue is not None:
            milestone_queue.put(msg)
            if milestone_placeholder is not None:
                _drain_milestones(milestone_queue, milestone_placeholder, milestone_buffer)

    with stdout_ctx, stderr_ctx:
        with st.status("Running analysis...", expanded=True) as status:
            status.update(label="Scouting...", state="running")
            _milestone("Scout: Extracting logical graph from source domain...")
            graph_a = _run_async(scout.process(text_source))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            n_a = len(graph_a.nodes)
            e_a = len(graph_a.edges)
            _milestone(f"Scout: Graph extraction complete — source ({n_a} nodes, {e_a} edges)")
            _milestone("Scout: Extracting logical graph from target domain...")
            graph_b = _run_async(scout.process(text_target))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            n_b = len(graph_b.nodes)
            e_b = len(graph_b.edges)
            _milestone(f"Scout: Graph extraction complete — target ({n_b} nodes, {e_b} edges)")

            status.update(label="Matching...", state="running")
            _milestone("Matcher: Aligning nodes between domains...")
            mapping = _run_async(matcher.process({"graph_a": graph_a, "graph_b": graph_b}))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            n_m = len(mapping.node_matches)
            _milestone(f"Matcher: Aligned {n_m} node pairs between domains")

            status.update(label="Critiquing...", state="running")
            _milestone("Critic: Validating mapping consistency and confidence...")
            ontology_ok, ontology_issues = _check_ontology_alignment(mapping, graph_a, graph_b)
            if not ontology_ok:
                hypothesis = ValidatedHypothesis(
                    mapping=mapping,
                    is_consistent=False,
                    issues=ontology_issues,
                    confidence=0.0,
                )
            else:
                hypothesis = _run_async(critic.process(mapping))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            _milestone(
                f"Critic: Confidence {hypothesis.confidence:.2f}, "
                f"consistency {'PASS' if hypothesis.is_consistent else 'REFINE'}"
            )

            if (not hypothesis.is_consistent) or (hypothesis.confidence < 0.8):
                _milestone("Critic: Triggering refinement loop (Matcher + Critic)...")
                refined_mapping = _run_async(
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
                ref_ontology_ok, ref_ontology_issues = _check_ontology_alignment(
                    refined_mapping, graph_a, graph_b
                )
                if not ref_ontology_ok:
                    final_hypothesis = ValidatedHypothesis(
                        mapping=refined_mapping,
                        is_consistent=False,
                        issues=ref_ontology_issues,
                        confidence=0.0,
                    )
                else:
                    final_hypothesis = _run_async(critic.process(refined_mapping))
                if use_queue and log_queue is not None:
                    _drain_and_show(log_queue, log_placeholder, log_buffer)
                _milestone(
                    f"Critic: After refinement — confidence {final_hypothesis.confidence:.2f}, "
                    f"consistency {'PASS' if final_hypothesis.is_consistent else 'FAIL'}"
                )
            else:
                final_hypothesis = hypothesis

            status.update(label="Synthesizing...", state="running")
            _milestone("Architect: Generating research report and action plan...")
            report = _run_async(architect.process(final_hypothesis))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            n_mech = len(report.action_plan.transferable_mechanisms)
            _milestone(f"Architect: Report ready — {n_mech} transferable mechanisms")

    report.properties["graph_a"] = graph_a.model_dump()
    report.properties["graph_b"] = graph_b.model_dump()
    report.input_query = f"{text_source} | {text_target}"
    report.properties["stored_at"] = datetime.now(timezone.utc).isoformat()
    query = f"{text_source} {text_target}"
    report.sources = collect_sources(query, filter_academic, filter_rd, filter_noise)
    Path("assets/maps").mkdir(parents=True, exist_ok=True)
    draw_analogy(report, output_path="assets/maps/last_analogy_graph.png")
    librarian.store_report(report)
    st.session_state[KEY_ACTIVE_REPORT] = report.model_dump(mode="json")


def main() -> None:
    st.set_page_config(
        page_title="Analogy-Engine",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Lock sidebar width: prevent closing completely or opening too wide
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 300px;
            max-width: 380px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    init_session_state()

    try:
        get_config()
    except Exception as e:
        st.error(
            f"Configuration error: {e}. Set MONGODB_URI in .env. "
            "For Live mode, provide your Azure OpenAI API key and endpoint in the sidebar."
        )
        st.stop()

    librarian = Librarian()
    all_reports = librarian.get_all_reports()  # newest first

    with st.sidebar:
        st.markdown("### 🔬 Analogy-Engine")
        st.caption("AI Research Workbench")
        st.divider()
        st.subheader("Azure OpenAI Configuration")
        st.text_input(
            "API Key",
            type="password",
            key="user_api_key",
            help="Azure OpenAI key for Live mode.",
        )
        st.text_input(
            "Endpoint URL",
            key="user_endpoint",
            placeholder="https://xxx.openai.azure.com/",
        )
        st.selectbox(
            "Deployment",
            ["gpt-4o", "gpt-4", "gpt-35-turbo"],
            index=0,
            key="user_deployment",
        )
        st.info("Recommended model: GPT-4o for optimal results")
        st.divider()
        if st.button("➕ New research", use_container_width=True, key="btn_new_search"):
            for k in [
                KEY_ACTIVE_REPORT,
                KEY_ACTIVE_REPORT_ID,
                "dual_source",
                "dual_target",
                "researcher_problem",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        st.divider()
        st.title("Knowledge Base")
        st.metric("Total Reports", len(all_reports))
        st.divider()
        if all_reports:
            st.caption("Click a report to view. Use the delete button to remove it.")
            for i, (report, meta, doc_id) in enumerate(all_reports):
                stored = meta.stored_at
                ts = (
                    stored.strftime("%Y-%m-%d %H:%M")
                    if hasattr(stored, "strftime")
                    else str(stored)[:19]
                )
                raw_query = report.input_query or report.summary or "(no query)"
                query_display = raw_query[:45] + ("..." if len(raw_query) > 45 else "")
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(
                        f"{ts} — {query_display}",
                        key=f"kb_load_{i}",
                        use_container_width=True,
                    ):
                        report_dict = report.model_dump(mode="json")
                        props = report_dict.get("properties") or {}
                        if "stored_at" not in props and meta.stored_at:
                            stored_val = meta.stored_at
                            props["stored_at"] = (
                                stored_val.isoformat()
                                if hasattr(stored_val, "isoformat")
                                else str(stored_val)
                            )
                        report_dict["properties"] = props
                        st.session_state[KEY_ACTIVE_REPORT] = report_dict
                        st.session_state[KEY_ACTIVE_REPORT_ID] = doc_id
                        st.rerun()
                with col_del:
                    if st.button("🗑", key=f"kb_del_{i}", help="Delete this report"):
                        if librarian.delete_report(doc_id):
                            if st.session_state.get(KEY_ACTIVE_REPORT_ID) == doc_id:
                                del st.session_state[KEY_ACTIVE_REPORT]
                                del st.session_state[KEY_ACTIVE_REPORT_ID]
                            st.rerun()
                        else:
                            st.error("Could not delete report.")
        else:
            st.caption("No past analogies yet. Run an analysis to build the knowledge base.")

        st.divider()
        st.subheader("Source Filtering")
        st.checkbox(
            "Academic Papers (arXiv, IEEE, Theses)",
            value=False,
            key="filter_academic",
        )
        st.checkbox(
            "Technical R&D Reports & Official Docs",
            value=False,
            key="filter_rd",
        )
        st.checkbox(
            "Filter Noise (Exclude News/Forums)",
            value=True,
            key="filter_noise",
        )

    has_api_key = bool((st.session_state.get("user_api_key") or "").strip())
    has_endpoint = bool((st.session_state.get("user_endpoint") or "").strip())
    try:
        config = get_config()
        has_keys_from_env = bool(config.AZURE_OPENAI_API_KEY and config.AZURE_OPENAI_ENDPOINT)
    except Exception:
        has_keys_from_env = False
    is_live_mode = (has_api_key and has_endpoint) or has_keys_from_env

    active_raw = st.session_state.get(KEY_ACTIVE_REPORT)
    if active_raw is not None:
        try:
            active_report = ResearchReport.model_validate(active_raw)
        except Exception:
            active_report = None
    else:
        active_report = None

    if active_report is not None:
        # Report Viewer
        query_display = active_report.input_query or "(no query)"
        if len(query_display) > 100:
            query_display = query_display[:97] + "..."
        st.header(f"Report: {query_display}")
        stored_at_raw = active_report.properties.get("stored_at", "")
        if stored_at_raw:
            stored_at_str = (
                stored_at_raw[:19].replace("T", " ")
                if isinstance(stored_at_raw, str)
                else str(stored_at_raw)[:19]
            )
            st.caption(f"Generated on {stored_at_str}")
        else:
            st.caption("(date unknown)")
        active_report_id = st.session_state.get(KEY_ACTIVE_REPORT_ID)
        if active_report_id is not None:
            if st.button("Delete this report", type="secondary", key="btn_delete_report"):
                if librarian.delete_report(active_report_id):
                    del st.session_state[KEY_ACTIVE_REPORT]
                    del st.session_state[KEY_ACTIVE_REPORT_ID]
                    st.rerun()
                else:
                    st.error("Could not delete report.")
        st.divider()
        # Redraw the graph from stored trace (graph_a, graph_b) so we don't depend on saved images
        map_path = Path("assets/maps/last_analogy_graph.png")
        if active_report.properties.get("graph_a") and active_report.properties.get("graph_b"):
            Path("assets/maps").mkdir(parents=True, exist_ok=True)
            draw_analogy(active_report, output_path=str(map_path))
        if map_path.exists():
            # Lire les bytes pour éviter MediaFileStorageError (référence hash obsolète après rerun)
            with open(map_path, "rb") as f:
                st.image(f.read(), width="stretch")
        else:
            st.caption("No graph data to display for this report.")
        st.metric(
            "Critic's Confidence Score",
            f"{active_report.hypothesis.confidence:.2f}",
        )
        st.divider()
        include_sources = st.checkbox(
            "Include sources in export (PDF/Markdown)",
            value=False,
            key="include_sources",
        )
        col_md, col_pdf = st.columns(2)
        with col_md:
            md_content = generate_markdown(active_report, include_sources=include_sources)
            st.download_button(
                label="📄 Download .md",
                data=md_content,
                file_name=_export_filename("md"),
                mime="text/markdown",
                key="dl_md",
            )
        with col_pdf:
            pdf_bytes = generate_pdf(active_report, include_sources=include_sources)
            st.download_button(
                label="📑 Download .pdf",
                data=pdf_bytes,
                file_name=_export_filename("pdf"),
                mime="application/pdf",
                key="dl_pdf",
            )
        st.divider()
        st.subheader("Research Report")
        st.write("**Summary**")
        st.write(active_report.summary or "(none)")
        st.write("**Findings**")
        for finding in active_report.findings:
            st.write(f"- {finding}")
        if not active_report.findings:
            st.write("(none)")
        st.write("**Recommendation**")
        st.write(active_report.recommendation or "(none)")

        with st.expander("Engineering Action Plan", expanded=True):
            ap = active_report.action_plan
            st.write("**Transferable Mechanisms**")
            for m in ap.transferable_mechanisms:
                st.write(f"- {m}")
            if not ap.transferable_mechanisms:
                st.write("(none)")
            st.write("**Technical Roadmap**")
            for i, step in enumerate(ap.technical_roadmap, 1):
                st.write(f"{i}. {step}")
            if not ap.technical_roadmap:
                st.write("(none)")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Key Metrics**")
                for m in ap.key_metrics_to_track:
                    st.write(f"- {m}")
                if not ap.key_metrics_to_track:
                    st.write("(none)")
            with col2:
                st.write("**Potential Pitfalls**")
                for p in ap.potential_pitfalls:
                    st.write(f"- {p}")
                if not ap.potential_pitfalls:
                    st.write("(none)")

        with st.expander("Sources", expanded=False):
            if active_report.sources:
                for url in active_report.sources:
                    st.markdown(f"- [{url}]({url})")
            else:
                st.caption("(no sources collected)")

    elif not is_live_mode:
        # Demo/Archive Mode: pre-generated examples only
        st.warning(
            "Demo/Archive Mode: You are viewing pre-generated examples. "
            "Enter your Azure OpenAI API key and endpoint in the sidebar to activate Live mode."
        )
        st.title("Analogy-Engine: AI Research Workbench")
        st.subheader("Analogy Examples")
        st.caption(
            "High-quality scientific analogies. Provide your API credentials in the sidebar to generate new ones."
        )
        st.divider()
        examples = get_existing_data()
        for ex in examples:
            with st.container():
                st.subheader(ex.input_query or "Analogy")
                st.write(f"**Confidence:** {ex.hypothesis.confidence:.2f}")
                st.write(f"**Summary:** {ex.summary or 'N/A'}")
                with st.expander("View details"):
                    st.write("**Findings**")
                    for finding in ex.findings:
                        st.write(f"- {finding}")
                    st.write("**Recommendation**")
                    st.write(ex.recommendation or "N/A")
                    st.write("**Transferable Mechanisms**")
                    for m in ex.action_plan.transferable_mechanisms:
                        st.write(f"- {m}")
                    st.write("**Technical Roadmap**")
                    for i, step in enumerate(ex.action_plan.technical_roadmap, 1):
                        st.write(f"{i}. {step}")
                    if ex.sources:
                        st.write("**Sources**")
                        for url in ex.sources:
                            st.markdown(f"- [{url}]({url})")
                st.divider()

    else:
        # Live Mode: Generation + Demo examples (keys from .env or sidebar)
        st.success("Live Mode activated: Analogy generation available")
        if has_keys_from_env and not (has_api_key and has_endpoint):
            st.caption("Using API keys from .env (local). You can also view demo examples below.")
        st.divider()
        st.subheader("Multi-Agent Reasoning Console")
        st.caption(
            "Watch the AI agents collaborate in real-time (Scout → Matcher → Critic → Architect)"
        )
        with st.expander("Agent Activity Log", expanded=False):
            agent_log_placeholder = st.empty()
        agent_milestone_queue: queue.Queue[str] = queue.Queue()

        tab_generate, tab_examples = st.tabs(["Generate", "Examples"])

        with tab_examples:
            st.subheader("Analogy Examples")
            st.caption(
                "Pre-generated scientific analogies. Use the Generate tab to create new reports."
            )
            st.divider()
            examples = get_existing_data()
            for ex in examples:
                with st.container():
                    st.subheader(ex.input_query or "Analogy")
                    st.write(f"**Confidence:** {ex.hypothesis.confidence:.2f}")
                    st.write(f"**Summary:** {ex.summary or 'N/A'}")
                    with st.expander("View details"):
                        st.write("**Findings**")
                        for finding in ex.findings:
                            st.write(f"- {finding}")
                        st.write("**Recommendation**")
                        st.write(ex.recommendation or "N/A")
                        st.write("**Transferable Mechanisms**")
                        for m in ex.action_plan.transferable_mechanisms:
                            st.write(f"- {m}")
                        st.write("**Technical Roadmap**")
                        for i, step in enumerate(ex.action_plan.technical_roadmap, 1):
                            st.write(f"{i}. {step}")
                        if ex.sources:
                            st.write("**Sources**")
                            for url in ex.sources:
                                st.markdown(f"- [{url}]({url})")
                    st.divider()

        with tab_generate:
            st.title("Analogy-Engine: AI Research Workbench")
            st.markdown(
                "Compare two domains (e.g. hydraulics vs. electronics), or use Researcher Mode "
                "to discover analogies for your problem. Click **New research** in the sidebar to start."
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
                    try:
                        llm_config = _get_live_llm_config()
                    except ValueError as e:
                        st.error(f"Configuration: {e}")
                        st.stop()
                    st.info("Analysis running… (2–5 minutes depending on API calls)")
                    with st.expander("Reasoning Process", expanded=True):
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
                            llm_config,
                            text_source.strip() or DEFAULT_SOURCE,
                            text_target.strip() or DEFAULT_TARGET,
                            filter_academic=st.session_state.get("filter_academic", False),
                            filter_rd=st.session_state.get("filter_rd", False),
                            filter_noise=st.session_state.get("filter_noise", True),
                            log_placeholder=log_area,
                            log_queue=log_queue_dual,
                            milestone_placeholder=agent_log_placeholder,
                            milestone_queue=agent_milestone_queue,
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication error: Check your API key and endpoint. {e}")
                        with st.expander("Error details"):
                            st.code(traceback.format_exc(), language="text")
                    finally:
                        threading.Thread.start = original_start  # type: ignore[method-assign]

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
                        "How to transfer information instantly between two distant points "
                        "without a physical medium?"
                    ),
                    help="Use concepts (subject, goal, phenomenon) for better results.",
                    key="researcher_problem",
                )

                if st.button("Discover Analogies", key="btn_researcher"):
                    problem = problem_text.strip()
                    if not problem:
                        st.warning("Please describe your problem or research topic.")
                    else:
                        try:
                            llm_config = _get_live_llm_config()
                        except ValueError as e:
                            st.error(f"Configuration: {e}")
                            st.stop()
                        st.info("Analysis running… (2–5 minutes depending on API calls)")
                        with st.expander("Reasoning Process", expanded=True):
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
                            visionary = Visionary(llm_config=llm_config)
                            writer_res = QueueLogWriter(log_queue_res)
                            with (
                                contextlib.redirect_stdout(writer_res),
                                contextlib.redirect_stderr(writer_res),
                            ):
                                with st.status(
                                    "Visionary suggesting source domain...", expanded=True
                                ):
                                    suggested_source = _run_async(visionary.process(problem))
                            if suggested_source:
                                st.info(f"**Visionary suggests looking at:** {suggested_source}")
                                run_pipeline(
                                    llm_config,
                                    suggested_source,
                                    problem,
                                    filter_academic=st.session_state.get("filter_academic", False),
                                    filter_rd=st.session_state.get("filter_rd", False),
                                    filter_noise=st.session_state.get("filter_noise", True),
                                    log_placeholder=log_area_res,
                                    log_queue=log_queue_res,
                                    milestone_placeholder=agent_log_placeholder,
                                    milestone_queue=agent_milestone_queue,
                                )
                                st.rerun()
                            else:
                                st.error("Visionary did not return a source suggestion.")
                        except Exception as e:
                            st.error(f"Authentication error: Check your API key and endpoint. {e}")
                            with st.expander("Error details"):
                                st.code(traceback.format_exc(), language="text")
                        finally:
                            threading.Thread.start = original_start  # type: ignore[method-assign]


if __name__ == "__main__":
    main()
