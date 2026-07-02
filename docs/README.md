# Docs index

The map of this repo's documentation. Inspired by how [`akoita/resonate/docs`](https://github.com/akoita/resonate/tree/main/docs)
is organized — improved with an **index** (it has none) and **per-issue plans in a subdir with a
template** (it dumps `issue-*-implementation-plan.md` at the docs root).

Docs are part of the harness — treated as code: reviewed in PRs, owned, kept current. See
[AGENTIC_SDLC.md](AGENTIC_SDLC.md) and [AGENTS.md](../AGENTS.md).

## Where does X go? (the taxonomy)

| Kind | Location | What it is | Lifecycle |
|---|---|---|---|
| **Decision** | [`adr/`](adr/) | Architecture Decision Record — a *made* choice + trade-offs | short, immutable once Accepted |
| **Proposal** | `rfc/` | A design under discussion *before* a decision (graduates to an ADR) | edited until resolved |
| **Plan** | [`plans/`](plans/) | Per-issue/feature implementation plan (orchestrator-mode artifact) | lives with the issue; archived when done |
| **Runbook** | [`runbooks/`](runbooks/) | Operational procedure (deploy, rollback, incident) | living |
| **Guide / reference** | `docs/*.md` (below) | How-to + conceptual reference | living |
| **State / planning** | repo root | What's done, next, and broken | living |

**Conventions:** kebab-case filenames; one ADR/plan per file; link a plan to its issue and vice-versa;
significant changes that alter a decision get a *new* ADR (don't rewrite history).

## Index

### Decisions — [`adr/`](adr/)
- [ADR-0001](adr/ADR-0001-backend-reuse-vs-reimplement.md) — reuse the backend, don't reimplement
- [ADR-0002](adr/ADR-0002-feature-scope-compute-vs-data.md) — feature scope: compute vs data split
- [ADR-0003](adr/ADR-0003-runtime-and-model-portability.md) — runtime & model portability
- [ADR-0005](adr/ADR-0005-deployment-iac-repo-separation.md) — private IaC / control-plane repo split
- [ADR-0006](adr/ADR-0006-agent-ops-deployment-model.md) — agent-ops deployment model (Agent Runtime, source-based)
- ADR-0004 (reserved: agent auth, [#19](https://github.com/akoita/resonate-agentic/issues/19) / [#35](https://github.com/akoita/resonate-agentic/issues/35))

### Guides & strategy
- [AGENTIC_PLATFORM_STRATEGY.md](AGENTIC_PLATFORM_STRATEGY.md) — professional dev + deploy blueprint (GCP-first, portable)
- [AGENTIC_SDLC.md](AGENTIC_SDLC.md) — the engineered harness + the dev loop
- [GCP_AGENTIC_STACK.md](GCP_AGENTIC_STACK.md) — GCP agentic stack & Agent Runtime vs Cloud Run

### Plans — [`plans/`](plans/)
Per-issue implementation plans. Start from [`plans/_TEMPLATE.md`](plans/_TEMPLATE.md). See [plans/README.md](plans/README.md).

### Runbooks — [`runbooks/`](runbooks/)
Operational procedures. See [runbooks/README.md](runbooks/README.md).

### State & planning — repo root
- [STATUS.md](../STATUS.md) · [ROADMAP.md](../ROADMAP.md) · [BACKLOG.md](../BACKLOG.md) · [TECH_DEBT.md](../TECH_DEBT.md)

> Infrastructure/cloud-delivery docs live in the private [`resonate-agentic-iac`](https://github.com/akoita/resonate-agentic-iac) repo (ADR-0005).
