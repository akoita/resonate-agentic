# ADR-0005: Separate private IaC / cloud-delivery repository

**Status:** Accepted
**Date:** 2026-06-17
**Deciders:** Project owner (akoita)
**Builds on:** [ADR-0003](ADR-0003-runtime-and-model-portability.md)
**Note:** ADR-0004 is reserved for the agent-auth decision (see [#19](https://github.com/akoita/resonate-agentic/issues/19)).

## Context

`resonate-agentic` is **public** and **agent-edited** (agents routinely open PRs here). It will soon
need cloud deployment (Agent Runtime / Cloud Run), which brings cloud credentials, IAM, Secret
Manager wiring, and Terraform state into play. The org already uses an `app` + `*-iac` split
(`resonate`/`resonate-iac`, plus `fusion-prime-iac`, `agent-forge-iac`, …), all private.

Question: keep deployment/IaC in this repo, or split it into a separate private repo?

## Decision

**Split.** Cloud infrastructure and delivery live in a separate **private** repo,
**[`akoita/resonate-agentic-iac`](https://github.com/akoita/resonate-agentic-iac)**, mirroring the
`resonate` / `resonate-iac` pattern. This repo (the app) holds **no cloud credentials**.

| `resonate-agentic` (public app) | `resonate-agentic-iac` (private) |
|---|---|
| App source, ADK agents, skills, AGENTS.md harness | Terraform (`environments/`, `modules/`) |
| App CI: lint · test · guardrails | Cloud CD: plan/apply, deploy |
| Build image + emit deploy *intent* | WIF, deployer/runtime SAs, IAM, Secret Manager, TF state |
| **No cloud creds** | Auth via Workload Identity Federation (no static keys) |

**Cross-repo contract** (mirrors `resonate` ↔ `resonate-iac`): the app sends deploy intent via
`repository_dispatch` (`resonate_agentic_deploy`); the IaC repo's receiver applies it only when
`AUTO_DEPLOY_ENABLED=true`, **prod is manual-only**. See the IaC repo's
`docs/cross-repo-deploy-contract.md`.

## Why (sharper than the generic case)

1. **Public surface** — IAM, WIF config, secret references, and TF state must not be public.
2. **Agent-edited surface** — with deploy creds absent from this repo, an agent PR (or external
   contributor) **cannot** escalate cloud privileges or exfiltrate credentials. The boundary is
   structural, not procedural.
3. **Timing** — this repo holds zero cloud creds today (only the optional `ANTHROPIC_API_KEY` for PR
   review). We set the boundary *before* any cloud secret would ever land here.
4. **Org consistency** — same pattern as the other `*-iac` repos.

## Options considered

- **A. Separate private IaC repo (chosen).** Strong isolation, matches org pattern. Cost: two-repo
  coordination for changes that span app + infra.
- **B. `infra/` dir in this repo + scoped CI.** Less overhead, but cloud config sits in a public,
  agent-edited repo — exactly what we want to avoid.
- **C. No IaC, click-ops.** Not reproducible; rejected.

## Consequences

- **Easier:** least-privilege CI; app repo never needs cloud-admin; infra reviewed with stricter
  rigor; portability preserved (target-specific provisioning stays out of the app — ADR-0003).
- **Harder:** changes spanning both repos need coordination via the dispatch contract; a small
  sender workflow lives here.
- **Backlog impact:** BL-08 (deploy recipes) and BL-10 (Secret Manager + WIF) are **owned by the
  IaC repo**; this repo keeps only the build + deploy-intent sender.

## Action items

1. [x] Create private `resonate-agentic-iac` (Terraform + gated CD + WIF).
2. [x] Add a gated `deploy-dispatch` sender workflow here (no-ops without `IAC_DISPATCH_TOKEN`).
3. [ ] Add the app **build** (Dockerfile + image push) feeding the dispatch (part of BL-08).
4. [ ] Keep cloud creds out of this repo permanently (guardrail candidate).
