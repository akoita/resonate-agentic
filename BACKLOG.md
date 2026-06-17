# Backlog

Source of truth for actionable work. Group by horizon in [ROADMAP.md](ROADMAP.md). Each item is
sized for an agent task (one PR). `make check` must pass before any item is closed.

> Convert to GitHub Issues with `gh issue create` (templates in `.github/ISSUE_TEMPLATE/`).
> Labels: `now` / `next` / `later` / `blocked`, plus area labels (`commerce`, `dj`, `infra`, `eval`, `docs`).

| ID | Item | Horizon | Area | Refs / acceptance |
|----|------|---------|------|-------------------|
| BL-01 | Replace catalog/quote/purchase tools with an ADK `McpToolset` on `$RESONATE_API_BASE/mcp` | now | commerce | ADR-0001 · catalog/commerce tests still green |
| BL-02 | Generate a typed Python client from `/openapi.json`; wrap public read paths; delete guessed paths | now | infra | ADR-0001 · client regenerates via script |
| BL-03 | x402 proof generation via agentcash MCP; prove one live 0.05-USDC `stem.download` | now | commerce | ADR-0001 · receipt asserted in a (gated) integration test |
| BL-04 | Budget enforcement as an ADK `before_tool_callback` on purchase tools | now | commerce | TECH_DEBT · denies over-budget purchase in a test |
| BL-05 | Eval harness: trajectory + final-response evals per workflow, with rubrics; CI gate | next | eval | whitepaper "set the bar at the eval" · `make eval` runs |
| BL-06 | Observability: Cloud Trace + structured logging behind config (portable) | next | infra | ADR-0003 · no-op locally, on in prod |
| BL-07 | Managed Sessions/Memory behind a factory with in-memory fallback; drop per-call `InMemoryRunner` | next | infra | TECH_DEBT #9 · ADR-0003 guardrail |
| BL-08 | Deploy recipes: Agent Runtime (priority) + Cloud Run (portable) | next | infra | ADR-0003 · `make deploy` documented |
| BL-09 | Fix the 7-stem-type assumption (`vocals…other,original`) in schemas/instructions | next | docs | matches live storefront |
| BL-10 | Secret Manager + Workload Identity for GCP deploys | later | infra | no secrets in env at rest |
| BL-11 | LiteLLM (non-Gemini) example to demonstrate model portability | later | docs | ADR-0003 |
| BL-12 | Harden: idempotent purchases, rate limiting, privacy review | later | infra | — |
| BL-13 | DJ-via-backend-scorer + artist upload + analytics + community | blocked | dj/community | needs ADR-0004 (agent auth) |

## Definition of done (every item)

1. `make check` green (lint + tests + guardrails).
2. Behavior change → test/eval added or updated.
3. New decision → ADR added.
4. No new hard-rule violation (AGENTS.md).
5. PR reviewed (AI first-pass via `/code-review`, then human).
