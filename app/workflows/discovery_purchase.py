"""Discovery → Purchase workflow using ADK 2.0 Workflow API.

This workflow orchestrates the full stem discovery and purchase flow:
START → search → select_best → quote → check_budget → purchase/suggest_alternatives
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.workflow import Workflow
from google.genai import types
from pydantic import BaseModel

from app.config import config
from app.tools.catalog import catalog_search, stem_quote
from app.tools.commerce import budget_check, stem_purchase


# ─── Pydantic I/O Schemas ───────────────────────────────────────────


class SearchInput(BaseModel):
    query: str
    genre: str | None = None
    mood: str | None = None
    license_type: str = "personal"
    max_budget_usd: float = 10.0


class SelectedStem(BaseModel):
    stem_id: str
    title: str
    artist: str
    price_usd: float
    license_type: str
    reason: str


class PurchaseDecision(BaseModel):
    action: str  # "purchase" or "skip"
    reason: str


# ─── Workflow Nodes ──────────────────────────────────────────────────


def parse_input(ctx: Context, node_input: Any) -> dict:
    """Parse the user's discovery request."""
    text = ""
    if isinstance(node_input, types.Content):
        text = node_input.parts[0].text if node_input.parts else ""
    elif isinstance(node_input, str):
        text = node_input
    else:
        text = str(node_input)

    return Event(
        output={"query": text, "license_type": "personal", "max_budget_usd": 10.0},
        state={"search_query": text},
    )


async def search_catalog(node_input: dict) -> dict:
    """Search the Resonate catalog."""
    return await catalog_search(
        query=node_input.get("query", ""),
        limit=10,
        genre=node_input.get("genre"),
        mood=node_input.get("mood"),
    )


stem_selector = LlmAgent(
    name="stem_selector",
    model=config.model_name,
    instruction="""You are analyzing search results from the Resonate music catalog.
Select the single best stem that matches the user's query: {search_query}

Pick the most relevant stem based on genre match, artist relevance,
and price within budget. Return your selection.""",
    output_schema=SelectedStem,
    output_key="selected_stem",
)


async def get_quote(ctx: Context, node_input: Any) -> Event:
    """Get a price quote for the selected stem."""
    selected = ctx.state.get("selected_stem", {})
    if not selected or not selected.get("stem_id"):
        return Event(output={"status": "no_selection"}, route="no_results")

    quote = await stem_quote(
        stem_id=selected["stem_id"],
        license_type=selected.get("license_type", "personal"),
    )
    return Event(output=quote, state={"quote": quote})


async def check_budget_node(ctx: Context, node_input: dict) -> Event:
    """Verify the buyer has sufficient budget."""
    user_id = ctx.state.get("user_id", "default")
    budget = await budget_check(user_id)

    quote = ctx.state.get("quote", {})
    price = 0.0
    if isinstance(quote, dict) and "quote" in quote:
        price = quote["quote"].get("priceUsdc", quote["quote"].get("price", 0.0))

    remaining = budget.get("remaining_usd", 0.0)

    if remaining >= price:
        return Event(output={"approved": True, "budget": budget}, route="approved")
    else:
        return Event(
            output={"approved": False, "budget": budget, "price": price},
            route="rejected",
        )


async def execute_purchase(ctx: Context, node_input: dict) -> dict:
    """Execute the x402 stem purchase."""
    selected = ctx.state.get("selected_stem", {})
    if not selected:
        return {"status": "error", "message": "No stem selected"}

    return await stem_purchase(
        stem_id=selected["stem_id"],
        license_type=selected.get("license_type", "personal"),
    )


def suggest_alternatives(ctx: Context, node_input: dict) -> dict:
    """Suggest budget-friendly alternatives."""
    budget = node_input.get("budget", {})
    return {
        "status": "budget_exceeded",
        "remaining_usd": budget.get("remaining_usd", 0.0),
        "suggestion": "Try a personal license tier ($0.05) or browse cheaper stems.",
    }


def format_no_results(node_input: Any) -> dict:
    """Handle the case where no stems were found."""
    return {
        "status": "no_results",
        "message": "No matching stems found. Try a different query or browse by genre.",
    }


# ─── Workflow Graph ──────────────────────────────────────────────────

discovery_purchase_workflow = Workflow(
    name="discovery_purchase",
    description="Full discovery-to-purchase flow: search → select → quote → budget check → purchase.",
    edges=[
        ("START", parse_input),
        (parse_input, search_catalog),
        (search_catalog, stem_selector),
        (stem_selector, get_quote),
        (get_quote, {
            "__DEFAULT__": check_budget_node,
            "no_results": format_no_results,
        }),
        (check_budget_node, {
            "approved": execute_purchase,
            "rejected": suggest_alternatives,
        }),
    ],
)
