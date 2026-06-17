"""Shared async HTTP helpers for Resonate backend calls.

All Resonate tools are native ``async def`` so ADK can await them directly
inside its running event loop. Do NOT wrap these in ``asyncio.run`` /
``run_until_complete`` from a tool — that crashes with "event loop is already
running" when ADK dispatches the tool.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import config


def _auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build request headers, including backend auth when configured."""
    headers: dict[str, str] = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if extra:
        headers.update(extra)
    return headers


async def api_get(
    path: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
) -> Any:
    """Authenticated async GET against the Resonate backend; returns parsed JSON."""
    async with httpx.AsyncClient(base_url=config.api_base, timeout=timeout) as client:
        resp = await client.get(path, params=params, headers=_auth_headers(headers))
        resp.raise_for_status()
        return resp.json()


async def api_post(
    path: str,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
) -> Any:
    """Authenticated async POST against the Resonate backend; returns parsed JSON."""
    async with httpx.AsyncClient(base_url=config.api_base, timeout=timeout) as client:
        resp = await client.post(path, json=json, headers=_auth_headers(headers))
        resp.raise_for_status()
        return resp.json()
