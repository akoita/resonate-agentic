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

## Live verification (the staging backend, 2026-06-17)

Interrogated the deployed staging backend (read-only). It confirms the source analysis **and
sharpens the contract boundary**:

- **MCP** live at `POST /mcp` (streamable-http, protocol `2025-11-25`), discovery at
  `/.well-known/mcp.json` — exactly 3 tools: `catalog.search` (auth none/free), `stem.quote`
  (none/free), `stem.download` (`x402-tool-proof`/paid).
- **x402** live: `/.well-known/x402` + `/api/x402/public-config` → network `eip155:84532`
  (Base Sepolia), **Circle USDC** `0x036cbd…`, facilitator `https://x402.org/facilitator`. A real
  `GET /api/stems/{id}/x402` with no payment returns **HTTP 402** + a `payment-required` header
  carrying a base64 x402-v2 challenge (`scheme: exact`, `amount: "50000"` = 0.05 USDC @ 6 dp,
  `payTo` = the public payout address). The well-known explicitly states *"the generic payment
  router is an internal backend boundary"* — matching the responsibility split below.
- **OpenAPI** (`/openapi.json`, 3.1.0) publishes **only 10 public read paths** — storefront,
  catalog, stem-pricing, and the two x402 endpoints — with **empty `securitySchemes`**.
- **The JWT features are NOT in the external contract.** `GET /recommendations/{id}`,
  `/community/cohorts/suggestions`, `/sessions/playlist`, `/agents/config/history`, `/wallet/{id}`
  all return **401** live, and there is **no public auth endpoint** (`/auth/login`, `/auth/token`,
  `/.well-known/openid-configuration` → 404). So there's no documented way for an external agent to
  obtain a JWT today.
- Minor data note: live stems expose **7 stem types** (`vocals, drums, bass, guitar, piano, other,
  original`) — our code/docs assume 6 (missing `original`).

**Consequence for scope:** the backend's *blessed external-agent surface* is precisely
**discovery (storefront/catalog/pricing) + commerce (MCP + x402)** — no auth required. The DJ,
recommendations, wallet/budget, artist-upload, analytics, community, and shows flows sit behind
JWT with no public auth path, i.e. they are **first-party app APIs, not (yet) part of the agent
contract.**

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

## Scope decision raised by live verification

Because the JWT flows aren't in the agent contract, **scope the agentic MVP to the blessed public
loop: discover → quote → pay → download** (catalog_agent + commerce_agent on MCP + x402 + storefront,
zero auth). The DJ / artist-upload / community / analytics agents are **blocked on a decision by the
backend owner** (you): either (a) extend the public/MCP contract (and add an agent auth path) to
cover them, or (b) keep them first-party and drop them from the agentic layer for now. Track as
**ADR-0002**.

## Action Items

1. [ ] Point an ADK `McpToolset` at `$RESONATE_API_BASE/mcp`; replace the
       catalog/quote/purchase tools. (Staging is reachable — no need to run locally first.)
2. [ ] Generate a typed Python client from `/openapi.json` for the 10 public read paths
       (storefront/catalog/stem-pricing/x402-info); delete the guessed paths they replace.
3. [ ] Implement x402 proof generation for `stem.download` / `GET …/x402` — via the **agentcash MCP**
       (Base Sepolia + Circle USDC, facilitator x402.org) — and prove one live 0.05-USDC purchase.
4. [ ] Fix the 7-stem-type assumption (`…, other, original`) in schemas/instructions.
5. [ ] **ADR-0002 (scope + auth):** decide whether DJ/artist/community/analytics flows are in scope;
       if yes, get an agent auth path (none exists publicly today) before building them.
6. [ ] Defer DJ/artist/community tools until #5 is resolved; mark them clearly as first-party-gated.
7. [ ] Update TECH_DEBT.md #1 to reflect MVP-scoping + MCP/OpenAPI reuse (done).
8. [ ] Read upstream `docs/architecture/external_agent_application_contract.md` and align.
