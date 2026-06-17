"""ADK MCP toolset for the Resonate backend's agent contract.

The backend ships a purpose-built MCP server (streamable-HTTP) at ``$RESONATE_API_BASE/mcp``
exposing the agent-commerce core: ``catalog.search`` (free), ``stem.quote`` (free), and
``stem.download`` (x402-paid). We consume it directly (ADR-0001) rather than hand-rolling HTTP.

Construction is lazy — no network at import — so building the toolset is safe in tests/CI; the
connection happens on first tool use at runtime.
"""

from __future__ import annotations

from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from app.config import config

# MCP tool names as published by the backend (.well-known/mcp.json).
CATALOG_SEARCH = "catalog.search"
STEM_QUOTE = "stem.quote"
STEM_DOWNLOAD = "stem.download"


def _headers() -> dict[str, str]:
    """Backend auth header when configured (public MCP tools need none)."""
    return {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}


def resonate_mcp_toolset(tool_filter: list[str], timeout: float = 30.0) -> McpToolset:
    """Build an MCP toolset over the Resonate ``/mcp`` server, limited to ``tool_filter``.

    Args:
        tool_filter: MCP tool names to expose (e.g. ``[CATALOG_SEARCH, STEM_QUOTE]``).
        timeout: per-request timeout in seconds.

    Returns:
        An ADK ``McpToolset`` (lazily connected).
    """
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=config.mcp_url,
            headers=_headers(),
            timeout=timeout,
        ),
        tool_filter=tool_filter,
    )


def discovery_toolset() -> McpToolset:
    """Public discovery tools for the catalog agent."""
    return resonate_mcp_toolset([CATALOG_SEARCH, STEM_QUOTE])


def commerce_toolset() -> McpToolset:
    """Quote + paid download for the commerce agent (download is x402-gated)."""
    return resonate_mcp_toolset([STEM_QUOTE, STEM_DOWNLOAD], timeout=60.0)
