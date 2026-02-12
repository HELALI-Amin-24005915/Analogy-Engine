# Analogy-Engine

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
| **AI / Agents** | [AutoGen](https://microsoft.github.io/autogen/) (Microsoft), Azure OpenAI, GPT-4 |
| **Backend** | Python 3.10+, Pydantic, asyncio |
| **Database** | MongoDB Atlas (PyMongo) |
| **UI** | Streamlit |
| **Search** | [ddgs](https://pypi.org/project/ddgs/) (DuckDuckGo) |
| **Graphs** | NetworkX, Matplotlib |
| **Export** | fpdf2 (PDF), Markdown |
| **Protocols** | MCP (Model Context Protocol) |
| **Dev** | Ruff, MyPy, pip-audit |

---

## Prerequisites

- **Python 3.10+**
- **Azure OpenAI account** (API key + endpoint)
- **MongoDB Atlas** (free tier) or another MongoDB cluster

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

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit UI (app.py)                   │
│  [New Search]  │  [Knowledge Base]  │  [Source Filtering]       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent pipeline (AutoGen)                   │
│                                                                 │
│   Scout ──► Matcher ──► Critic ──► Architect                    │
│     │          │           │            │                       │
│     │     (mapping)   (refine if        │                       │
│     │                 confidence<0.8)   ▼                       │
│     │                         ResearchReport + ActionPlan       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Librarian (MongoDB)  │  collect_sources (ddgs)  │  draw_analogy│
└─────────────────────────────────────────────────────────────────┘
```

| Agent | Role |
|-------|------|
| **Scout** | Extracts logical property graphs from texts |
| **Matcher** | Aligns nodes between the two graphs |
| **Critic** | Validates mapping consistency and confidence |
| **Architect** | Synthesizes the report and technical action plan |
| **Visionary** | (Researcher Mode) Suggests a source domain for a given problem |
| **Librarian** | Stores and retrieves reports in MongoDB |

---

## Project Structure

```
Analogy-Engine/
├── app.py                 # Streamlit UI (interface + pipeline)
├── main.py                # Alternative entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template (no secrets)
├── LICENSE                # MIT License
├── assets/
│   ├── analogy_map.png    # Example analogy map
│   └── maps/              # Generated graphs (current_display.png)
├── agents/
│   ├── scout.py           # Graph extraction
│   ├── matcher.py         # Node alignment
│   ├── critic.py          # Validation
│   ├── architect.py       # Synthesis + Action Plan
│   ├── visionary.py       # Source domain suggestion
│   └── librarian.py       # MongoDB storage
├── core/
│   ├── config.py          # Environment variable loading
│   └── schema.py          # Pydantic models (ResearchReport, etc.)
├── scripts/
│   ├── visualize_analogy.py   # Graph generation
│   ├── verify_quality.sh      # Quality checks
│   └── check_docs.py          # Documentation checks
├── config/
│   └── pre-commit-config.yaml
└── .github/workflows/
    └── quality.yml        # CI (ruff, mypy, pip-audit)
```

---

## Example Queries (Doctoral Level)

### Dual Domain Mode

- **Source:** *Biological neural networks learn through synaptic plasticity (STDP) with precise temporal windows.*  
- **Target:** *Memristor-based neuromorphic architectures reproduce analog computation and plasticity with ultra-low energy consumption.*

### Researcher Mode

- *Which principles from natural ecosystems (resilience, redundancy, emergence) can be formally transferred to the design of fault-tolerant, self-organizing distributed systems?*
- *How can immune memory mechanisms (clonal selection, adaptive memory) inspire anomaly detection and cyberdefense architectures with continuous learning?*

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
| `Configuration error` on launch | Ensure `.env` exists and contains `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `MONGODB_URI` |
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
