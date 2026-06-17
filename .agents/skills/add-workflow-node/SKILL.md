---
name: add-workflow-node
description: Add or modify a node/edge in an ADK 2.x Workflow graph under app/workflows. Use when changing discovery_purchase, artist_upload, or dj_session, or building a new graph — covers the real Event route/state contract, LlmAgent nodes, and routing.
---

# Add an ADK Workflow node

The real ADK 2.2 `Workflow` contract (verified against the installed package). Don't guess it.

## Node functions

- Signature is introspected: include `ctx` (Context) and/or `node_input` as needed.
- Async is fine (and required if the node calls an async tool — then `await` it).
- Return a plain value/dict (becomes the node output), or an `Event`, or `None`.

## Routing — the real mechanism

A node selects an outgoing edge by emitting a **route** via the `Event` convenience kwarg, which lands
in `event.actions.route`:

```python
from google.adk.events.event import Event
return Event(output={...}, route="approved")          # picks the "approved" edge
```

Edges with a routing map; `DEFAULT_ROUTE` ("__DEFAULT__") is the fallback:

```python
from google.adk.workflow import Workflow, DEFAULT_ROUTE
edges=[
    ("START", parse),
    (parse, decide),
    (decide, {"approved": do_it, DEFAULT_ROUTE: skip}),  # dict = routing map
]
```

Graph validation is strict (e.g. duplicate `(from,to)` edges are rejected at construction). Cycles
are allowed (the DJ loop routes `advance → select_pick`).

## State — read/write across nodes

```python
ctx.state.get("key")                                  # read
return Event(output={...}, state={"key": value})      # write (→ event.actions.state_delta)
```

## LlmAgent nodes

```python
from google.adk.agents import LlmAgent
node = LlmAgent(name="...", model=config.model_name,
                instruction="... uses {state_key} templated from state ...",
                output_schema=MyPydanticModel, output_key="result")  # result → ctx.state["result"]
```

## Rules

- Agent-side enforcement (budget, loops) lives in function nodes (see `dj_session.advance`) — not the backend.
- Keep DJ/curation on the **public** catalog (ADR-0002); don't add JWT calls.
- The three real workflows hit an `LlmAgent` early, so full end-to-end needs model creds; cover the
  deterministic logic offline (see `tests/test_dj_budget.py`, `tests/test_workflow_runtime.py`).

`make check` must pass.
