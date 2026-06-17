"""Offline tests for the MCP toolset wiring (#7 / BL-01).

McpToolset construction is lazy (no network at import), so we can assert the toolset is built with
the right endpoint + tool filter, and that the agents carry it, without hitting the live MCP server.
"""

from __future__ import annotations

from google.adk.tools.mcp_tool import McpToolset

from app.config import config
from app.tools.mcp import (
    CATALOG_SEARCH,
    STEM_DOWNLOAD,
    STEM_QUOTE,
    commerce_toolset,
    discovery_toolset,
    resonate_mcp_toolset,
)


def test_toolset_points_at_mcp_url_with_filter():
    ts = resonate_mcp_toolset([CATALOG_SEARCH, STEM_QUOTE])
    assert isinstance(ts, McpToolset)
    # connection params carry the configured /mcp URL
    assert ts._connection_params.url == config.mcp_url
    assert config.mcp_url.endswith("/mcp")


def test_discovery_and_commerce_filters():
    assert discovery_toolset().tool_filter == [CATALOG_SEARCH, STEM_QUOTE]
    assert commerce_toolset().tool_filter == [STEM_QUOTE, STEM_DOWNLOAD]


def test_agents_carry_the_mcp_toolset():
    from app.agents import catalog_agent, commerce_agent

    assert any(isinstance(t, McpToolset) for t in catalog_agent.tools), "catalog_agent missing MCP toolset"
    assert any(isinstance(t, McpToolset) for t in commerce_agent.tools), "commerce_agent missing MCP toolset"


def test_root_agent_still_constructs():
    from app.agent import root_agent

    assert root_agent.name == "resonate"
    assert len(root_agent.sub_agents) == 8
