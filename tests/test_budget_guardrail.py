"""Offline tests for the budget guardrail (#10 / BL-04).

The guardrail enforces spend limits deterministically as an ADK before/after tool callback —
no LLM, no network. We drive it with stand-ins for `tool` (has `.name`) and `tool_context`
(has `.state`).
"""

from __future__ import annotations

from types import SimpleNamespace

from app.config import config
from app.guardrails.budget import budget_after_tool, budget_before_tool

DOWNLOAD = SimpleNamespace(name="stem.download")
QUOTE = SimpleNamespace(name="stem.quote")


def _ctx(**state):
    return SimpleNamespace(state=state)


def test_non_purchase_tool_is_allowed():
    assert budget_before_tool(QUOTE, {}, _ctx(spent_usd=999)) is None


def test_within_budget_allowed():
    # remaining 50 >= worst-case cap 25 → allow
    assert budget_before_tool(DOWNLOAD, {}, _ctx()) is None
    # explicit cheap price well within budget
    assert budget_before_tool(DOWNLOAD, {}, _ctx(pending_purchase_usd=0.05)) is None


def test_exhausted_budget_denied():
    ev = budget_before_tool(DOWNLOAD, {}, _ctx(budget_usd=50, spent_usd=50))
    assert ev and ev["status"] == "budget_blocked" and ev["reason"] == "budget_exhausted"


def test_over_per_purchase_cap_denied():
    ev = budget_before_tool(DOWNLOAD, {}, _ctx(pending_purchase_usd=config.max_purchase_usd + 1))
    assert ev["reason"] == "exceeds_per_purchase_cap"


def test_would_exceed_remaining_denied():
    ev = budget_before_tool(DOWNLOAD, {}, _ctx(budget_usd=10, spent_usd=5, pending_purchase_usd=8))
    assert ev["reason"] == "would_exceed_budget"
    assert ev["remaining_usd"] == 5


def test_conservative_block_when_price_unknown_and_remaining_below_cap():
    # remaining 1 < worst-case cap → fail safe (block) when the price isn't recorded
    ev = budget_before_tool(DOWNLOAD, {}, _ctx(budget_usd=10, spent_usd=9))
    assert ev["reason"] == "would_exceed_budget"


def test_after_tool_records_spend():
    ctx = _ctx(spent_usd=0.0, pending_purchase_usd=0.05)
    budget_after_tool(DOWNLOAD, {}, ctx, {"status": "purchased"})
    assert abs(ctx.state["spent_usd"] - 0.05) < 1e-9


def test_after_tool_ignores_blocked_purchase():
    ctx = _ctx(spent_usd=1.0, pending_purchase_usd=0.05)
    budget_after_tool(DOWNLOAD, {}, ctx, {"status": "budget_blocked"})
    assert ctx.state["spent_usd"] == 1.0


def test_commerce_agent_has_callbacks_and_root_constructs():
    from app.agent import root_agent
    from app.agents import commerce_agent

    assert commerce_agent.before_tool_callback is budget_before_tool
    assert commerce_agent.after_tool_callback is budget_after_tool
    assert root_agent.name == "resonate" and len(root_agent.sub_agents) == 8
