# Resonate Agentic — Status & Roadmap to Production (GCP)

_Assessment date: 2026-06-17 · ADK installed: `google-adk` 2.2.0 · Python 3.13 (poetry venv), project targets 3.11_

This is an **experimental agentic-first reimplementation** of [akoita/resonate](https://github.com/akoita/resonate)
using Google's Agent Development Kit (ADK) 2.0. This document is the first honest status
of where it stands and what it takes to reach a production deployment on GCP's professional
agentic platform (Agent Runtime / Cloud Run + ADK).

---

## 1. What exists today

A clean, well-structured **multi-agent skeleton**. Roughly ~1,200 lines, no dead weight.

```
app/
  agent.py            root orchestrator (LLM router) + 5 specialists + 3 workflow wrappers
  config.py           dataclass config from env (.env)
  schemas.py          ~30 Pydantic domain models (mirrors Resonate's Prisma model)
  agents/             catalog, dj, commerce, artist, community  (LlmAgent + instructions)
  tools/              17 tools across catalog/commerce/dj/artist/community
  workflows/          discovery_purchase, artist_upload, dj_session (graph Workflows)
  agents/workflow_agent.py  BaseAgent wrapper to expose a Workflow as a sub-agent
tests/test_imports.py  single import smoke test
pyproject.toml / poetry.lock   (no requirements.txt)
.env.example
```

**Verdict: a credible architectural prototype, not yet a running system.** The agent graph
imports and constructs successfully (`root_agent` with 8 sub-agents). The design choices are
sound — clear specialist separation, typed schemas, graph workflows for deterministic flows.
But **no backend-touching path actually executes**, there are no deployment artifacts, and the
only test is an import check that doesn't even pass in the default interpreter.

---

## 2. Verified findings (tested, not guessed)

### ✅ BLOCKER 1 — Every network tool crashed at runtime — FIXED (Phase 0)
All 17 tools wrapped async HTTP in `asyncio.get_event_loop().run_until_complete(...)`. ADK
dispatches tools from **inside a running event loop**, so this raised at runtime. Confirmed
before the fix:

```
catalog_search("techno")  ->  {'status': 'error', 'error': 'This event loop is already running'}
```

**Fix shipped:** all I/O tools are now native `async def` over a shared async HTTP helper
(`app/tools/_http.py`); workflow nodes that call them now `await`. Proven with a test that runs
a tool *inside* a live event loop and a workflow end-to-end through the ADK `Runner`
(`tests/test_workflow_runtime.py`, 5 passing).

### ✅ BLOCKER 2 (RETRACTED — was a false alarm)
My first pass claimed the workflow routing/state contract was invalid because
`Event(...).route` was `NOATTR`. **That was wrong** — I checked the wrong attribute. ADK 2.2
accepts `route=` and `state=` as **Event convenience kwargs** that are routed to
`event.actions.route` and `event.actions.state_delta`. Verified:

```
e = Event(output={...}, route="approved", state={"k":"v"})
e.actions.route == "approved";  e.actions.state_delta == {"k":"v"}
```

So the workflows' conditional routing (incl. `__DEFAULT__` == `DEFAULT_ROUTE`) and state
hand-off were **already written against the real API** and execute correctly once the tools
they call are async. No rewrite was needed. (Graph validation is real and strict — e.g. it
rejects duplicate edges at construction.)

### 🟠 BLOCKER 3 — x402 payment flow is non-functional
`stem_purchase` forwards an `X-PAYMENT` header **if a proof is passed in**, but nothing in the
codebase ever constructs or signs one. There is no wallet, no USDC handling, no x402 client.
A purchase can therefore never complete — it can only ever return the `402` challenge.
(Note: the environment has an **`agentcash` MCP server** that natively handles x402 + SIWX wallet
proofs — a strong candidate to delegate payments to instead of hand-rolling.)

### 🟠 Several tools are pure stubs (return fabricated success)
`marketplace_list`, `stem_price`, `stem_mint`, `shows_campaign`, and the create/join/leave
branches of `room_manage` return hard-coded `"status": "minted/listed/priced"` without any
backend or chain call. They look like they work but do nothing.

### 🟡 Backend API contract is unverified / inconsistent
Tool URLs use mixed, guessed prefixes against the Resonate backend: `/api/storefront/stems`,
`/sessions/agent/next`, `/agents/config/session`, `/recommendations/{id}`,
`/analytics/artist/{id}/v1`, `/api/wallet/budget/{id}`, `/community/...`. These must be
validated against the actual akoita/resonate routes; several almost certainly don't match.

### 🟡 No auth anywhere
HTTP clients send no API key, bearer token, or wallet signature. The Resonate backend and any
SIWX/identity-gated endpoints will reject these calls.

### 🟡 WorkflowAgent spins up a throwaway runtime per call
`workflow_agent.py` creates a **new `InMemoryRunner` + new session on every invocation**. State
is never shared with the parent session and is lost between turns. Fine for a demo, wrong for prod.

### 🟡 Test/quality posture is minimal
- Only `tests/test_imports.py`, and it **fails in the system Python** (`google.adk` only in the
  poetry venv) — there's no documented "how to run" that makes the env unambiguous.
- No unit tests, no tool tests, no ADK eval sets, no CI.

---

## 3. Gaps toward production on GCP

There are **zero** deployment/ops artifacts. Confirmed missing:

```
MISSING: Dockerfile  requirements.txt  README.md  .gitignore
MISSING: Makefile  cloudbuild.yaml  .github/  deploy/  agent.yaml
```

Also: not a git repository. No observability, no eval harness, no secret management, no IaC.

**Model/runtime targeting is AI-Studio-style, not GCP-professional:** config reads
`GOOGLE_API_KEY` and uses `gemini-2.5-flash` directly. A professional GCP deployment should run
on **Vertex AI** (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, project + region), with credentials via
Workload Identity / Secret Manager rather than a raw API key in `.env`.

---

## 4. Target architecture (GCP professional agentic platform)

| Concern              | Recommendation |
|----------------------|----------------|
| **Agent runtime**    | **Agent Runtime** (formerly Vertex AI Agent Engine; managed ADK runtime, sessions, scaling) — primary target. Cloud Run as the portable/cheaper fallback. |
| **Model access**     | Gemini on the Agent Platform (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`); pin model + region; keep Flash for routing, consider Pro for the rights/selection LLM nodes. |
| **Sessions/Memory**  | Managed **Agent Platform Sessions** (`VertexAiSessionService`) instead of `InMemoryRunner`; durable session + memory for multi-turn DJ/upload flows. |
| **Secrets**          | Secret Manager + Workload Identity; remove API keys from `.env`. |
| **Payments (x402)**  | Either integrate the `agentcash` MCP (handles x402+SIWX wallet proofs) or a dedicated payment microservice; never sign in the agent process without a managed key (Cloud KMS). |
| **Observability**    | Cloud Trace + structured logging; ADK's built-in tracing; prompt/response logging to BigQuery for analytics & eval. |
| **CI/CD**            | Cloud Build (or GitHub Actions) → containerize → deploy to Agent Runtime/Cloud Run; gated on tests + eval pass. |
| **Eval**             | ADK eval datasets per workflow (discovery→purchase, upload, DJ session) as a release gate. |

The installed ADK + the `google-agents-cli-*` skills (scaffold / deploy / eval / observability /
publish) map directly onto this. The fastest correct path is to **scaffold a deployment shell
with `agents-cli` and port these agents into it**, rather than hand-build Docker/CI from scratch.

---

## 5. Prioritized roadmap

### Phase 0 — Make it run ✅ DONE
1. ✅ All I/O tools converted to native `async def` over `app/tools/_http.py`; `run_until_complete` removed; workflow nodes `await` them. **[fixed BLOCKER 1]**
2. ✅ Verified the ADK 2.2 routing/state contract — workflows were already correct (BLOCKER 2 retracted).
3. ✅ Added pinned `requirements.txt`, `.gitignore`, `README.md`, `docs/GCP_AGENTIC_STACK.md`, pytest config; `git init`.
4. ✅ `tests/test_workflow_runtime.py` (5 tests) proves async tools + workflow routing/state run against a mocked backend; all agents/workflows construct.

**Phase 0 leftovers (small):** stub tools are now clearly flagged with `"stub": True` but still need real backends (moved to Phase 1); a per-workflow eval/run with live LLM credentials is deferred to Phase 1/2.

### Phase 1 — Make it real (1–2 weeks)
5. Validate every backend route against akoita/resonate; fix paths; add auth headers.
6. Implement the stub tools (`stem_price`, `stem_mint`, `marketplace_list`, `shows_campaign`, room create/join) against real backend/chain endpoints — or explicitly mark them mocked.
7. Implement x402 end-to-end (recommend: delegate to `agentcash` MCP); prove one full discovery→quote→pay→receipt run.
8. Add budget/spend guardrails as ADK callbacks (before-tool checks), not just instructions, so "never purchase without confirmation" is enforced in code.

### Phase 2 — Make it production on GCP (2–4 weeks)
9. Switch to the Agent Platform model backend + managed Sessions/Memory service; remove `InMemoryRunner` from `WorkflowAgent`.
10. Containerize and deploy to **Agent Runtime** (use `google-agents-cli-deploy`); secrets via Secret Manager + Workload Identity.
11. Wire Cloud Trace + BigQuery logging (`google-agents-cli-observability`).
12. Build ADK eval sets and gate CI/CD on them (`google-agents-cli-eval`); Cloud Build pipeline.
13. Load/latency test the LLM router (8 sub-agents → routing cost); add caching where possible.

### Phase 3 — Harden
14. AuthZ per user/wallet, rate limiting, idempotency on purchases, PII/privacy review for cohort/community features, structured error taxonomy, runbooks.

---

## 6. One-line summary

**A clean, well-designed ADK multi-agent skeleton that imports but does not yet run:**
two runtime blockers (event-loop misuse in every tool; invalid workflow routing/state contract),
a non-functional payment path, several stub tools, and zero GCP deployment scaffolding. The
structure is worth keeping; the next concrete step is **Phase 0** — fix the async tools and the
workflow API contract so a single happy-path flow executes locally before touching GCP.
