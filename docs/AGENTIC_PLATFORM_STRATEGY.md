# Agentic Platform Strategy

**State-of-the-art recommendation for managing professional agentic application development and
deployment — GCP-first, vendor-portable.**

> _Mid-2026 snapshot. The tools move fast; the principles and the abstraction boundary are the
> durable part. Companion to [AGENTIC_SDLC.md](AGENTIC_SDLC.md) (the harness) and the ADRs._

## TL;DR

Treat agent development as **agentic engineering**, not vibe coding: your real product is the
**system that builds and runs the agent** — specs, harness, evals, guardrails, and feedback loops
(the *factory model*). Build on **open, portable layers**; deploy **GCP-first** on managed
**Agent Runtime**; keep a clean abstraction boundary so an Anthropic- or OpenAI-native runtime later
is a **config/adapter swap, not a rewrite**.

| Layer | Recommendation (now) | Why portable |
|---|---|---|
| **Framework** | **Google ADK 2.0** (open-source, Apache-2.0; GA in Python/Go/Java/TS) | not GCP-bound; runs anywhere Python runs |
| **Models** | Gemini via Agent Runtime; swappable via **LiteLLM** | any provider (Claude, GPT, OSS) with one config |
| **Tools** | **MCP** (Model Context Protocol) | the de-facto tool standard (Linux Foundation AAIF) |
| **Agent-to-agent** | **A2A** (Agent2Agent) | open coordination standard (Linux Foundation, 150+ orgs) |
| **Runtime (priority)** | **Agent Runtime** (Gemini Enterprise Agent Platform) | managed sessions/memory/trace; sub-second cold start |
| **Runtime (portable)** | **Cloud Run** / GKE / any container host / local | same ADK app, different target |
| **Dev harness** | `AGENTS.md` + `.agents/skills/` + guardrails | one source drives Claude · Codex · Gemini CLIs |
| **Ops** | **AgentOps**: eval-gated CD, trajectory+output evals, full-trace observability | discipline, not a vendor |

The bet: **own the harness and the open standards; rent the runtime.** Runtimes are commodity and
interchangeable; the harness and evals are where durable quality lives.

---

## 1. Principles (the operating philosophy)

From Google's _The New SDLC with Vibe Coding_ (2026) and current AgentOps practice:

1. **Factory model.** Your output is the system that produces the agent, not the agent's code.
   Give agents *success criteria* (tests/evals), not step-by-step instructions.
2. **`Agent = Model + Harness`.** The model is one input; most behavior comes from the harness
   (instructions, tools, context policies, guardrails, sub-agents, observability). Most "model
   failures" are configuration failures — fix the harness.
3. **Context engineering is the skill.** Manage the static/dynamic context boundary deliberately:
   lean always-on instructions (`AGENTS.md`), procedural detail in on-demand **skills**.
4. **Evals are the contract.** Tests check determinism; **evals** check the non-deterministic parts
   (trajectory + final response). "Set the bar at the eval, not the demo."
5. **Structure scales, vibes don't.** Vibe coding is for exploration; production needs specs, tests,
   guardrails, and human oversight of architecture and correctness.

---

## 2. The professional agentic SDLC (development)

The loop, with the recommended tooling at each phase:

| Phase | Practice | Tooling |
|---|---|---|
| **Scaffold** | Start from a deployment-ready template; prototype-first | `agents-cli scaffold` |
| **Build** | ADK agents/tools/workflows; reuse backends via MCP, don't reimplement | ADK 2.0; MCP toolsets |
| **Context-engineer** | `AGENTS.md` (static) + skills (dynamic); review them like code | `.agents/skills/`, `AGENTS.md` |
| **Eval-drive** | Write the eval before the behavior; rubric-scored trajectory + output | `agents-cli eval`, ADK evalsets |
| **Review** | AI first-pass review, then human; extra scrutiny on AI-generated code | `/code-review`, PR checklist |
| **Gate** | Lint + tests + **guardrails** + eval thresholds, in CI, on every PR | `make check`, GitHub Actions |
| **Improve** | Quality flywheel: evaluate → cluster failures → optimize prompt/tool/skill → verify → monitor | evals + observability |

**Two modes, matched to the task:** *conductor* (real-time, in-editor, for complex/unfamiliar work)
and *orchestrator* (async delegation of well-specified tasks to background agents that open PRs).
This repo's harness ([AGENTS.md](../AGENTS.md), skills, `agent-task` issue template) supports both.

---

## 3. Deployment & AgentOps (GCP-first)

### 3.1 Runtime choice

| Need | **Agent Runtime** (priority) | Cloud Run | GKE |
|---|:--:|:--:|:--:|
| Managed sessions + memory + trace | ✅ built-in | DIY | DIY |
| Source-based deploy (no Dockerfile) | ✅ | container | container |
| Scale-to-zero / low ops | ✅ | ✅ | ❌ |
| Event-driven (Pub/Sub, Eventarc, schedules) | ❌ | ✅ | ✅ |
| Custom OS deps / GPU sidecars | ❌ | limited | ✅ |
| Best for Resonate Agentic | **✅** | portable fallback | only if self-hosting GPU work |

**Recommendation:** Agent Runtime for the agent. It is **source-based** — package an `AdkApp` and
deploy with `agents-cli deploy` / `uv run -m app.app_utils.deploy` (no Docker, no `gcloud`).
Cloud Run is the portable escape hatch and the home for any event-driven/ambient variant.

### 3.2 Repo topology (security boundary)

Split, per [ADR-0005](adr/ADR-0005-deployment-iac-repo-separation.md):

- **App repo (public, agent-edited)** — agent source, harness, evals, app CI, and the *source*
  deploy artifacts (`AdkApp`, `deploy.py`). **No cloud credentials.**
- **Control-plane repo (private)** — Terraform (reasoning-engine + IAM + Secret Manager + logs),
  WIF, and the CD pipeline. It **checks out the app at a pinned `release_sha`** and runs the
  source-based deploy. See **ADR-0006** ([tracking: #21](https://github.com/akoita/resonate-agentic/issues/21))
  for the reconciliation with `agents-cli` (which is single-repo-opinionated).

### 3.3 The delivery pipeline (eval-gated)

```
app CI green ─► build/package + emit deploy intent (release_sha)
                         │  repository_dispatch
control-plane CD ─► gate (AUTO_DEPLOY_ENABLED?) ─► checkout app@sha ─► EVAL GATE
                         │ pass                                          │ fail → stop
                         ▼ WIF (cicd_runner_sa, no static keys)
                 deploy → staging ─► [manual approval] ─► prod ─► publish (Gemini Enterprise) ─► observe
```

- **Identity:** `app_sa` (runtime) + `cicd_runner_sa` (CD); **Workload Identity Federation only** —
  no static keys. Secrets in **Secret Manager** (granted to the Agent Runtime managed SA).
- **Promotion:** staging auto (when enabled), **prod manual** (GitHub Environment protection).
- **Rollback:** git-based — redeploy the last-good `release_sha` (Agent Runtime has no revision
  rollback; Cloud Run supports traffic shifting).

### 3.4 AgentOps observability (non-negotiable at scale)

Agent observability captures **not just what the agent did, but why** — the full reasoning/tool-call
trajectory. Wire all five: **traces** (Cloud Trace), **prompt/response logging** → **BigQuery**
analytics, **evals in CI** as a release gate, **cost/latency metering**, and **drift monitoring** on
production traffic feeding the quality flywheel. (Budget for instrumentation overhead; benchmark it.)

---

## 4. Portability architecture (the Anthropic / OpenAI future)

All three major stacks are production-ready in mid-2026 — **Google ADK** (managed infra, multi-lang,
A2A-native), **OpenAI AgentKit / Agents SDK** (sandboxed subagents, Responses API), **Anthropic
Claude Agent SDK** (MCP-native, in-process servers, lifecycle hooks). Don't bet the app on one.
Keep the **boundary** clean so the runtime is swappable:

| Concern | Keep portable (own it) | Per-vendor adapter (swap it) |
|---|---|---|
| Agent logic / orchestration | ADK app, workflows | — |
| Tools | **MCP** servers/clients | — |
| Inter-agent | **A2A** | — |
| Model | `AGENT_MODEL` + LiteLLM | provider creds/config |
| Instructions/skills | `AGENTS.md` + `.agents/skills/` | tool-native adapter (`CLAUDE.md`/`GEMINI.md`, `.gemini/commands`) |
| **Runtime/deploy** | (thin) | **the only big per-vendor piece** |
| Secrets/identity | provider-agnostic config | platform IAM/WIF |

**Per-vendor deploy mapping (forward-looking):**

| Vendor | Native runtime/deploy | Portability notes |
|---|---|---|
| **GCP (now)** | Agent Runtime (source-based, `agents-cli`) / Cloud Run | priority target |
| **Anthropic (later)** | Claude Agent SDK hosting (MCP-native; in-process servers) | strongest if MCP-heavy; ADK app reaches it via MCP + LiteLLM(Claude) |
| **OpenAI (later)** | AgentKit / Agents SDK (sandbox, subagents, Responses API) | ADK app reaches GPT via LiteLLM; or re-host the same tools/evals on Agents SDK |

**Rule of thumb:** anything above the runtime line should never import a provider-only SDK in `app/`
core logic (enforced here by the portability guardrail + [ADR-0003](adr/ADR-0003-runtime-and-model-portability.md)).
Switching vendors then means: new runtime adapter + creds + a re-run of the **same** eval suite to
prove parity. The evals are what make a vendor swap *safe*.

> **Standards posture:** lean on the converging two-layer model — **MCP for tools, A2A for agents**
> (both under the Linux Foundation), with NIST's AI Agent Standards Initiative formalizing the space.
> Betting on these protocols is the cheapest insurance against lock-in.

---

## 5. Governance & security

- **Repo split** (public app / private control plane) so cloud creds/IAM/state never touch the
  public, agent-edited surface. → ADR-0005.
- **WIF everywhere; zero static keys.** Least-privilege SAs per environment. Prod manual-only.
- **Guardrails as code** (`scripts/harness_guardrails.py` + CI): no secrets, no leaked hosts, no
  provider lock-in in `app/`, async-tool rule. Plus model-I/O safety (**Model Armor**) at runtime.
- **AI-code review discipline:** hallucinated deps, error handling, silent stubs, over-broad scope.
- **Supply chain:** pinned deps, SHA-pinned actions, secret scanning, Dependabot (grouped/monthly).

---

## 6. Where to start (maturity ladder)

1. **Foundation (done here):** `AGENTS.md` harness, skills, guardrails, CI gate, protected `main`,
   ADRs, public/private repo split.
2. **Make it real:** MCP toolset for the backend, x402 commerce, budget guardrail callback
   ([#7](https://github.com/akoita/resonate-agentic/issues/7)–[#10](https://github.com/akoita/resonate-agentic/issues/10)).
3. **Make it trustworthy:** eval harness + CI gate ([#11](https://github.com/akoita/resonate-agentic/issues/11)),
   then the source-based deploy entrypoint ([#22](https://github.com/akoita/resonate-agentic/issues/22)) and the
   control-plane CD ([iac #3](https://github.com/akoita/resonate-agentic-iac/issues/3)).
4. **Make it observable & discoverable:** Cloud Trace + BigQuery ([#12](https://github.com/akoita/resonate-agentic/issues/12) /
   [iac #4](https://github.com/akoita/resonate-agentic-iac/issues/4)); publish to Gemini Enterprise ([iac #5](https://github.com/akoita/resonate-agentic-iac/issues/5)).
5. **Harden & keep portable:** Secret Manager/WIF, idempotency, a LiteLLM (non-Gemini) proof, and
   re-running evals against a second vendor to validate portability.

---

## 7. How this project implements the blueprint

| Blueprint element | Status |
|---|---|
| Factory model / harness | ✅ `AGENTS.md`, `.agents/skills/`, guardrails, `docs/AGENTIC_SDLC.md` |
| Multi-tool dev harness | ✅ Claude · Codex · Gemini (one source) |
| CI gate (lint+test+guardrails) | ✅ green, protected `main`, PR-only |
| Portability stance | ✅ ADR-0003 (model/runtime), open MCP/A2A |
| Public/private repo split | ✅ ADR-0005 + `resonate-agentic-iac` |
| Agent-ops deploy model | 🧭 this doc + issues ([#21](https://github.com/akoita/resonate-agentic/issues/21) ADR-0006, [#22](https://github.com/akoita/resonate-agentic/issues/22), iac #1–#6) |
| Eval gate | 🧭 #11 |
| Observability / publish | 🧭 #12, iac #4/#5 |
| MCP commerce / x402 | 🧭 #7–#10 |

---

## References

- Google, _The New SDLC with Vibe Coding_ (Osmani, Saboo, Kartakis, 2026).
- [ADK](https://adk.dev/) · [Agent Runtime / Gemini Enterprise Agent Platform](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk) · `agents-cli`.
- [A2A Protocol](https://a2a-protocol.org/) (Linux Foundation) · [MCP](https://modelcontextprotocol.io/).
- [Anthropic Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) · [OpenAI AgentKit/Agents SDK](https://openai.github.io/openai-agents-python/).
- [ADK AgentOps](https://google.github.io/adk-docs/observability/agentops/) · NIST AI Agent Standards Initiative (2026).
