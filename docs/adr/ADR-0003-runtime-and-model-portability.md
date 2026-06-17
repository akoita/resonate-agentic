# ADR-0003: Runtime & model portability — Gemini Enterprise is priority, not a lock-in

**Status:** Accepted
**Date:** 2026-06-17
**Deciders:** Project owner (akoita)
**Relates to:** [ADR-0001](ADR-0001-backend-reuse-vs-reimplement.md), [docs/GCP_AGENTIC_STACK.md](../GCP_AGENTIC_STACK.md)

## Context

The project's GCP guide and early branding read as if **Gemini Enterprise Agent Runtime** were the
*only* home for this agent. The owner's intent is different: Gemini Enterprise is the **priority**
target, but deployment to **other AI / agentic environments** is an explicit goal and must not be
blocked. We want the strengths of the managed GCP runtime *when we use it*, without architecting
ourselves into a corner.

## Decision

**Treat Gemini Enterprise (Agent Runtime) as the priority deployment target, and keep every layer
portable so the same agent runs elsewhere with only configuration changes — no code rewrite.**

Portability is preserved at four layers:

1. **Framework — open-source ADK.** ADK (Apache-2.0) is plain Python; it has no hard runtime
   dependency on GCP. The agent runs locally (`adk run` / `adk web`) and in any container host.
2. **Runtime — pluggable.** Priority: **Agent Runtime** (managed sessions/memory/tracing).
   Alternatives with no code change: **Cloud Run**, **GKE**, another cloud's container/serverless
   platform, or self-hosted. The only runtime-specific pieces (managed Session/Memory services) sit
   behind ADK service interfaces, so they're swap-in/swap-out.
3. **Models — swappable via `AGENT_MODEL`.** Gemini through AI Studio *or* Gemini Enterprise, or
   **any provider** (OpenAI, Anthropic, local/OSS) through ADK's LiteLLM integration. No hard-coded
   model assumptions in agent logic.
4. **Interop — open standards.** The agent consumes **MCP** and can expose **A2A**, so it composes
   with non-Google agentic ecosystems; the Resonate backend is reached over an open contract
   (MCP · OpenAPI · x402) regardless of where the agent runs.

### Guardrails to keep it true

- Don't import GCP-only SDKs in `app/` core logic; isolate any managed-service wiring (e.g.
  `VertexAiSessionService`) behind config/factory selection with a non-GCP default for local runs.
- Keep secrets/config provider-agnostic (env-driven today; Secret Manager is one *option*).
- Prefer ADK + open-standard abstractions over provider-native features in the agent layer; when a
  managed feature is a big win (Agent Runtime sessions/memory, Model Armor), adopt it *behind* an
  interface and document the portable fallback.

## Consequences

- **Easier:** demoing/deploying on Cloud Run, another cloud, or locally; swapping models for cost or
  availability; avoiding vendor lock-in concerns for adopters.
- **Harder:** we forgo some "free" depth from going all-in on one platform (e.g. we must provide a
  non-GCP session/memory path); a little extra config surface and abstraction.
- **Revisit when:** a managed Gemini Enterprise capability becomes compelling enough to hard-depend
  on — at which point this ADR is the place to record the trade-off.

## Action Items

1. [ ] When wiring managed sessions/memory (Phase 2), select the backend by config with an
       in-memory/Firestore fallback for non-Agent-Runtime hosts.
2. [ ] Add a LiteLLM-based model example to docs so non-Gemini deployment is a documented path.
3. [ ] Keep `app/` free of GCP-only imports; add a lint/CI check if practical.
4. [ ] Optionally add a Cloud Run / generic-container deploy recipe alongside the Agent Runtime one.
