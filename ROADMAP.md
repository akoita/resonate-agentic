# Roadmap

Now / Next / Later view. The detailed backlog lives in [BACKLOG.md](BACKLOG.md); the rationale
lives in [STATUS.md](STATUS.md), [TECH_DEBT.md](TECH_DEBT.md), and [docs/adr/](docs/adr/).

Legend: ✅ done · 🔜 in progress / next · 🧭 planned · 🔒 blocked (needs a decision/auth)

## ✅ Done

- **Phase 0 — make it run.** Async tools, verified ADK Workflow routing/state, runtime tests. ([STATUS](STATUS.md))
- **Backend integration strategy** — reuse via MCP + OpenAPI + x402, verified live. ([ADR-0001](docs/adr/ADR-0001-backend-reuse-vs-reimplement.md))
- **Feature scope** — compute-vs-data split; DJ re-pointed to public catalog. ([ADR-0002](docs/adr/ADR-0002-feature-scope-compute-vs-data.md))
- **Portability stance** — Gemini Enterprise priority, not lock-in. ([ADR-0003](docs/adr/ADR-0003-runtime-and-model-portability.md))
- **Agentic dev harness** — AGENTS.md, skills, guardrails, CI, this roadmap. ([docs/AGENTIC_SDLC.md](docs/AGENTIC_SDLC.md))
- **MCP toolset wired** — ADK `McpToolset` → backend `/mcp` (catalog + commerce). (BL-01, [#7](https://github.com/akoita/resonate-agentic/issues/7), PR #26)
- **Budget guardrail** — spend enforced via ADK `before/after_tool_callback` on purchase tools. (BL-04, [#10](https://github.com/akoita/resonate-agentic/issues/10), PR #28)
- **7-stem-type fix** — `STEM_TYPES` includes `original`; schemas/instructions/README updated. (BL-09, [#15](https://github.com/akoita/resonate-agentic/issues/15))

## 🔜 Now (current focus)

| | Item | Why | Ref |
|---|---|---|---|
| 🔜 | Generate typed client from `/openapi.json` for public read paths | Kill route drift | BL-02 |
| 🔜 | x402 proof (in-app x402 client) → one live 0.05-USDC purchase (needs testnet wallet) | Core value prop works | BL-03 |
| 🔜 | Agent Runtime deploy track: ADR-0006 → deploy entrypoint (#21 → #22, after #23) | Eval-gated deploys | — |

## 🧭 Next

| | Item | Ref |
|---|---|---|
| 🧭 | Eval harness (trajectory + final-response) per workflow, wired into CI as a gate | BL-05 |
| 🧭 | Observability: Cloud Trace + structured logs (portable behind config) | BL-06 |
| 🧭 | Managed Sessions/Memory behind config with in-memory fallback (replace `InMemoryRunner`) | BL-07 |
| 🧭 | Deploy recipes — **source-based Agent Runtime** per [ADR-0006](docs/adr/ADR-0006-agent-ops-deployment-model.md) (here: `AdkApp` + `deploy.py` + evalsets; CD in [resonate-agentic-iac](https://github.com/akoita/resonate-agentic-iac)); image path = Cloud Run fallback only | BL-08 |

## 🧭 Later

| | Item | Ref |
|---|---|---|
| 🧭 | Secret Manager + Workload Identity (when deploying to GCP) | BL-10 |
| 🧭 | LiteLLM (non-Gemini) model example to prove portability | BL-11 |
| 🧭 | Harden: idempotent purchases, rate limiting, privacy review | BL-12 |

## 🔒 Blocked — needs your decision

| | Item | Blocker | Ref |
|---|---|---|---|
| 🔒 | DJ via backend scorer, artist upload, analytics, community | JWT flows aren't in the public agent contract; no agent auth path exists | BL-13 → ADR-0004 (auth) |

> The DJ already works in compute-bound mode on the public catalog; "via backend scorer" is the
> richer, blocked variant. Resolve by extending the backend's public/MCP contract + an agent auth path.
