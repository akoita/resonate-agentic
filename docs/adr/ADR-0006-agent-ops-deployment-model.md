# ADR-0006: Agent-ops deployment model (Agent Runtime, source-based, cross-repo)

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Project owner (akoita)
**Builds on:** [ADR-0003](ADR-0003-runtime-and-model-portability.md) (portability) · [ADR-0005](ADR-0005-deployment-iac-repo-separation.md) (repo split)
**Tracked by:** [#21](https://github.com/akoita/resonate-agentic/issues/21) · consumed by [#22](https://github.com/akoita/resonate-agentic/issues/22) and `resonate-agentic-iac` #1–#6

## Context

ADR-0005 split cloud delivery into the private `resonate-agentic-iac` repo, framed as classic IaC
(Terraform + image build + deploy dispatch). The primary target, **Agent Runtime** (GCP Agentic
Platform), turns out not to fit that framing: it is **source-based** — the standard path packages
the agent from source with `agents-cli` / an `AdkApp` entrypoint and deploys via the platform SDK,
with **no Dockerfile and no `gcloud run deploy`**. Its lifecycle is also richer than
build-and-ship: evals gate releases, deployments are promoted, agents are published to Gemini
Enterprise, and traffic is observed via Trace + BigQuery.

Question: how do we deploy/manage the agent on Agent Runtime while keeping the ADR-0005 boundary
(no secrets or cloud creds in this public, agent-edited repo)?

## Decision

Reframe `resonate-agentic-iac` as an **agent-deployment control plane**, not classic IaC, and
adopt the platform's source-based flow:

1. **Source-based deploys.** The deploy artifact is source, not an image:
   `agent_runtime_app.py` (`AdkApp`: `set_up`, `register_operations`, `async_stream_query`) +
   `app/app_utils/deploy.py`, run via `uv run -m app.app_utils.deploy`. Standard tooling is
   **`agents-cli`**. No Dockerfile, no `gcloud` in the deploy path.
2. **Lifecycle = agent-ops.** `build/package → eval gate → deploy (staging) → manual promote
   (prod) → publish (Gemini Enterprise) → observe (Trace + BigQuery)`. Rollback is **git-based**:
   redeploy the prior `release_sha` (source-based deploys make the SHA the artifact).
3. **Cross-repo reconciliation (ADR-0005 stands).** `agents-cli` is single-repo-opinionated, so
   the split is by *artifact kind*:
   - **This repo (app)** keeps the *source* deploy artifacts — `AdkApp` entrypoint, `deploy.py`,
     evalsets, lockfile/export (`.requirements.txt`). **No secrets, no Terraform, no IAM**
     (guardrails enforce this).
   - **IaC repo CD** checks out this repo at a pinned **`release_sha`** and runs the source-based
     deploy, authenticated via **WIF** — no static keys anywhere.
4. **Identity & state on the platform.**
   - Service-account split: **`app_sa`** (runtime identity) vs **`cicd_runner_sa`** (CD identity).
   - Secrets via **Secret Manager**, granted to the Agent Runtime managed SA — never env-at-rest.
   - Managed sessions via **`VertexAiSessionService`** (replaces the per-call `InMemoryRunner`,
     TECH_DEBT #9 / [#13](https://github.com/akoita/resonate-agentic/issues/13)) — behind config
     with an in-memory fallback, per ADR-0003.

## Options considered

- **A. Source-based Agent Runtime deploy, cross-repo (chosen).** Platform-native, minimal
  artifacts, eval-gated; keeps the ADR-0005 security boundary.
- **B. Containerize + Cloud Run as primary.** Portable (and stays as the fallback target per
  ADR-0003), but forfeits managed sessions/tracing/publishing that Agent Runtime provides, and
  makes the eval-gated lifecycle bespoke.
- **C. Deploy from this repo directly (agents-cli's default single-repo flow).** Simplest, but
  puts WIF/SA config in a public, agent-edited repo — rejected by ADR-0005's reasoning.

## Consequences

- **Easier:** deploys are reproducible from a SHA; evals become a release gate (pulls
  [#11](https://github.com/akoita/resonate-agentic/issues/11) onto the critical path); managed
  sessions/observability come with the platform rather than bespoke wiring.
- **Harder:** the app must stay importable/runnable under the platform's pinned **Python 3.12**
  ([#23](https://github.com/akoita/resonate-agentic/issues/23), CI matrix); cross-repo releases
  need the pinned-SHA contract; `agents-cli` scaffolding must be pruned to source-only artifacts
  here ([#22](https://github.com/akoita/resonate-agentic/issues/22)).
- **Supersedes:** the generic "build image + dispatch" framing of BL-08 for the Agent Runtime
  target. The image path remains only as the Cloud Run fallback (ADR-0003). ADR-0005's dispatch
  contract stays, carrying `release_sha` as the payload.

## Action items

1. [ ] App repo: add the source deploy artifacts (`AdkApp` + `deploy.py` via
   `agents-cli scaffold enhance`, pruned to source-only) — [#22](https://github.com/akoita/resonate-agentic/issues/22).
2. [ ] App repo: CI green on Python 3.12 — [#23](https://github.com/akoita/resonate-agentic/issues/23) (PR #31).
3. [ ] IaC repo: CD that checks out the pinned `release_sha` and runs the source-based deploy via
   WIF (`cicd_runner_sa`) — resonate-agentic-iac #3.
4. [ ] Eval gate before deploy — [#11](https://github.com/akoita/resonate-agentic/issues/11).
