# Resonate Agentic — Tech Debt Register

_Assessed 2026-06-17, post-Phase-0 (commit `5af1708`). Scoring: `(Impact + Risk) × (6 − Effort)`, each 1–5._

Effort key (rough): **1** ≈ hours · **2** ≈ 1–2 days · **3** ≈ 3–5 days · **4** ≈ 1–2 weeks · **5** ≈ multi-week.

## Already paid down in Phase 0 (for context)
- ✅ **Event-loop anti-pattern** — `run_until_complete` in every tool (crashed inside ADK). Tools are now native `async`.
- ✅ **No reproducible deps / VCS hygiene** — added pinned `requirements.txt`, `.gitignore`, `git init`.
- ✅ **No runtime tests** — added `tests/test_workflow_runtime.py` (engine + tools proven offline).
- ✅ **Silent fake tools** — stub tools now self-identify with `"stub": True`.

---

## Open debt — prioritized

| # | Item | Category | Impact | Risk | Effort | **Score** | Est. |
|---|------|----------|:--:|:--:|:--:|:--:|:--:|
| 1 | **Backend API contract unverified** — tool URLs guessed, mixed `/api` prefixes, no auth verified against real Resonate backend | Architecture / Docs | 4 | 5 | 2 | **36** | 1–2d |
| 2 | **x402 payment path non-functional** — no proof is ever constructed/signed; purchases can't settle | Architecture | 5 | 5 | 3 | **30** | 3–5d |
| 3 | **No CI** — tests/lint run only by hand | Infrastructure | 3 | 3 | 1 | **30** | hrs |
| 4 | **No deployment artifacts** — no Dockerfile/Agent Engine config/IaC | Infrastructure | 4 | 3 | 2 | **28** | 1–2d |
| 5 | **No observability** — no tracing/structured logging/metrics | Infrastructure | 3 | 4 | 2 | **28** | 1–2d |
| 6 | **Secrets & model backend** — API key in `.env`; AI Studio key, not Vertex/Secret Manager | Infrastructure / Security | 2 | 4 | 2 | **24** | 1–2d |
| 7 | **Placeholder workflow nodes** — `validate_upload`/`parse_input` hardcode title/artist/budget instead of parsing real input | Code | 3 | 3 | 2 | **24** | 1–2d |
| 8 | **5 stub tools** — `marketplace_list`, `stem_price`, `stem_mint`, `shows_campaign`, room create/join return synthetic data | Code (functional) | 3 | 4 | 3 | **21** | 3–5d |
| 9 | **Ephemeral sessions** — `WorkflowAgent` spawns a fresh `InMemoryRunner`+session per call; state lost between turns, not shared with parent | Architecture | 4 | 3 | 3 | **21** | 3–5d |
| 10 | **Duplicated pricing constants** — `0.05/5/25` tiers + floor/ceiling repeated across `schemas.py`, artist tools, workflows | Code | 2 | 2 | 1 | **20** | hrs |
| 11 | **Thin test coverage / no eval** — no tool error-path tests, no LLM/agent eval sets, real workflows never run with a live model | Test | 3 | 3 | 3 | **18** | 3–5d |
| 12 | **Loose dependency pins in `pyproject`** — `google-genai` unpinned; 3.11-vs-3.13 matrix untested | Dependency | 1 | 2 | 1 | **15** | hrs |
| 13 | **Sub-agent sprawl/overlap** — root has 8 sub-agents; `discovery_purchase` workflow overlaps `catalog`+`commerce` specialists → routing cost & ambiguity | Architecture | 2 | 2 | 3 | **12** | 3–5d |
| 14 | **`stem_purchase` inlines httpx** instead of the shared `_http` helper (minor dup) | Code | 1 | 1 | 1 | **10** | hrs |

---

## Business justification (top items)

- **#1 Backend contract** — until tool routes match the real Resonate API, *every* real interaction
  fails or returns garbage. It's cheap to fix and unblocks all downstream work; do it first.
- **#2 x402** — purchasing is the platform's core value prop. Without proof generation, the product
  literally cannot transact. Recommend delegating to the connected **agentcash MCP** (handles
  x402 + SIWX) rather than hand-rolling wallet signing in-process.
- **#3 CI** — hours of work that protects every later change; highest leverage-per-effort item.
- **#4/#5/#6 deploy + observability + secrets** — the minimum to run safely on **Agent Engine**
  (see `docs/GCP_AGENTIC_STACK.md`). Agent Engine gives tracing and managed sessions largely for
  free, which also discounts the effort on #5 and #9.
- **#9 sessions** — multi-turn DJ/upload UX is broken today (state evaporates). Switching to Agent
  Engine managed Sessions fixes #9 as a side effect of #4.

---

## Phased remediation (alongside feature work)

### Phase 1 — Make it real (rides with backend integration)
- #1 Verify/fix backend routes + auth (do before touching anything else).
- #3 Add CI (GitHub Actions or Cloud Build): `ruff` + `pytest` on every push. *Quick win, do now.*
- #7 Make `validate_upload`/`parse_input` parse real input.
- #2 x402 end-to-end via agentcash MCP; prove one discovery→quote→pay→receipt run.
- #8 Implement the 5 stub tools against real backend/chain (or formally descope them).
- #10/#12/#14 mop-up (centralize pricing constants, pin `pyproject`, route `stem_purchase` through `_http`) — bundle into the PRs above.

### Phase 2 — Production on GCP (rides with deployment)
- #6 Vertex AI backend + Secret Manager + Workload Identity.
- #4 Containerize + deploy to Agent Engine (which also resolves **#9** via managed Sessions/Memory).
- #5 Cloud Trace + BigQuery prompt/response logging.
- #11 Build eval datasets per workflow; gate CI on them.

### Phase 3 — Harden / optimize
- #13 Revisit agent topology — consider collapsing the workflow wrappers into tool-driven specialist flows, or measuring router latency/cost and pruning.
- Idempotency on purchases, rate limiting, privacy review for cohort/community data.

---

## Servicing rule of thumb
Carry **one "quick win" debt item (effort 1) per feature PR** (#3, #10, #12, #14) and schedule the
effort-3+ items (#2, #8, #9, #11, #13) as their own tracked work. Re-score this register at the end
of each phase.
