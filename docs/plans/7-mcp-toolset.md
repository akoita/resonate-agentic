# Issue #7 (BL-01) — MCP toolset for catalog/quote/purchase · implementation plan

**Issue:** https://github.com/akoita/resonate-agentic/issues/7 · **ADR:** ADR-0001, ADR-0002 · **Status:** done

## Goal
Have the agents use the backend's **purpose-built MCP server** (`$RESONATE_API_BASE/mcp`) for the
agent-commerce core — `catalog.search`, `stem.quote`, `stem.download` — instead of hand-written,
guessed HTTP tools. This is the first real feature exercised end-to-end through the harness.

## Scope
**In:**
- `app/tools/mcp.py` — a factory that builds an ADK `McpToolset` over streamable-HTTP to `config.mcp_url`.
- Wire it into `catalog_agent` (discovery: `catalog.search`, `stem.quote`) and `commerce_agent`
  (commerce: `stem.quote`, `stem.download`).
- Add `mcp` as a dependency (ADK's optional MCP support).

**Out (separate issues):**
- x402 proof generation for `stem.download` (#9 / BL-03) — without a proof the tool returns the 402
  challenge, which is the correct behavior here.
- Migrating the **workflows** off the hand-written async tools — the workflows keep using
  `app/tools/{catalog,commerce}.py` for now; those tools stay. `catalog_browse` + `stem_info` (no MCP
  equivalent) remain hand-written on `catalog_agent`.

## Approach
- `McpToolset(connection_params=StreamableHTTPConnectionParams(url=config.mcp_url, headers=...),
  tool_filter=[...], tool_name_prefix="resonate")`. Construction is **lazy** (no network at import) —
  verified — so root-agent import and CI stay offline.
- Auth: pass `Authorization: Bearer` from `config.api_key` when set (public MCP tools need none).
- `catalog_agent.tools = [mcp(catalog.search, stem.quote), catalog_browse, stem_info]`.
- `commerce_agent.tools = [mcp(stem.quote, stem.download), budget_check, marketplace_list, stem_info]`.
- Keep the hand-written tool modules (workflows + typed paths depend on them).

## Acceptance / evals
- [x] `make check` green (lint + 14 tests + guardrails) with `mcp` added to deps.
- [x] `app/tools/mcp.py` factory returns an `McpToolset` pointed at `config.mcp_url` with the right
      `tool_filter`; constructed offline (no network) in a unit test.
- [x] `catalog_agent` and `commerce_agent` carry the MCP toolset; `root_agent` still constructs (8 sub-agents).
- [x] Existing workflow/runtime tests stay green (hand-written tools untouched).
- [x] (manual) Live MCP handshake against staging lists exactly `catalog.search`, `stem.quote`,
      `stem.download` — names match the filter. (Full paid `stem.download` returns the 402 challenge
      until x402 proof generation lands — #9.)

## Risks & rollbacks
- MCP tool names may be exposed sanitized (e.g. `catalog_search` vs `catalog.search`). Mitigation:
  the filter is data; if names differ, adjust the filter (the live check confirms). Risk is low and
  isolated to `app/tools/mcp.py`.
- Live MCP unavailability only affects runtime, not import/CI (lazy). Rollback: revert the agents'
  `tools=` to the hand-written set (kept in-tree).

## Validation
- Offline unit tests (this PR, 4 new).
- Live check (2026-06-17) against `api-staging`: `get_tools()` over streamable-HTTP returned
  `['catalog.search', 'stem.quote', 'stem.download']` — connection + filter confirmed end-to-end.
