"""Runtime proof tests for Phase 0.

These verify the two things the original code got wrong/untested:
  1. Tools are native async and run inside ADK's event loop (no run_until_complete).
  2. The Workflow node/routing/state contract actually executes through the runner.

The three real workflows hit a Gemini ``LlmAgent`` node early, which needs live
credentials, so the end-to-end engine test uses a function-only workflow built
with the *same* API (Event(route=...), Event(state=...), ctx.state, dict routing
maps, async function nodes calling async tools).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.runners import InMemoryRunner
from google.adk.workflow import DEFAULT_ROUTE, Workflow
from google.genai import types

from app.config import config
from app.tools.catalog import catalog_search


# ─── 1. Async tools run inside a running event loop ──────────────────


@pytest.mark.asyncio
async def test_async_tool_runs_in_event_loop():
    with respx.mock(base_url=config.api_base) as mock:
        mock.get("/api/storefront/stems").mock(
            return_value=httpx.Response(200, json={"stems": [{"id": "stem_1"}]})
        )
        result = await catalog_search("techno")
    assert result["status"] == "ok"
    assert result["results"]["stems"][0]["id"] == "stem_1"


# ─── 2. Workflow engine: routing + state + async tool node ───────────


def parse(ctx: Context, node_input):
    text = ""
    if isinstance(node_input, types.Content):
        text = node_input.parts[0].text if node_input.parts else ""
    elif isinstance(node_input, str):
        text = node_input
    return Event(output={"query": text}, state={"search_query": text})


async def search(node_input: dict) -> dict:
    return await catalog_search(query=node_input.get("query", ""))


def route_on_results(ctx: Context, node_input: dict) -> Event:
    results = node_input.get("results", {})
    stems = results.get("stems", []) if isinstance(results, dict) else []
    if stems:
        return Event(output={"stems": stems}, route="found", state={"top": stems[0]})
    return Event(output={"stems": []}, route="empty")


def on_found(ctx: Context, node_input: dict) -> dict:
    # proves state written by an upstream node is readable here
    return {"status": "found", "top": ctx.state.get("top"), "query": ctx.state.get("search_query")}


def on_empty(ctx: Context, node_input: dict) -> dict:
    return {"status": "empty"}


def _build_workflow() -> Workflow:
    return Workflow(
        name="runtime_proof",
        edges=[
            ("START", parse),
            (parse, search),
            (search, route_on_results),
            (route_on_results, {"found": on_found, DEFAULT_ROUTE: on_empty}),
        ],
    )


async def _run(workflow: Workflow, message: str) -> list[Event]:
    app = App(name=workflow.name + "_app", root_agent=workflow)
    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(
        app_name=app.name, user_id="test_user"
    )
    events = []
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_workflow_routes_found_branch_and_reads_state():
    with respx.mock(base_url=config.api_base) as mock:
        mock.get("/api/storefront/stems").mock(
            return_value=httpx.Response(200, json={"stems": [{"id": "stem_42"}]})
        )
        events = await _run(_build_workflow(), "deep house")

    outputs = [e.output for e in events if e.output is not None]
    found = [o for o in outputs if isinstance(o, dict) and o.get("status") == "found"]
    assert found, f"expected a 'found' output, got: {outputs}"
    assert found[0]["top"] == {"id": "stem_42"}      # state written upstream
    assert found[0]["query"] == "deep house"          # state from parse node


@pytest.mark.asyncio
async def test_workflow_routes_empty_branch():
    with respx.mock(base_url=config.api_base) as mock:
        mock.get("/api/storefront/stems").mock(
            return_value=httpx.Response(200, json={"stems": []})
        )
        events = await _run(_build_workflow(), "no such genre")

    outputs = [e.output for e in events if e.output is not None]
    assert any(isinstance(o, dict) and o.get("status") == "empty" for o in outputs), outputs


# ─── 3. All real workflows + root agent construct ────────────────────


def test_real_workflows_and_root_agent_construct():
    from app.agent import root_agent
    from app.workflows import (
        artist_upload_workflow,
        discovery_purchase_workflow,
        dj_session_workflow,
    )

    assert root_agent.name == "resonate"
    assert len(root_agent.sub_agents) == 8
    assert discovery_purchase_workflow.name == "discovery_purchase"
    assert artist_upload_workflow.name == "artist_upload"
    assert dj_session_workflow.name == "dj_session"
