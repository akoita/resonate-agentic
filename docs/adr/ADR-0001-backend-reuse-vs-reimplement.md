# ADR-0001: Reuse the Resonate backend vs. reimplement domain logic in the agentic layer

**Status:** Proposed
**Date:** 2026-06-17
**Deciders:** Project owner (koita)
**Relates to:** TECH_DEBT.md #1 (unverified backend contract), #2 (x402), #8 (stub tools), #9 (sessions)

## Context

`resonate-agentic` (this repo, Python + ADK 2.0) currently talks to the Resonate backend through
**hand-written `httpx` tools with guessed REST paths**. The question: should the agentic layer
keep/expand its own backend integration logic (and how much), or reuse what the upstream backend
already provides?

Ground truth from inspecting [akoita/resonate](https://github.com/akoita/resonate) source:

- It is a **production-grade NestJS + Next.js + Solidity system**, already deployed on GCP
  (Cloud Run, Pub/Sub, Cloud SQL, Redis, GCS), with Demucs stem-separation workers and
  ERC-4337 contracts.
- It was **explicitly built for external agents**: there is an
  `docs/architecture/external_agent_application_contract.md`, an **MCP server at `POST /mcp`**
  (discovery at `/.well-known/mcp.json`), a **generated OpenAPI spec at `/openapi.json`**, and an
  **x402 discovery doc at `/.well-known/x402`**.
- The **MCP server already exposes the agent-commerce core**: `catalog.search` (free),
  `stem.quote` (free), `stem.download` (x402-paid, returns base64 audio + receipt). Auth and the
  full x402 challenge→proof→settlement→receipt flow are handled server-side.
- The backend has its **own internal "agent runtime"** (`AgentRuntimeService`,
  `AgentOrchestratorService`, `AgentNegotiatorService`, `AgentLearningService`) doing
  taste-constrained scoring, price negotiation, and taste learning — exposed via
  `POST /sessions/agent/next`, `GET /recommendations/{userId}`, `POST /agents/config/session`, etc.
- **Auth model:** storefront + x402 + MCP search/quote are **public**; `stem.download` is
  authenticated by **x402 payment proof**; sessions/recommendations/wallet/analytics/ingestion/
  cohorts require **JWT** (`@UseGuards(AuthGuard("jwt"))`), some admin-only.
- Verified path drift in our current tools: `/api/wallet/budget/{userId}` → should be
  `GET /wallet/{userId}` (read) / `POST /wallet/budget` (write); `/api/releases/upload` (JSON) →
  should be `POST /ingestion/upload` (**multipart**). Most session/recommendation/wallet calls send
  **no JWT** and would 401 in reality.

Forces at play: the backend already owns every hard part (payments, chain, ML, scoring); it is the
system of record; it changes independently of this repo; and it was designed to be consumed by
agents — but it also already has an *internal* orchestrator, so we must avoid building a second,
competing "brain."

## Decision

**Reuse the backend as the system of record. Do NOT reimplement any domain logic in the agentic
layer.** Consume the backend through its **purpose-built agent contract**, with a clear division of
responsibility:

- **Backend owns** (call, never duplicate): catalog data, pricing, x402 payments/settlement,
  receipts, NFT/chain, stem separation, **and the recommendation/negotiation/learning scoring**.
- **Agentic layer owns** (its reason to exist): the conversational LLM **router**, cross-domain
  **multi-agent orchestration** (catalog ↔ commerce ↔ artist ↔ community ↔ shows), **workflow
  graphs**, human-facing presentation, and **budget/safety guardrails as ADK callbacks**.

Concretely, integrate via three layers (in priority order):

1. **MCP-first for the agent-commerce core.** Point ADK at the existing `POST /mcp` via an ADK
   `McpToolset`; let `catalog.search` / `stem.quote` / `stem.download` replace our hand-written
   catalog + quote + purchase tools. This gets the full x402 + receipt handling for free and stays
   in lockstep with the backend's agent contract.
2. **OpenAPI-generated typed client for the rest.** Generate a client from `/openapi.json` for
   endpoints not in MCP (sessions, recommendations, analytics, ingestion, community, shows, wallet).
   Regenerate on backend changes instead of hand-maintaining paths.
3. **Thin ADK tool wrappers** only to shape ergonomics for the LLM — wrapping the generated client /
   MCP tools, never raw `httpx` with literal paths.

The DJ flow specifically **calls** `POST /sessions/agent/next` (server-side taste scorer) rather
than re-scoring in an `LlmAgent` — this simplifies `dj_session` and avoids the competing-brain risk.

## Options Considered

### Option A: Reuse via MCP + OpenAPI-generated client (thin agentic layer) — RECOMMENDED
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low–Med (consume MCP; generate client) |
| Cost | Low — no domain re-build; tracks backend automatically |
| Scalability | High — backend already scales on Cloud Run |
| Team familiarity | Med — need to learn ADK McpToolset + OpenAPI codegen |

**Pros:** zero duplication; x402/receipts/auth handled upstream; structurally kills route-drift
(#1); uses the contract the backend was *designed* to expose; least code to own.
**Cons:** couples us to backend availability + contract; JWT acquisition still required; MCP tool
set is small (3 tools) so most calls still go through the REST/OpenAPI client.

### Option B: Hand-written HTTP client, tailored — just fix the guessed routes
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low now, Med over time |
| Cost | Low upfront, recurring (manual drift) |
| Scalability | High (backend) |
| Team familiarity | High (already doing it) |

**Pros:** simplest immediate change; full control of tool signatures.
**Cons:** ignores the MCP server built for exactly this; routes drift again on every backend
change; we re-implement x402 proof handling that MCP `stem.download` already does; this is the
status quo that produced #1.

### Option C: Reimplement backend domain logic in the agentic service (fat agentic layer)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Very High |
| Cost | Very High |
| Scalability | Duplicated/uncertain |
| Team familiarity | Low (payments, chain, ML) |

**Pros:** independence from backend; could tailor everything to agents.
**Cons:** re-building payments, ERC-4337, Demucs, and a scorer is months of work, security risk,
and a second source of truth that *will* diverge. Non-starter.

## Trade-off Analysis

The decisive factors: (1) the backend is the **system of record** and already contains everything
expensive/risky to build, and (2) it **ships an explicit agent contract (MCP + OpenAPI + x402)**.
That collapses the choice — A and B both "reuse," but B leaves on the table the very interface
designed for us and keeps the manual-drift tax that created #1. C duplicates a production system.
The only real cost of A over B is the learning curve (McpToolset + codegen) and accepting backend
coupling — both acceptable, since coupling to the system of record is correct, not accidental.

The subtler decision is **responsibility split** given the backend's *own* agent runtime: we treat
that runtime as a **domain service to call** (scoring/negotiation/learning), and keep the ADK layer
as the **conversational, cross-domain orchestrator**. This prevents two orchestrators fighting.

## Consequences

- **Easier:** tool correctness (generated, not guessed); x402 purchases actually work (via MCP
  `stem.download`); backend changes flow in via regen; less code to maintain; `dj_session` simplifies.
- **Harder:** we must implement **JWT acquisition** for the authenticated endpoints (new work, see
  ADR-0002 candidate); we take a hard runtime dependency on backend availability/versioning; ADK
  `McpToolset` + OpenAPI codegen are new skills to acquire.
- **Revisit when:** the MCP tool catalog grows (more flows could move from REST→MCP); or if the
  backend's agent runtime is later exposed for external orchestration (would shrink our workflow code).

## Action Items

1. [ ] Spin up the backend locally (`docker/`, port 3000); fetch `/openapi.json` and `/.well-known/mcp.json`.
2. [ ] Replace catalog/quote/purchase tools with an ADK `McpToolset` pointed at `POST /mcp`.
3. [ ] Generate a typed Python client from `/openapi.json`; wrap session/recommendation/analytics/
       ingestion/community/shows/wallet calls over it (delete guessed paths).
4. [ ] Fix the confirmed-wrong calls: wallet (`GET /wallet/{userId}` / `POST /wallet/budget`),
       upload (`POST /ingestion/upload`, multipart).
5. [ ] Add JWT auth handling for protected endpoints (token source + refresh) — spin out as ADR-0002.
6. [ ] Repoint the DJ flow at `POST /sessions/agent/next`; remove any client-side re-scoring.
7. [ ] Update TECH_DEBT.md #1 (now "adopt MCP + OpenAPI client + JWT," lower long-term cost).
8. [ ] Read `docs/architecture/external_agent_application_contract.md` upstream and align to it.
