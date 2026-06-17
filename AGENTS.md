# AGENTS.md — Resonate Agentic harness

> Static context. Loaded every session. `CLAUDE.md` and `GEMINI.md` point here — **single source of truth.**
> Keep this lean: it is paid for on every interaction. Procedural detail lives in **skills** (dynamic context).
> **Multi-tool:** works with Claude Code, OpenAI Codex, and Gemini CLI — see [docs/AGENTIC_SDLC.md](docs/AGENTIC_SDLC.md) §Multi-tool harness.
> The engineered harness around the model is documented in [docs/AGENTIC_SDLC.md](docs/AGENTIC_SDLC.md).

## Mission

`resonate-agentic` is the **agentic layer** over the [Resonate](https://github.com/akoita/resonate)
music platform, built on **Google ADK 2.0**. It orchestrates LLM agents that discover stems, quote,
pay over **x402**, and curate music. It is a *thin orchestration layer* — the backend is the system
of record.

## Stack

Python 3.11+ · Google ADK 2.0 · `google-genai` · `httpx` · `pydantic` · Poetry.
Tests: `pytest` + `pytest-asyncio` + `respx` (backend mocked). Lint: `ruff`.

## Hard rules (never violate — these are enforced by guardrails + CI)

1. **Reuse, don't reimplement.** Never rebuild backend domain logic (payments, chain, ML, scoring). Consume MCP / OpenAPI / x402. → [ADR-0001](docs/adr/ADR-0001-backend-reuse-vs-reimplement.md)
2. **Tools are `async def`** over [`app/tools/_http.py`](app/tools/_http.py). Never `asyncio.run` / `run_until_complete` / `get_event_loop()` inside a tool (it crashes in ADK's loop).
3. **Stay portable.** No GCP-only imports (`vertexai`, `google.cloud.*`) in `app/`; model is swappable via `AGENT_MODEL`; managed services sit behind config. → [ADR-0003](docs/adr/ADR-0003-runtime-and-model-portability.md)
4. **Respect contract scope.** Catalog / commerce / DJ run on the **public** contract (MCP + x402); JWT flows (upload, analytics, community) are first-party-gated. → [ADR-0002](docs/adr/ADR-0002-feature-scope-compute-vs-data.md)
5. **No secrets, tokens, or deployment hostnames in the repo.** Config via env only (`.env`, never committed). Use the `$RESONATE_API_BASE` placeholder in docs.
6. **Branch + PR only.** Never commit to `main`. End AI-authored commits with the `Co-Authored-By` trailer.
7. **No silent partial features.** A tool that doesn't really do the work must self-flag `"stub": True` in its output.
8. **Tests + evals are the contract.** Change behavior → add/adjust a test. Prefer writing the test before the code.

## Workflow (the loop)

`plan → branch → implement → make check → PR → AI review (/code-review) → human review → merge`

- `make check` = `ruff` + `pytest` + `guardrails` (must be green before PR).
- Significant decisions become a numbered ADR in `docs/adr/`.

## Context map (where knowledge lives)

| Context type | Location |
|---|---|
| Instructions (static) | this file |
| Knowledge | [docs/](docs/) — ADRs, [GCP stack](docs/GCP_AGENTIC_STACK.md), [STATUS](STATUS.md), [ROADMAP](ROADMAP.md), [TECH_DEBT](TECH_DEBT.md) |
| Skills (dynamic) | [`.agents/skills/`](.agents/skills/) — canonical `SKILL.md`, loaded on demand. Claude reads via `.claude/skills →` symlink; Codex reads `.agents/skills` natively; Gemini via [`.gemini/commands/`](.gemini/commands/) |
| Tools | [`app/tools/`](app/tools/) + the backend MCP/OpenAPI/x402 contract |
| Memory / decisions | [`docs/adr/`](docs/adr/) · state in STATUS / ROADMAP |
| Guardrails / hooks | [`scripts/harness_guardrails.py`](scripts/harness_guardrails.py) · `.pre-commit-config.yaml` · `.github/workflows/` |

## Conventions

- Tools return a `dict` with a `"status"` key; typed I/O uses Pydantic models in `app/schemas.py`.
- Match the surrounding style; keep functions small and readable.
- Keep this file lean — push how-to detail into a skill under `.claude/skills/`.

## When the agent makes a mistake

Add a rule here **or** a check in `scripts/harness_guardrails.py` so it cannot recur.
Most agent failures are *configuration* failures (a missing tool, a vague rule, an absent guardrail) —
fix the harness, not just the symptom.
