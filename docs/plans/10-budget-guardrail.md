# Issue #10 (BL-04) — budget guardrail (`before_tool_callback`) · implementation plan

**Issue:** https://github.com/akoita/resonate-agentic/issues/10 · **ADR:** ADR-0001 (strategy: enforce in code, not prompt) · **Status:** done

## Goal
Enforce the spending budget **in code** on the purchase path, so an over-budget purchase is *denied
deterministically* — not left to the LLM following an instruction. Prerequisite for any real x402
payment (#9).

## Approach
ADK `before_tool_callback` on `commerce_agent`. Verified contract (from installed source):
- called `callback(tool=, args=, tool_context=)`; **return a truthy dict → the tool is skipped** and
  that dict is the result; return `None` → the tool runs.
- `tool_context.state` is the session state; `tool.name` identifies the tool.

`app/guardrails/budget.py`:
- `PURCHASE_TOOLS = {"stem.download"}` (the paid MCP tool; extensible).
- `budget_before_tool(tool, args, tool_context)`:
  - non-purchase tool → `None` (allow).
  - `budget = state.budget_usd or config.default_budget_usd`; `spent = state.spent_usd or 0`.
  - `price = state.pending_purchase_usd` if set, **else assume worst-case = `config.max_purchase_usd`**
    (conservative: only allow when the budget can absorb a full-cap purchase).
  - deny (return dict) if: `remaining <= 0` (exhausted) · `price > config.max_purchase_usd`
    (per-purchase cap) · `price > remaining` (would exceed). Else `None`.
- `budget_after_tool(tool, args, tool_context, tool_response)`: on a successful purchase, add the
  (known or assumed) price to `state.spent_usd`.
- Wire `commerce_agent(before_tool_callback=budget_before_tool, after_tool_callback=budget_after_tool)`.
- Config: add `max_purchase_usd` (default 25.0 = commercial tier) + `.env.example`.

Pure module (no I/O, no GCP imports) — portable + offline-testable.

## Scope
**In:** the budget callback + wiring on commerce_agent + config + tests.
**Out:** the actual x402 payment (#9, blocked on a testnet wallet); session-state population of
`pending_purchase_usd` by the LLM flow (the guardrail is conservative without it).

## Acceptance / evals
- [x] `make check` green.
- [x] Deny when budget exhausted (`spent >= budget`).
- [x] Deny when intended price > per-purchase cap.
- [x] Deny when intended price > remaining.
- [x] Allow (`None`) for a within-budget purchase and for non-purchase tools.
- [x] `commerce_agent` carries the callbacks; `root_agent` still constructs.
- [x] `after_tool` increments `spent_usd`.

## Risks & rollbacks
- Without `pending_purchase_usd` in state the guard is *conservative* (assumes full cap) — may block a
  cheap purchase when the remaining budget < cap. Acceptable (fails safe); revisit when the quote→buy
  flow records the price. Rollback: drop the callbacks from `commerce_agent`.

## Validation
- Offline unit tests (this PR).
