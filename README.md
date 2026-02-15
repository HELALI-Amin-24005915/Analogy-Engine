# Analogy-Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://helali-amin-24005915-analogy-engine-app-btjlvb.streamlit.app/)

[![Quality · Doc · Security](https://github.com/HELALI-Amin-24005915/Analogy-Engine/actions/workflows/quality.yml/badge.svg)](https://github.com/HELALI-Amin-24005915/Analogy-Engine/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <strong>Built for</strong>
  <br>
  <a href="https://innovationstudio.microsoft.com/hackathons/ai-dev-days/">
    <img src="https://img.shields.io/badge/Microsoft_AI_Dev_Days_Hackathon-0078D4?style=for-the-badge&logo=microsoft&logoColor=white" alt="Microsoft AI Dev Days Hackathon">
  </a>
  <br>
</p>

---

**Analogy-Engine** is an AI-powered analogy engine for scientific research. It connects distant domains (e.g. hydraulics ↔ electricity, ecosystems ↔ distributed systems) through a chain of specialized agents and generates structured reports with a technical action plan.

---

## Quick Access & Usage

The app is **deployed live** so the jury can try it immediately (see the [Streamlit badge](#analogy-engine) or link above). The UI implements a **Hot-Swap** logic (in `app.py`) so you can use it in two ways:

| Mode | Description |
|------|-------------|
| **Demo Mode (default)** | The app opens in **Archive Mode** by default. You can browse pre-generated scientific analogies and explore the knowledge base **without any API key**. Ideal for a quick look and for evaluators who do not have Azure OpenAI credentials. |
| **Live Mode** | To generate **new** analogies in real time, enter your **Azure OpenAI** credentials in the sidebar (API key, endpoint, deployment). Once validated, Live mode activates instantly and unlocks Dual Domain and Researcher generation. |

No need to clone or configure anything to explore the demo; use the live link above. For architecture details, see [System Architecture](#system-architecture). UI screenshots are in the [Screenshots (UI)](#screenshots-ui) section.

---

## Features

| Feature | Description |
|---------|-------------|
| **Dual Domain Mode** | Compare two domains you define (source + target) |
| **Researcher Mode** | Describe a problem; the AI suggests a source domain and runs the analysis |
| **Engineering Action Plan** | Transferable mechanisms, technical roadmap, metrics, and pitfalls |
| **Knowledge Base** | MongoDB storage for reports; browse history |
| **Sources** | Collect links via DuckDuckGo with academic / R&D filters |
| **Export** | Download reports as Markdown and PDF |

---

## Quick Start / Demo

**Don't have an Azure OpenAI key?** No problem!

The application opens by default in **Archive/Demo Mode**, allowing you to explore pre-generated scientific analogy examples without any configuration required.

### Launch Demo Mode

1. Clone the repository and install dependencies (see below).
2. Configure only MongoDB in `.env`:
   ```bash
   MONGODB_URI="mongodb+srv://..."
   ```
3. Launch the application:
   ```bash
   streamlit run app.py
   ```
4. The interface opens in Demo Mode with browsable examples.

### Switch to Live Mode

To generate new analogies, enter your Azure OpenAI credentials in the sidebar:

- **API Key**: Your Azure OpenAI key
- **Endpoint**: Your Azure resource URL (e.g. `https://xxx.openai.azure.com/`)
- **Recommended model**: GPT-4o

Once validated, Live mode activates instantly and unlocks generation features.

---

## Tech Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Azure_OpenAI-0078D4?style=flat-square&logo=microsoft-azure&logoColor=white" alt="Azure OpenAI">
  <img src="https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB">
  <img src="https://img.shields.io/badge/AutoGen-Microsoft-0078D4?style=flat-square&logo=microsoft&logoColor=white" alt="AutoGen">
  <img src="https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic">
  <img src="https://img.shields.io/badge/NetworkX-008CC1?style=flat-square&logo=networkx&logoColor=white" alt="NetworkX">
  <img src="https://img.shields.io/badge/Matplotlib-11557C?style=flat-square&logo=matplotlib&logoColor=white" alt="Matplotlib">
  <img src="https://img.shields.io/badge/DuckDuckGo-DE5833?style=flat-square&logo=duckduckgo&logoColor=white" alt="DuckDuckGo">
</p>

| Layer | Technology |
|-------|------------|
| **AI / Agents** | [AutoGen](https://microsoft.github.io/autogen/) (Microsoft), Azure OpenAI, GPT-4o |
| **Backend** | Python 3.11+, Pydantic, asyncio |
| **Database** | MongoDB Atlas (PyMongo) |
| **UI** | Streamlit |
| **Search** | [ddgs](https://pypi.org/project/ddgs/) (DuckDuckGo) |
| **Graphs** | NetworkX, Matplotlib |
| **Export** | fpdf2 (PDF), Markdown |
| **Protocols** | MCP (Model Context Protocol) |
| **Dev** | Ruff, MyPy, pip-audit |

---

## AI-Assisted Development

This project was developed using a modern **AI-assisted workflow**, combining several AI coding and reasoning tools to accelerate design, implementation, and quality assurance while keeping full control over architecture and final code.

| Tool | Role in this project |
|------|------------------------|
| **[Cursor](https://cursor.com)** | Primary IDE. In-editor AI (composer, chat, refactors), codebase-aware suggestions, and integrated terminal. Used for implementing features from specs, navigating the repo, and applying structured changes (e.g. ontology enforcement, mypy fixes). |
| **[GitHub Copilot](https://github.com/features/copilot)** | Inline code completion and short snippets. Used for boilerplate (Pydantic models, fixtures, Streamlit widgets), tests, and repetitive patterns. |
| **[Claude](https://claude.ai)** (Anthropic) | Long-context reasoning and design. Used for pipeline design (Scout → Matcher → Critic → Architect), ontology taxonomy wording, and reviewing multi-file flows. |
| **[Gemini](https://gemini.google.com)** (Google) | Alternative perspective and validation. Used for cross-checking prompts, suggesting test cases, and validating documentation clarity. |

### How they were used

- **Architecture & specs:** Claude and Cursor were used to turn high-level ideas (e.g. “triple-layer ontology”, “refinement loop”) into concrete plans and file-level tasks.
- **Implementation:** Cursor (composer/agent) and Copilot handled most of the typing: agents, schema, pipeline wiring, and UI. Cursor’s codebase awareness helped keep changes consistent across modules.
- **Quality:** MyPy and Ruff were run in CI; Cursor and Claude were used to fix type errors and align style. Gemini was occasionally used to double-check prompt and README wording.
- **Version control:** Commits and push were done locally; branch rules (e.g. code scanning) were adjusted on GitHub so that CI and push could succeed.

**Code verification, logic, review, and problem resolution are performed by the developer.** AI tools suggest or generate code; the author is responsible for verifying correctness, validating the logic, conducting code review, and resolving any issues before commit. This setup illustrates a **human-in-the-loop** approach: the developer defines the product and architecture, checks and approves all changes, and uses AI to accelerate implementation and iteration—not to replace oversight.

---

## Prerequisites

### Required (all modes)

- **Python 3.11+**
- **MongoDB Atlas** (free tier) or MongoDB cluster

### Required (Live Mode only)

- **Azure OpenAI account** with:
  - Valid API key
  - Configured endpoint
  - **GPT-4o** model deployment (recommended)

**Important:** The **GPT-4o** model is the supported and optimized model for this application. Other models (GPT-4, GPT-3.5) may work but with variable results.

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/HELALI-Amin-24005915/Analogy-Engine.git
cd Analogy-Engine
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux / macOS
# or: .venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the values:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Endpoint URL (e.g. `https://xxx.openai.azure.com/`) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Deployment name (e.g. `gpt-4o`) |
| `MONGODB_URI` | MongoDB connection string (e.g. `mongodb+srv://user:pass@cluster.mongodb.net/`) |

**Note:** In Demo Mode, only `MONGODB_URI` is required. Azure OpenAI keys can be provided via the sidebar interface at usage time.

### 5. Run the application

```bash
streamlit run app.py
```

The UI will be available at [http://localhost:8501](http://localhost:8501).

---

## Demo: Analogy Map

Example output from the **Hydraulics ↔ Electricity** pipeline: logical property graphs with color-matched nodes.

![Analogy map — Hydraulics vs Electricity](assets/analogy_map.png)

*Graph A (source domain) and Graph B (target domain) with mappings shown as dotted lines.*

---

## Screenshots (UI)

### Generation Hub — Dual Domain Mode

Form to compare two domains (e.g. hydraulics and electronics).

### Report Viewer

Report display with summary, findings, recommendation, Engineering Action Plan, and sources.

### Knowledge Base (sidebar)

Report history with search by query and date.

> **Tip:** You can add UI screenshots to `assets/` (e.g. `assets/screenshot_hub.png`, `assets/screenshot_report.png`) and reference them here.

---

## System Architecture

Analogy-Engine uses a Pipe-and-Filter multi-agent pipeline (Scout, Matcher, Critic, Architect) that respects a Triple-Layer Ontology and an optional refinement loop until the Critic accepts the mapping.

[View Detailed Architecture & Agent Flow](./docs/ARCHITECTURE.md)

High-level context: the user interacts with the Streamlit UI, which orchestrates the agents via Azure OpenAI (GPT-4o), stores reports in MongoDB Atlas, and collects sources via DuckDuckGo.

```mermaid
flowchart LR
    User["User (Browser)"]
    subgraph SystemBoundary["Analogy-Engine"]
        StreamlitUI["Streamlit UI"]
        AzureOpenAI["Azure OpenAI\n(GPT-4o)"]
        MongoDBAtlas["MongoDB Atlas\n(Knowledge Base)"]
        DuckDuckGo["DuckDuckGo\n(Search)"]
    end

    User <-->|"HTTP"| StreamlitUI
    StreamlitUI -->|"LLM calls"| AzureOpenAI
    AzureOpenAI -->|"responses"| StreamlitUI
    StreamlitUI <-->|"store / retrieve reports"| MongoDBAtlas
    StreamlitUI -->|"source search"| DuckDuckGo
    DuckDuckGo -->|"URLs"| StreamlitUI
```

---

## Project Structure

```
Analogy-Engine/
├── app.py                 # Streamlit UI (interface + pipeline)
├── data_manager.py        # Static demo data for Archive/Demo mode
├── main.py                # Alternative entry point (CLI)
├── pyproject.toml         # Project config (Ruff, MyPy, Python 3.11+)
├── requirements.txt      # Python dependencies
├── .env.example           # Configuration template (no secrets)
├── LICENSE                # MIT License
├── assets/
│   ├── analogy_map.png    # Example analogy map
│   └── maps/              # Generated graphs (last_analogy_graph.png)
├── agents/
│   ├── base.py            # Base agent class
│   ├── scout.py           # Graph extraction
│   ├── matcher.py         # Node alignment
│   ├── critic.py          # Validation
│   ├── architect.py       # Synthesis + Action Plan
│   ├── visionary.py       # Source domain suggestion
│   └── librarian.py       # MongoDB storage
├── core/
│   ├── config.py          # Environment variable loading
│   ├── ontology.py        # Ontology alignment checks
│   └── schema.py          # Pydantic models (ResearchReport, etc.)
├── scripts/
│   ├── visualize_analogy.py   # Graph generation
│   ├── verify_quality.sh      # Quality checks
│   └── check_docs.py          # Documentation checks
├── config/
│   └── pre-commit-config.yaml
├── docs/
│   ├── ARCHITECTURE.md    # Detailed architecture & agent flow
│   └── TEST_QUERIES.md    # English test prompts for both modes
├── tests/
│   ├── test_config.py     # core.config (LLM config from input)
│   ├── test_data_manager.py
│   ├── test_librarian.py  # Librarian (with mocked MongoDB)
│   └── test_ontology.py   # Ontology alignment
└── .github/workflows/
    └── quality.yml        # CI (ruff, mypy, pip-audit)
```

---

## Example Queries (Doctoral Level)

See **[docs/TEST_QUERIES.md](docs/TEST_QUERIES.md)** for a full list of English test prompts for both modes.

### Dual Domain Mode

- **Source:** *Biological neural networks learn through synaptic plasticity (STDP) with precise temporal windows.*  
- **Target:** *Memristor-based neuromorphic architectures reproduce analog computation and plasticity with ultra-low energy consumption.*

### Researcher Mode

- *Which principles from natural ecosystems (resilience, redundancy, emergence) can be formally transferred to the design of fault-tolerant, self-organizing distributed systems?*
- *How can immune memory mechanisms (clonal selection, adaptive memory) inspire anomaly detection and cyberdefense architectures with continuous learning?*

---

## Unit Tests

Run the test suite with pytest:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover:

- **data_manager**: `get_existing_data()`, structure of `EXISTING_DATA`
- **core.config**: `build_llm_config_from_input()` (validation, stripping, custom deployment)
- **core.ontology**: ontology alignment checks
- **agents.librarian**: `delete_report()`, `get_all_reports()` return type (with mocked MongoDB)

---

## CI / CD and Quality

The **Quality · Doc · Security** workflow runs on every push and PR to `main`:

- `ruff format --check` and `ruff check`
- `mypy`
- `pip-audit` (CVE)
- `scripts/check_docs.py`

### Pre-commit (optional)

```bash
pre-commit install --config config/pre-commit-config.yaml
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `externally-managed-environment` with `pip` | Use the venv: `.venv/bin/pip install -r requirements.txt` |
| `Configuration error` on launch | Ensure `.env` exists and contains `MONGODB_URI`. For Live mode, add Azure OpenAI key and endpoint in the sidebar (or in `.env`) |
| `(no sources collected)` | Check internet connection; very long queries are automatically truncated |
| Pre-commit blocks commit | Use `PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit ...` or install `pre-commit` with the project config |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You may freely use, modify, and distribute this software under the terms of the MIT License.

---

## Contributors

Project developed for the **[Microsoft AI Dev Days Hackathon](https://innovationstudio.microsoft.com/hackathons/ai-dev-days/)** (Microsoft Innovation Studio).

Repository: [github.com/HELALI-Amin-24005915/Analogy-Engine](https://github.com/HELALI-Amin-24005915/Analogy-Engine)
