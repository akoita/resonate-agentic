# Agentic SDLC — the engineered harness

How this repo is set up for **agentic engineering** (not ad-hoc vibe coding). The structure follows
the *factory model* and *harness engineering* from Google's _The New SDLC with Vibe Coding_
(Osmani, Saboo, Kartakis, 2026): the developer's primary output is **the system that builds the
software** — specifications, agents, tests/evals, feedback loops, and guardrails.

> `Agent = Model + Harness.` The model is one input. Everything below is the harness — and it is
> *our* surface area to own, version, and review like code.

## The harness, mapped to this repo

| Harness component | Where it lives | Notes |
|---|---|---|
| **Instructions / rule files** | [`AGENTS.md`](../AGENTS.md) (→ `CLAUDE.md`, `GEMINI.md`) | Lean **static context**: mission, stack, hard rules, workflow, context map. |
| **Skills** (dynamic context) | [`.claude/skills/`](../.claude/skills/) | Procedural knowledge loaded **on demand** via progressive disclosure — keeps static context lean. |
| **Tools** | [`app/tools/`](../app/tools/) + backend MCP/OpenAPI/x402 | Async tools over a shared HTTP client; the agent-commerce core comes from the backend's MCP. |
| **Orchestration** | [`app/agent.py`](../app/agent.py), [`app/workflows/`](../app/workflows/) | LLM router + specialist sub-agents + ADK `Workflow` graphs. |
| **Guardrails / hooks** | [`scripts/harness_guardrails.py`](../scripts/harness_guardrails.py), `.pre-commit-config.yaml`, `.claude/settings.json` | Deterministic checks at lifecycle points (pre-commit, CI, on-stop). |
| **Tests & evals** | [`tests/`](../tests/) + eval harness (planned, BL-05) | Tests check determinism; evals check trajectory + final response. |
| **Observability** | Cloud Trace + logs (planned, BL-06) | Token/latency/drift visibility before scale. |
| **CI/CD** | [`.github/workflows/`](../.github/workflows/) | Lint, test, guardrails, security, AI review, deploy. |

## Context engineering: static vs. dynamic

Static context is paid for on **every** interaction, so we keep it small and push detail outward:

- **Static** (always loaded): `AGENTS.md` — who the agent is and the rules it cannot break.
- **Dynamic** (loaded on match): skills in `.claude/skills/`, tool results, docs/ADRs fetched on demand.

The six context types (instructions · knowledge · memory · examples · tools · guardrails) are mapped
in the **Context map** table of `AGENTS.md`. The static/dynamic boundary is a first-class decision —
reviewed in PRs like any config.

## The loop (think → act → observe)

```
plan ─► branch ─► implement ─► make check ─► PR ─► AI review (/code-review) ─► human review ─► merge
                     ▲                │
                     └──── feedback ◄─┘   (tests/evals + guardrails route failures back)
```

- `make check` = `ruff` + `pytest` + `guardrails`. The same gate runs in CI.
- Failures are routed back to the agent as the feedback signal — the heart of self-correction.

## Conductor vs. orchestrator

- **Conductor** (real-time, in-editor): complex logic, debugging, unfamiliar code — you direct each change.
- **Orchestrator** (async, delegated): well-specified tasks (a BACKLOG item, a migration, test/eval gen)
  handed to an agent that runs `make check` and opens a PR.

Match the mode to the task. Either way, **review every line that ships** and watch for the *80% problem*:
AI nails the bulk; the edge cases, error handling, and integration points need human judgment.

## Quality flywheel (planned, BL-05)

`evaluate → diagnose (cluster root causes) → optimize (prompt/tool/skill) → verify (regression) → monitor`.
The bar for shipping an agent into a shared workflow is a **passing eval with an explicit rubric**, not a demo.

## How we improve the harness

When the agent does something it shouldn't: add a rule to `AGENTS.md` **or** a check to
`scripts/harness_guardrails.py`. Most agent failures are configuration failures — fix the harness,
not just the symptom. Treat `AGENTS.md`, skills, evals, and guardrails as code: reviewed, versioned, owned.
