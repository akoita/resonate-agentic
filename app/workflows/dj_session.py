"""AI DJ Session workflow (ADK 2.0) — compute-bound, public-contract only.

Per ADR-0002 the DJ is treated as a *compute-bound* feature: its intelligence is
taste-aware curation, which the LLM does natively over the backend's **public**
catalog. So this workflow uses only the auth-free agent contract:

    START → init → derive_taste(LLM) → search_public(catalog.search)
          → select_pick(LLM) → advance(budget+route) ⟲ → session_summary

No JWT-gated endpoints (no /sessions, /recommendations, /wallet). Taste is
inferred by the LLM; budget is enforced agent-side in workflow state.
"""

from __future__ import annotations

import uuid
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.workflow import Workflow
from google.genai import types
from pydantic import BaseModel, Field

from app.config import config
from app.tools.catalog import catalog_search


# ─── Schemas ─────────────────────────────────────────────────────────


class TasteSeed(BaseModel):
    """Taste profile the LLM infers from the listener's request (no backend call)."""

    query: str = Field(description="A concise catalog search query capturing the vibe")
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    energy: str | None = None


class DJPick(BaseModel):
    """A single curated pick chosen by the LLM from public catalog candidates."""

    stem_id: str = ""
    track_title: str = ""
    artist: str = ""
    stem_type: str | None = None
    price_usd: float = 0.0
    explanation: str = ""
    should_continue: bool = True


# ─── Helpers ─────────────────────────────────────────────────────────


def _extract_text(node_input: Any) -> str:
    if isinstance(node_input, types.Content):
        return node_input.parts[0].text if node_input.parts else ""
    if isinstance(node_input, str):
        return node_input
    return ""


def _compact_candidates(search_result: dict) -> list[dict]:
    """Reduce a catalog_search payload to compact, LLM-friendly candidate rows."""
    results = search_result.get("results", {})
    items = results.get("items", []) if isinstance(results, dict) else (
        results if isinstance(results, list) else []
    )
    compact: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        price = it.get("price", {})
        price_usd = price.get("usd") if isinstance(price, dict) else None
        compact.append(
            {
                "stem_id": it.get("id"),
                "title": it.get("title"),
                "artist": it.get("artist"),
                "stem_type": it.get("stemType"),
                "price_usd": price_usd if price_usd is not None else 0.0,
            }
        )
    return compact


# ─── Nodes ───────────────────────────────────────────────────────────


def init_session(ctx: Context, node_input: Any) -> Event:
    """Initialize a purely agent-side DJ session (no backend session)."""
    request = _extract_text(node_input)
    session_id = f"dj_{uuid.uuid4().hex[:12]}"
    return Event(
        output={"session_id": session_id, "request": request},
        state={
            "session_id": session_id,
            "dj_request": request,
            "picks_count": 0,
            "max_picks": ctx.state.get("max_picks", 5),
            "budget_usd": ctx.state.get("budget_usd", 10.0),
            "total_spend": 0.0,
            "played_stem_ids": [],
            "picks": [],
        },
    )


derive_taste = LlmAgent(
    name="derive_taste",
    model=config.model_name,
    instruction="""Infer the listener's musical taste from their request: {dj_request}

Produce a concise catalog search `query` plus any `genres`, `moods`, and `energy`
you can reasonably infer. If the request is vague, choose a sensible, broad vibe.
Do not invent specific track or artist names — describe the vibe for search.""",
    output_schema=TasteSeed,
    output_key="taste",
)


async def search_public(ctx: Context, node_input: Any) -> Event:
    """Search the PUBLIC catalog using the LLM-inferred taste seed (no auth)."""
    taste = ctx.state.get("taste", {}) or {}
    genres = taste.get("genres") or []
    moods = taste.get("moods") or []
    result = await catalog_search(
        query=taste.get("query") or ctx.state.get("dj_request", ""),
        limit=20,
        genre=genres[0] if genres else None,
        mood=moods[0] if moods else None,
    )
    return Event(
        output={"count": len(_compact_candidates(result))},
        state={"candidates": _compact_candidates(result)},
    )


select_pick = LlmAgent(
    name="select_pick",
    model=config.model_name,
    instruction="""You are an AI DJ curating the next track for the listener.

Listener request: {dj_request}
Inferred taste: {taste}
Candidates (public catalog): {candidates}
Already played (stem_ids — do NOT repeat): {played_stem_ids}

Pick the single best *unplayed* candidate that fits the taste. Fill in its
stem_id, track_title, artist, stem_type, and price_usd from the candidate row.
Give a one-sentence `explanation` of why it fits. Set should_continue=false only
if there are no good unplayed candidates left.""",
    output_schema=DJPick,
    output_key="current_pick",
)


def advance(ctx: Context, node_input: Any) -> Event:
    """Agent-side budget + loop control (replaces the JWT budget/session calls)."""
    pick = ctx.state.get("current_pick", {}) or {}
    picks_count = ctx.state.get("picks_count", 0)
    max_picks = ctx.state.get("max_picks", 5)
    budget = ctx.state.get("budget_usd", 10.0)
    spent = ctx.state.get("total_spend", 0.0)
    played = list(ctx.state.get("played_stem_ids", []))
    picks = list(ctx.state.get("picks", []))

    price = float(pick.get("price_usd", 0.0) or 0.0)
    stem_id = pick.get("stem_id") or ""

    # Stop conditions: LLM gave up, no stem, budget would be exceeded, or quota hit.
    if not pick.get("should_continue", True) or not stem_id or (spent + price) > budget:
        return Event(output={"recorded": False, "reason": "stop"}, route="exit")

    played.append(stem_id)
    picks.append(pick)
    picks_count += 1
    spent += price

    route = "continue" if picks_count < max_picks else "exit"
    return Event(
        output={"recorded": True, "pick": pick, "picks_count": picks_count},
        route=route,
        state={
            "played_stem_ids": played,
            "picks": picks,
            "picks_count": picks_count,
            "total_spend": spent,
        },
    )


def session_summary(ctx: Context, node_input: Any) -> dict:
    """Generate the local session summary (no backend stop call)."""
    return {
        "status": "completed",
        "session_id": ctx.state.get("session_id", ""),
        "picks_count": ctx.state.get("picks_count", 0),
        "total_spend_usd": ctx.state.get("total_spend", 0.0),
        "picks": ctx.state.get("picks", []),
        "message": "DJ session completed (curated from the public catalog).",
    }


# ─── Workflow Graph ──────────────────────────────────────────────────

dj_session_workflow = Workflow(
    name="dj_session",
    description="AI DJ session: LLM taste inference + curation over the public catalog, agent-side budget.",
    edges=[
        ("START", init_session),
        (init_session, derive_taste),
        (derive_taste, search_public),
        (search_public, select_pick),
        (select_pick, advance),
        (advance, {
            "continue": select_pick,
            "exit": session_summary,
        }),
    ],
)
