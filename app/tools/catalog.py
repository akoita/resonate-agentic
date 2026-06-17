"""Catalog discovery tools for the Resonate platform.

These tools enable agents to search, browse, and inspect the
Resonate music catalog — releases, tracks, and stems.

All tools are native ``async def`` — ADK awaits them directly.
"""

from __future__ import annotations

import httpx

from app.tools._http import api_get


async def catalog_search(
    query: str,
    limit: int = 10,
    genre: str | None = None,
    mood: str | None = None,
) -> dict:
    """Search the Resonate music catalog for releases, tracks, and stems.

    Use this tool when a user wants to find music by name, artist, genre, or mood.
    Returns a list of matching releases with track and stem information.

    Args:
        query: Search text — artist name, track title, genre, or description.
        limit: Maximum number of results to return (default 10, max 50).
        genre: Optional genre filter (e.g. 'electronic', 'hip-hop', 'jazz').
        mood: Optional mood filter (e.g. 'chill', 'energetic', 'melancholic').

    Returns:
        Dictionary with 'results' payload and the originating query.
    """
    params: dict = {"q": query, "limit": min(limit, 50)}
    if genre:
        params["genre"] = genre
    if mood:
        params["mood"] = mood

    try:
        result = await api_get("/api/storefront/stems", params=params)
        return {"status": "ok", "results": result, "query": query}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": str(e), "query": query}
    except Exception as e:
        return {"status": "error", "error": str(e), "query": query}


async def catalog_browse(
    genre: str | None = None,
    mood: str | None = None,
    sort: str = "recent",
    limit: int = 20,
) -> dict:
    """Browse the Resonate catalog by genre, mood, or recent additions.

    Use this when the user wants to explore music without a specific search query.
    Good for discovering new releases or browsing by category.

    Args:
        genre: Filter by genre (e.g. 'electronic', 'hip-hop', 'ambient').
        mood: Filter by mood (e.g. 'chill', 'dark', 'uplifting').
        sort: Sort order — 'recent' (default), 'popular', or 'price_asc'.
        limit: Number of results (default 20, max 50).

    Returns:
        Dictionary with 'releases' list and browsing metadata.
    """
    params: dict = {"sort": sort, "limit": min(limit, 50)}
    if genre:
        params["genre"] = genre
    if mood:
        params["mood"] = mood

    try:
        result = await api_get("/api/storefront/stems", params=params)
        return {"status": "ok", "releases": result, "filters": params}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def stem_info(stem_id: str) -> dict:
    """Get detailed information about a specific stem asset.

    Use this to inspect a stem's metadata, pricing tiers, rights, and
    purchase options before quoting or purchasing.

    Args:
        stem_id: The unique identifier of the stem.

    Returns:
        Dictionary with stem metadata, pricing, rights, and x402 config.
    """
    try:
        result = await api_get(f"/api/stems/{stem_id}/x402/info")
        return {"status": "ok", "stem": result}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"status": "not_found", "stem_id": stem_id}
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def stem_quote(stem_id: str, license_type: str = "personal") -> dict:
    """Get a price quote and x402 payment challenge for a stem.

    Use this before purchasing to see the exact USDC price and get the
    payment requirements needed for checkout.

    Args:
        stem_id: The unique identifier of the stem to quote.
        license_type: License tier — 'personal', 'remix', or 'commercial'.

    Returns:
        Dictionary with price_usdc, payment challenge, rights info, and
        available actions.
    """
    try:
        result = await api_get(
            f"/api/stems/{stem_id}/x402/info",
            params={"licenseType": license_type},
        )
        return {
            "status": "ok",
            "stem_id": stem_id,
            "license_type": license_type,
            "quote": result,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
