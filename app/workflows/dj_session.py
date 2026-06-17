"""AI DJ Session workflow using ADK 2.0 Workflow API.

Orchestrates: START → init → taste_analyze → recommendation loop:
  → search → score → policy_check → present → continue/exit
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
from app.tools.commerce import budget_check
from app.tools.dj import recommend_next, session_manage, taste_analyze


# ─── Schemas ─────────────────────────────────────────────────────────


class DJPick(BaseModel):
    track_title: str
    artist: str
    stem_type: str | None = None
    price_usd: float = 0.0
    explanation: str = ""
    should_continue: bool = True


# ─── Nodes ───────────────────────────────────────────────────────────


async def init_session(ctx: Context, node_input: Any) -> Event:
    """Initialize the AI DJ session."""
    text = ""
    if isinstance(node_input, types.Content):
        text = node_input.parts[0].text if node_input.parts else ""
    elif isinstance(node_input, str):
        text = node_input

    user_id = ctx.state.get("user_id", "default_user")
    session = await session_manage(action="start", user_id=user_id)

    return Event(
        output={
            "session_id": session.get("session_id", "session_1"),
            "user_id": user_id,
            "request": text,
        },
        state={
            "session_id": session.get("session_id", "session_1"),
            "picks_count": 0,
            "max_picks": 5,
            "total_spend": 0.0,
        },
    )


async def analyze_taste(ctx: Context, node_input: dict) -> dict:
    """Analyze the listener's taste profile."""
    user_id = node_input.get("user_id", ctx.state.get("user_id", "default_user"))
    return await taste_analyze(user_id)


async def get_recommendation(ctx: Context, node_input: Any) -> dict:
    """Get the next AI DJ recommendation."""
    session_id = ctx.state.get("session_id", "")
    return await recommend_next(session_id=session_id)


async def check_policy(ctx: Context, node_input: dict) -> Event:
    """Check budget and policy constraints."""
    user_id = ctx.state.get("user_id", "default_user")
    budget = await budget_check(user_id)
    picks = ctx.state.get("picks_count", 0)
    max_picks = ctx.state.get("max_picks", 5)

    if picks >= max_picks:
        return Event(output={"recommendation": node_input, "budget": budget}, route="exit")

    if not budget.get("can_purchase", True):
        return Event(output={"recommendation": node_input, "budget": budget}, route="exit")

    return Event(
        output={"recommendation": node_input, "budget": budget},
        route="continue",
        state={"picks_count": picks + 1},
    )


pick_presenter = LlmAgent(
    name="pick_presenter",
    model=config.model_name,
    instruction="""You are presenting an AI DJ pick to the listener.
Format the recommendation as a compelling music suggestion with the track title,
artist, why it was picked, and the price. Be enthusiastic but concise.

Decide whether to continue the session or end it based on the remaining budget
and picks count.""",
    output_schema=DJPick,
    output_key="current_pick",
)


def continue_or_exit(ctx: Context, node_input: Any) -> Event:
    """Decide whether to continue the DJ session."""
    pick = ctx.state.get("current_pick", {})
    if pick.get("should_continue", True):
        return Event(output=pick, route="continue")
    return Event(output=pick, route="exit")


async def session_summary(ctx: Context, node_input: Any) -> dict:
    """Generate the session summary."""
    session_id = ctx.state.get("session_id", "")
    await session_manage(action="stop", user_id=ctx.state.get("user_id", "default"))
    return {
        "status": "completed",
        "session_id": session_id,
        "picks_count": ctx.state.get("picks_count", 0),
        "total_spend": ctx.state.get("total_spend", 0.0),
        "message": "DJ session completed. Thanks for listening!",
    }


# ─── Workflow Graph ──────────────────────────────────────────────────

dj_session_workflow = Workflow(
    name="dj_session",
    description="AI DJ session: taste analysis → recommendation loop with budget checks.",
    edges=[
        ("START", init_session),
        (init_session, analyze_taste),
        (analyze_taste, get_recommendation),
        (get_recommendation, check_policy),
        (check_policy, {
            "continue": pick_presenter,
            "exit": session_summary,
        }),
        (pick_presenter, continue_or_exit),
        (continue_or_exit, {
            "continue": get_recommendation,
            "exit": session_summary,
        }),
    ],
)
