---
name: eval-and-deploy
description: Evaluate and deploy the Resonate agent. Use when building evals, wiring the CI eval gate, or deploying to Agent Runtime / Cloud Run. Covers the quality flywheel, the eval-as-contract bar, and portable deploy targets.
---

# Evaluate & deploy

> Status: eval harness and deploy are planned (ROADMAP BL-05 / BL-08). This skill is the playbook
> for wiring them; keep it the single reference when you do.

## Evals (set the bar at the eval, not the demo)

Two kinds, both required for an agent shipping into a shared workflow:

- **Final-response eval** — is the output correct? (datasets + rubric + LLM-judge)
- **Trajectory eval** — did it take the right steps / call the right tools / respect guardrails?

Use ADK's eval support. An evalset per workflow (`discovery_purchase`, `dj_session`), each with an
explicit rubric scoring: task success, tool-use quality, trajectory compliance, hallucination,
response quality. Wire `make eval` and gate CI on it (BL-05).

The **quality flywheel**: `evaluate → diagnose (cluster root causes) → optimize (prompt/tool/skill)
→ verify (regression) → monitor`. Each cycle compounds. Write the eval *before* the behavior where practical.

## Deploy (portable — priority target, not lock-in; ADR-0003)

- **Priority:** Agent Runtime (Gemini Enterprise). Managed sessions/memory/tracing.
- **Portable alternatives, no code change:** Cloud Run, GKE, other clouds, or local (`adk run` / `adk web`).
- Select managed Sessions/Memory by **config** with an in-memory/Firestore fallback (BL-07) so non-GCP
  hosts keep working. Keep `app/` free of GCP-only imports (guardrail).
- Model is swappable via `AGENT_MODEL` (Gemini or any provider via LiteLLM).

## Pre-deploy gate

`make check` green · evals pass with rubric · no hard-rule violations · secrets via env/Secret Manager
(never committed). See `docs/GCP_AGENTIC_STACK.md` for the GCP deep-dive and the `google-agents-cli-*`
skills for the managed-platform mechanics.
