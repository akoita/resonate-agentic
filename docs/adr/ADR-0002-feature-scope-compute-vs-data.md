# ADR-0002: Keep all agentic features via a compute-vs-data split (reuse, don't reimplement)

**Status:** Accepted
**Date:** 2026-06-17
**Deciders:** Project owner (koita)
**Builds on:** [ADR-0001](ADR-0001-backend-reuse-vs-reimplement.md)

## Context

ADR-0001 established: reuse the Resonate backend as system of record; its **public, auth-free
agent contract** (verified live on the staging backend) is **discovery (storefront/
catalog/pricing) + commerce (MCP + x402)**. The DJ, taste/recommendations, wallet/budget, artist
upload, analytics, community, and shows endpoints are **JWT-gated and absent from the public
contract**, with no public auth path.

Open question: to **keep all five specialist agents + three workflows**, is it better to
reimplement/adapt backend logic *inside* the agentic project, or reuse the existing backend with
adaptation on both sides?

## Decision

**Reuse + targeted adaptation. Never reimplement backend domain logic.** The right boundary is not
a side of the wire but the *nature of each feature*:

- **Compute-bound** (the logic is the value; inputs are public) → **adapt agent-side**; keep the
  feature with **no backend auth**.
- **Data / identity-bound** (the value is data, assets, or a user identity living in the backend)
  → **reuse the backend**; cannot be meaningfully reimplemented (no data/audio/Demucs/chain
  without it), so these require an agent **auth path** to unlock.

Reimplementing never *keeps* an otherwise-lost feature: the gated features are gated because their
**data lives in the backend**, so a rebuilt copy is an empty shell — and for features that already
work it just creates a second source of truth that drifts.

### Per-feature mapping

| Feature / agent | Nature | Approach | Auth | Works now |
|---|---|---|---|---|
| Catalog discovery | data (public) | Reuse MCP `catalog.search` / storefront | none | ✅ |
| Commerce / purchase | data + payment (public) | Reuse MCP `stem.download` + x402 (agentcash) | x402 proof | ✅ |
| **DJ / taste / recs** | **compute** | **Adapt agent-side** — LLM curation over public `catalog.search` + `stem.quote` | none | ✅ |
| **Budget / spend caps** | **compute** | **Adapt agent-side** — ADK `before_tool` callbacks + session state on the agent wallet | none | ✅ |
| Artist upload | data + assets + identity | Reuse `/ingestion` (Demucs/storage) | JWT | ⛔ |
| Artist analytics | server-owned data | Reuse `/analytics` | JWT | ⛔ |
| Community / cohorts | social-graph data | Reuse `/community` | JWT (mostly) | ⛔ |
| Shows campaigns | data | Reuse `/shows` (some public) | partial | ◐ |

## Consequences

- **All five agents stay in the architecture.** Four become genuinely functional against staging
  almost immediately (catalog, commerce, DJ, budget); none require rebuilding payments/chain/ML/
  storage.
- The **DJ becomes LLM-native over the public catalog** (this ADR's code change): no backend
  session/taste/recommendation calls, taste inferred by the LLM, budget enforced agent-side. The
  backend's own server-side scorer becomes an optional future enhancement, not a dependency.
- Only **upload / analytics / community** remain blocked — and *only* an agent auth path unlocks
  them (reimplementation cannot). They stay as clearly-labelled, first-party-gated stubs until then.
- New dependency: an **agent auth/token strategy** for the data-bound features (token source,
  scope, refresh). Tracked as a follow-up (ADR-0003 when those features are scheduled).

## Action Items

1. [x] Re-point the `dj_session` workflow to public `catalog.search` + LLM selection + agent-side
       budget (no JWT). *(this change)*
2. [x] Re-point the `dj_agent` specialist to public discovery/quote tools only.
3. [ ] Enforce budget as an ADK `before_tool_callback` on purchase tools (commerce path).
4. [ ] Keep `artist_agent` / `community_agent` tools, but label upload/analytics/community as
       first-party-gated until an auth path exists.
5. [ ] When upload/analytics/community are scheduled, write ADR-0003 (agent auth strategy).
