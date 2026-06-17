# Contributing to Resonate Agentic

Thanks for your interest! This is an **experimental** project — issues, ideas, and PRs are welcome.

> The agent/contributor rules of the road live in **[AGENTS.md](AGENTS.md)** (the harness) and
> **[docs/AGENTIC_SDLC.md](docs/AGENTIC_SDLC.md)**. Pick work from **[BACKLOG.md](BACKLOG.md)**.

## Development setup

```bash
poetry install --with dev          # or: pip install -r requirements.txt + dev tools
cp .env.example .env               # add GOOGLE_API_KEY (or Vertex) + RESONATE_API_BASE
```

## Before opening a PR

```bash
ruff check app tests               # lint must pass
pytest -q                          # tests must pass (offline; no creds needed)
```

- Keep tools **`async`** and route HTTP through `app/tools/_http.py` (see [STATUS.md](STATUS.md) for why).
- **Reuse the backend; don't reimplement domain logic** — read [ADR-0001](docs/adr/ADR-0001-backend-reuse-vs-reimplement.md) and [ADR-0002](docs/adr/ADR-0002-feature-scope-compute-vs-data.md) first.
- Significant design changes should land as a new ADR under `docs/adr/`.
- Match the surrounding code style; add a test for new behaviour where practical.

## Reporting issues

Open a GitHub issue with steps to reproduce, expected vs actual behaviour, and your environment (Python version, ADK version). For anything security-sensitive, please disclose privately rather than in a public issue.
