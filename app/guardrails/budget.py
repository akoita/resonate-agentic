"""Budget guardrail — enforce spend limits on purchase tools in code, not prompts.

Wired as ADK ``before_tool_callback`` / ``after_tool_callback`` on the commerce agent. The hard rule
"never purchase beyond budget" is enforced deterministically here, so it cannot be talked around by
the model. Prerequisite for any real x402 payment (#9).

ADK contract (verified against the installed package):
- ``before_tool_callback(tool, args, tool_context)`` — return a **truthy dict to skip** the tool (that
  dict becomes the result); return ``None`` to let it run.
- ``after_tool_callback(tool, args, tool_context, tool_response)`` — observe/adjust the result.
"""

from __future__ import annotations

from typing import Any

from app.config import config

# Paid tools subject to the budget. The MCP paid download is the purchase action.
PURCHASE_TOOLS = {"stem.download"}


def _is_purchase(tool_name: str) -> bool:
    return tool_name in PURCHASE_TOOLS or "purchase" in tool_name or "download" in tool_name


def _intended_price(state: Any) -> float:
    """Best-effort intended spend for the next purchase.

    Uses ``pending_purchase_usd`` from session state when the quote→buy flow recorded it; otherwise
    assumes the worst case (the per-purchase cap) so we only allow a purchase the budget can absorb.
    """
    pending = state.get("pending_purchase_usd")
    try:
        return float(pending) if pending is not None else float(config.max_purchase_usd)
    except (TypeError, ValueError):
        return float(config.max_purchase_usd)


def _deny(reason: str, **detail: Any) -> dict:
    return {"status": "budget_blocked", "reason": reason, **detail}


def budget_before_tool(tool, args, tool_context):  # noqa: ANN001 — ADK callback signature
    """Block over-budget / over-cap purchases before the tool runs."""
    if not _is_purchase(getattr(tool, "name", "")):
        return None

    state = tool_context.state
    budget = float(state.get("budget_usd", config.default_budget_usd))
    spent = float(state.get("spent_usd", 0.0))
    remaining = budget - spent
    price = _intended_price(state)
    cap = float(config.max_purchase_usd)

    base = {"budget_usd": budget, "spent_usd": spent, "remaining_usd": max(0.0, remaining)}
    if remaining <= 0:
        return _deny("budget_exhausted", **base)
    if price > cap:
        return _deny("exceeds_per_purchase_cap", price_usd=price, cap_usd=cap, **base)
    if price > remaining:
        return _deny("would_exceed_budget", price_usd=price, **base)
    return None  # within budget — let the purchase proceed


def budget_after_tool(tool, args, tool_context, tool_response):  # noqa: ANN001 — ADK signature
    """Record spend after a successful purchase so the budget tracks across the session."""
    if not _is_purchase(getattr(tool, "name", "")):
        return None
    # Don't count a purchase the guardrail itself blocked.
    if isinstance(tool_response, dict) and tool_response.get("status") == "budget_blocked":
        return None
    state = tool_context.state
    state["spent_usd"] = float(state.get("spent_usd", 0.0)) + _intended_price(state)
    return None
