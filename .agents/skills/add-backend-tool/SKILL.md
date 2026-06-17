---
name: add-backend-tool
description: Add or modify a tool in app/tools that calls the Resonate backend. Use when creating a new agent tool, wiring an endpoint, or touching app/tools — covers the async pattern, public-vs-JWT scope, and stub flagging.
---

# Add a backend tool

Procedural knowledge for `app/tools/`. Follow exactly — these encode AGENTS.md hard rules.

## 1. Decide scope first (ADR-0002)

- **Public contract** (no auth): storefront/catalog, `/api/stems/{id}/x402*`, stem-pricing, MCP
  (`catalog.search`, `stem.quote`, `stem.download`). ✅ build freely.
- **JWT-gated** (sessions, recommendations, wallet, analytics, ingestion, community): **blocked** —
  these need an agent auth path (BL-13 / ADR-0004). Do not hardcode tokens. If you must stub, flag it.

## 2. Write it as an `async def` over the shared client

```python
from app.tools._http import api_get, api_post  # NEVER asyncio.run / run_until_complete

async def my_tool(stem_id: str, license_type: str = "personal") -> dict:
    """One-line summary the LLM reads. Document args + returns.

    Returns: dict with a "status" key.
    """
    try:
        data = await api_get(f"/api/stems/{stem_id}/x402/info",
                             params={"licenseType": license_type})
        return {"status": "ok", "stem_id": stem_id, "data": data}
    except Exception as e:  # tools never raise to the agent
        return {"status": "error", "error": str(e)}
```

- I/O **must** go through `app/tools/_http.py` (auth header handling lives there).
- Return a `dict` with `"status"`; never let exceptions propagate to the agent loop.
- A tool that doesn't really do the work returns `"stub": True` (no fake success).

## 3. Register + use it

- Export from `app/tools/__init__.py`.
- Add to the relevant agent's `tools=[...]` in `app/agents/`.
- If a workflow node calls it, the node must be `async def` and `await` it.

## 4. Test offline (mock the backend)

```python
import respx, httpx, pytest
from app.config import config
from app.tools.catalog import my_tool

@pytest.mark.asyncio
async def test_my_tool():
    with respx.mock(base_url=config.api_base) as m:
        m.get("/api/stems/s1/x402/info").mock(return_value=httpx.Response(200, json={"ok": True}))
        assert (await my_tool("s1"))["status"] == "ok"
```

## 5. Gate

`make check` (ruff + pytest + guardrails) must pass. Prefer the existing MCP tools over hand-rolling
HTTP where the backend already exposes the capability (BL-01).
