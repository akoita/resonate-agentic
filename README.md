# Resonate Agentic

An **agentic-first** reimplementation of [Resonate](https://github.com/akoita/resonate) —
a machine-first audio licensing platform — built on **Google ADK 2.0**. Artists monetize
stems as programmable IP; agents discover, quote, purchase, and prove usage rights.

> Status: **early prototype**. See [STATUS.md](STATUS.md) for the production-readiness
> assessment and roadmap, and [docs/GCP_AGENTIC_STACK.md](docs/GCP_AGENTIC_STACK.md) for the
> GCP target architecture.

## Architecture

```
root_agent (LLM router)
├── catalog_agent      discovery: search / browse / stem info / quote
├── dj_agent           AI DJ: taste analysis, recommendations, sessions
├── commerce_agent     payments: x402 purchase, listings, budget
├── artist_agent       uploads, pricing, minting, analytics
├── community_agent    rooms, cohorts, Shows campaigns
└── 3 graph Workflows  discovery_purchase · artist_upload · dj_session
```

- **Tools** (`app/tools/`) call the Resonate backend over HTTP. All I/O tools are native
  `async def` (ADK awaits them directly). A few tools are still **stubs** — marked with
  `"stub": True` in their output (see STATUS.md §2).
- **Workflows** (`app/workflows/`) are ADK `Workflow` graphs: function nodes, conditional
  routing via `Event(route=...)`, shared state via `Event(state=...)` / `ctx.state`.

## Setup

Requires Python 3.11+. This repo uses Poetry, but a plain venv + `requirements.txt` works too.

```bash
# Option A — Poetry
poetry install --with dev
cp .env.example .env        # fill in GOOGLE_API_KEY (or Vertex AI vars) + RESONATE_API_BASE

# Option B — venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install pytest pytest-asyncio respx
```

### Configuration (`.env`)

| Var | Purpose |
|-----|---------|
| `RESONATE_API_BASE` | Resonate backend base URL (default `http://localhost:3000`) |
| `RESONATE_API_KEY` | Bearer token for the backend (optional) |
| `GOOGLE_API_KEY` | Gemini via AI Studio (local dev) |
| `GOOGLE_GENAI_USE_VERTEXAI` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` | Gemini via Vertex AI (production) |
| `AGENT_MODEL` | Model id (default `gemini-2.5-flash`) |

## Run

```bash
# Interactive dev UI / API (ADK)
adk web app            # browser playground
adk run app            # terminal chat

# Tests (no backend or LLM credentials required — backend is mocked)
pytest -q
```

## Tests

`tests/` proves the runtime contract offline:
- async tools execute inside ADK's event loop (the original `run_until_complete` bug),
- the Workflow engine routes branches and passes state with our exact node patterns,
- all agents + workflows + the root agent construct.

The three real workflows reach a Gemini `LlmAgent` node early, so a full end-to-end run of
those needs live model credentials; the engine itself is covered offline.
