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
from core.config import build_llm_config, get_config
from core.schema import ResearchReport
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


def init_session_state() -> None:
    if KEY_ACTIVE_REPORT not in st.session_state:
        st.session_state[KEY_ACTIVE_REPORT] = None


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
        "## Findings",
    ]
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


def run_pipeline(
    text_source: str,
    text_target: str,
    *,
    filter_academic: bool = False,
    filter_rd: bool = False,
    filter_noise: bool = True,
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
            graph_a = _run_async(scout.process(text_source))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)
            graph_b = _run_async(scout.process(text_target))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            status.update(label="Matching...", state="running")
            mapping = _run_async(matcher.process({"graph_a": graph_a, "graph_b": graph_b}))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            status.update(label="Critiquing...", state="running")
            hypothesis = _run_async(critic.process(mapping))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

            if (not hypothesis.is_consistent) or (hypothesis.confidence < 0.8):
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
                final_hypothesis = _run_async(critic.process(refined_mapping))
                if use_queue and log_queue is not None:
                    _drain_and_show(log_queue, log_placeholder, log_buffer)
            else:
                final_hypothesis = hypothesis

            status.update(label="Synthesizing...", state="running")
            report = _run_async(architect.process(final_hypothesis))
            if use_queue and log_queue is not None:
                _drain_and_show(log_queue, log_placeholder, log_buffer)

    report.properties["graph_a"] = graph_a.model_dump()
    report.properties["graph_b"] = graph_b.model_dump()
    report.input_query = f"{text_source} | {text_target}"
    report.properties["stored_at"] = datetime.now(timezone.utc).isoformat()
    query = f"{text_source} {text_target}"
    report.sources = collect_sources(query, filter_academic, filter_rd, filter_noise)
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
        if st.button("➕ New research", use_container_width=True, key="btn_new_search"):
            for k in [KEY_ACTIVE_REPORT, "dual_source", "dual_target", "researcher_problem"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        st.divider()
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
                raw_query = report.input_query or report.summary or "(sans requête)"
                query_display = raw_query[:45] + ("..." if len(raw_query) > 45 else "")
                label = f"{ts} — {query_display}"
                if st.button(label, key=f"kb_load_{i}", use_container_width=True):
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
                    st.rerun()
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

    active_raw = st.session_state.get(KEY_ACTIVE_REPORT)
    if active_raw is not None:
        try:
            active_report = ResearchReport.model_validate(active_raw)
        except Exception:
            active_report = None
    else:
        active_report = None

    if active_report is None:
        # Generation Hub
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
                st.info("⏳ Lancement de l'analyse… (2 à 5 minutes selon les appels API)")
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
                        filter_academic=st.session_state.get("filter_academic", False),
                        filter_rd=st.session_state.get("filter_rd", False),
                        filter_noise=st.session_state.get("filter_noise", True),
                        log_placeholder=log_area,
                        log_queue=log_queue_dual,
                    )
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
                    with st.expander("Détails de l'erreur"):
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
                    "Comment transférer instantanément l'information entre deux points "
                    "distants sans support physique ?"
                ),
                help=(
                    "Formulez en concepts (sujet, objectif, phénomène) pour de meilleurs résultats."
                ),
                key="researcher_problem",
            )

            if st.button("Discover Analogies", key="btn_researcher"):
                problem = problem_text.strip()
                if not problem:
                    st.warning("Please describe your problem or research topic.")
                else:
                    st.info("⏳ Lancement de l'analyse… (2 à 5 minutes selon les appels API)")
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
                                suggested_source = _run_async(visionary.process(problem))
                        if suggested_source:
                            st.info(f"**Visionary suggests looking at:** {suggested_source}")
                            run_pipeline(
                                suggested_source,
                                problem,
                                filter_academic=st.session_state.get("filter_academic", False),
                                filter_rd=st.session_state.get("filter_rd", False),
                                filter_noise=st.session_state.get("filter_noise", True),
                                log_placeholder=log_area_res,
                                log_queue=log_queue_res,
                            )
                            st.rerun()
                        else:
                            st.error("Visionary did not return a source suggestion.")
                    except Exception as e:
                        st.error(str(e))
                        with st.expander("Détails de l'erreur"):
                            st.code(traceback.format_exc(), language="text")
                    finally:
                        threading.Thread.start = original_start  # type: ignore[method-assign]

    else:
        # Report Viewer
        query_display = active_report.input_query or "(sans requête)"
        if len(query_display) > 100:
            query_display = query_display[:97] + "..."
        st.header(f"🔍 {query_display}")
        stored_at_raw = active_report.properties.get("stored_at", "")
        if stored_at_raw:
            stored_at_str = (
                stored_at_raw[:19].replace("T", " ")
                if isinstance(stored_at_raw, str)
                else str(stored_at_raw)[:19]
            )
            st.caption(f"Rapport généré le {stored_at_str}")
        else:
            st.caption("(date inconnue)")
        st.divider()
        # Redraw the graph from stored trace (graph_a, graph_b) so we don't depend on saved images
        map_path = Path("assets/maps/current_display.png")
        if active_report.properties.get("graph_a") and active_report.properties.get("graph_b"):
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
            "Inclure les sources dans l'export (PDF/Markdown)",
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

        with st.expander("📚 Voir les sources utilisées", expanded=False):
            if active_report.sources:
                for url in active_report.sources:
                    st.markdown(f"- [{url}]({url})")
            else:
                st.caption("(aucune source collectée)")


if __name__ == "__main__":
    main()
