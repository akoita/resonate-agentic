# GCP Agentic Stack — Upskilling Guide

A practical map of Google Cloud's **professional agentic platform**, written to (a) teach the
full stack and (b) decide where *this* project (Resonate Agentic, ADK 2.0) should run.

> TL;DR for this project: build on **ADK** (already done) → run on **Vertex AI Agent Engine**
> (managed runtime + sessions + memory) → expose via **Agent Engine API** and optionally
> **Gemini Enterprise / Agentspace** → secure with **Model Armor + IAM/Secret Manager** →
> observe with **Cloud Trace + BigQuery** → gate releases with **Vertex AI eval**.

---

## 1. The stack, layer by layer

Think of GCP's agentic offering as **8 layers**. You can adopt them incrementally.

| # | Layer | GCP product(s) | What it gives you | Where this project is |
|---|-------|----------------|-------------------|-----------------------|
| 1 | **Model** | Vertex AI — Gemini 2.5 (Flash/Pro), Model Garden (Llama, Claude, Mistral via Vertex), embeddings | The reasoning engine; Provisioned Throughput for guaranteed capacity | Uses `gemini-2.5-flash` via AI Studio key — **move to Vertex** |
| 2 | **Framework / SDK** | **ADK** (Agent Development Kit), LangGraph, LlamaIndex, CrewAI (all deployable) | Author agents, tools, workflows, callbacks | ✅ ADK 2.2 |
| 3 | **Runtime / hosting** | **Vertex AI Agent Engine** (managed), **Cloud Run** (serverless containers), **GKE** (full control) | Run the agent at scale, autoscaling, identity | Not deployed yet → **Agent Engine** |
| 4 | **Sessions & Memory** | Agent Engine **Sessions** + **Memory Bank** (managed); or Vertex/Firestore-backed services | Durable multi-turn state; long-term memory across sessions | Uses `InMemoryRunner` (ephemeral) → **managed sessions** |
| 5 | **Tools & interop** | **MCP** (Model Context Protocol), **A2A** (Agent-to-Agent protocol), **Application Integration**, **API Hub**, RAG Engine / Vertex AI Search | Connect agents to APIs, data, and *other agents* | Custom HTTP tools; consider MCP for backend + agentcash for x402 |
| 6 | **Governance & security** | **Model Armor** (prompt-injection / DLP filtering), IAM, **Secret Manager**, **Cloud KMS**, VPC-SC, Workload Identity | Guardrails, secrets, network isolation, least privilege | API key in `.env` → **Secret Manager + Vertex IAM** |
| 7 | **Observability & quality** | **Cloud Trace**, Cloud Logging, **BigQuery** export, **Vertex AI Evaluation** | Traces, prompt/response logs, eval scores, dashboards | None yet → **Trace + eval gate** |
| 8 | **Discovery & distribution** | **Gemini Enterprise / Agentspace**, **Agent Garden / Agent Gallery**, agents-cli `publish` | Publish agents for employees/users to discover & use | N/A yet (post-deploy) |

**Mental model:** ADK is *how you build*, Agent Engine is *where it runs and remembers*,
A2A/MCP is *how it talks to tools and other agents*, Model Armor + IAM is *how you keep it
safe*, Trace + eval is *how you know it works*, Gemini Enterprise is *how people find it*.

---

## 2. The runtime decision: Agent Engine vs Cloud Run vs GKE

This is the choice you flagged. All three can host an ADK agent — the question is how much of
the agent-specific plumbing you want managed for you.

### Vertex AI Agent Engine (managed agent runtime) — **recommended here**
A fully managed runtime *purpose-built for agents*. You hand it an ADK app; it runs it.

**You get for free:** autoscaling + scale-to-zero, **managed Sessions & Memory Bank**, built-in
tracing to Cloud Trace, identity/auth integration, a stable query API, framework-agnostic
hosting (ADK/LangGraph/etc.), and one-command deploy via `adk deploy agent_engine` / the
Vertex SDK / `agents-cli`.

**You give up:** fine-grained control of the container/runtime, custom sidecars, arbitrary
networking topologies, non-HTTP workloads.

**Pick it when:** you want the shortest path to a *stateful, observable, scalable* agent
without operating session/memory infra yourself. ← Resonate Agentic fits squarely here:
multi-turn DJ/upload flows need durable sessions, and you don't want to run a session DB.

### Cloud Run (serverless containers) — strong fallback
Run the agent as a normal container behind HTTP. ADK can scaffold this (`adk deploy cloud_run`).

**You get:** full control of the image, request-based autoscaling + scale-to-zero, cheap, easy
custom dependencies/binaries, concurrency tuning, any HTTP framework.

**You manage yourself:** sessions/memory (bring your own — Firestore, Cloud SQL, Memorystore),
agent tracing wiring, and the agent-specific glue Agent Engine gives you out of the box.

**Pick it when:** you need custom system deps or networking, want the cheapest predictable
serverless bill, already have a session store, or want to avoid Agent Engine lock-in.

### GKE (Kubernetes) — maximum control
**Pick it when:** you have heavy/complex workloads (e.g. co-locating GPU stem-separation like
Demucs with the agent), an existing k8s platform, strict networking/multi-tenancy, or need
sidecars and custom schedulers. Highest operational burden.

### Decision matrix

| Need | Agent Engine | Cloud Run | GKE |
|------|:---:|:---:|:---:|
| Managed sessions + long-term memory | ✅ built-in | ⚠️ DIY | ⚠️ DIY |
| Scale to zero / cheap idle | ✅ | ✅ | ❌ (nodes) |
| Built-in agent tracing | ✅ | ⚠️ wire it | ⚠️ wire it |
| Custom OS deps / GPU sidecars | ❌ | ⚠️ limited | ✅ |
| Lowest ops effort | ✅ | ◐ | ❌ |
| Portability / no lock-in | ◐ | ✅ | ✅ |
| Best fit for Resonate Agentic | **✅** | fallback | only if self-hosting Demucs |

**Recommendation:** **Agent Engine** for the agent itself. If/when you self-host the GPU
stem-separation pipeline, run *that* on GKE/Cloud Run with GPUs and keep the agent on Agent
Engine, calling it as a tool/service. Don't conflate the two workloads.

---

## 3. Concrete mapping for Resonate Agentic

| Current | Production target on GCP |
|---------|--------------------------|
| `GOOGLE_API_KEY` + AI Studio | `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + project/region; Gemini Flash for the router, **Pro** for the rights-evaluation & stem-selection `LlmAgent` nodes |
| `InMemoryRunner` in `WorkflowAgent` | Agent Engine **managed Sessions**; **Memory Bank** for cross-session taste memory (great fit for the DJ) |
| HTTP tools w/ no auth | Tools read `RESONATE_API_KEY` from **Secret Manager**; backend behind IAM/Identity-Aware Proxy |
| x402 payment proof absent | Delegate to the **agentcash MCP** (x402 + SIWX wallet proofs) as a tool, or a dedicated payments service with keys in **Cloud KMS** |
| No guardrails | **Model Armor** on inputs/outputs; budget/spend enforced as ADK `before_tool_callback` (code, not prompt) |
| No tracing/eval | **Cloud Trace** (auto on Agent Engine) + prompt/response logging to **BigQuery**; **Vertex AI eval** sets per workflow as a CI gate |
| Not discoverable | Optionally **publish to Gemini Enterprise / Agentspace** via `agents-cli publish` |

---

## 4. Suggested learning path (in order)

1. **ADK fundamentals** — agents, tools, callbacks, `Workflow` graphs, `Runner`/`App`,
   sessions vs state. (You already have a working app — read `app/` + `tests/` as your lab.)
2. **Vertex AI model access** — flip the project to Vertex (`GOOGLE_GENAI_USE_VERTEXAI`),
   understand regions, quotas, Provisioned Throughput.
3. **Agent Engine deploy** — `adk deploy agent_engine` (or Vertex SDK); learn the query API,
   managed Sessions, and Memory Bank. *This is the core upskill for your chosen target.*
4. **Sessions & Memory** — when to use session state vs Memory Bank; persistence semantics.
5. **Tools & interop** — MCP servers as tools; **A2A** for multi-agent / external-agent calls
   (relevant if Resonate agents call partner agents).
6. **Security** — Model Armor, Secret Manager, Workload Identity, VPC-SC, least-privilege IAM.
7. **Observability & eval** — Cloud Trace reading, BigQuery analytics, building eval datasets
   and reading LLM-as-judge scores; wire eval into CI/CD (Cloud Build).
8. **Distribution** — publishing to Gemini Enterprise / Agentspace; the Agent Garden samples.

### Hands-on resources in this very environment
The Claude Code session has ADK skills that are the fastest authoritative path — use them as
guided labs:

- `google-agents-cli-workflow` — the end-to-end ADK dev lifecycle (start here).
- `google-agents-cli-scaffold` — generate a deployment-ready project shell.
- `google-agents-cli-deploy` — Agent Engine / Cloud Run / GKE deploy mechanics, service
  accounts, secrets, rollback.
- `google-agents-cli-eval` — eval methodology + the Quality Flywheel.
- `google-agents-cli-observability` — Cloud Trace, prompt/response logging, BigQuery analytics.
- `google-agents-cli-publish` — publish to Gemini Enterprise.
- `google-agents-cli-adk-code` — ADK API patterns reference.

---

## 5. Glossary (acronyms you'll hit)

- **ADK** — Agent Development Kit (the Python framework these agents use).
- **Agent Engine** — Vertex AI's managed runtime for agents (a.k.a. Reasoning Engine / Agent
  Runtime in older docs).
- **A2A** — Agent-to-Agent protocol: open standard for agents to call other agents.
- **MCP** — Model Context Protocol: open standard for exposing tools/data to agents.
- **Memory Bank** — Agent Engine's managed long-term memory across sessions.
- **Model Armor** — managed safety filter (prompt injection, jailbreak, DLP) for model I/O.
- **Gemini Enterprise / Agentspace** — Google's enterprise surface to publish & discover agents.
- **Vertex AI eval** — managed evaluation (incl. LLM-as-judge) for agent quality gating.
