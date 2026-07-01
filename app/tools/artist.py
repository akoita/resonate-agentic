"""Artist management tools for the Resonate platform.

These tools enable artists to upload releases, set pricing,
mint stem NFTs, and view analytics. I/O tools are native ``async def``;
pure stubs remain sync.
"""

from __future__ import annotations

import httpx

from app.config import PRICE_COMMERCIAL_USD, PRICE_PERSONAL_USD, PRICE_REMIX_USD
from app.schemas import STEM_TYPES
from app.tools._http import api_get, api_post


async def release_upload(
    title: str,
    artist_name: str,
    genre: str | None = None,
    moods: list[str] | None = None,
    audio_url: str = "",
    explicit: bool = False,
) -> dict:
    """Upload a new music release for stem separation and cataloging.

    Initiates the full upload pipeline: audio → AI stem separation (Demucs htdemucs_6s)
    → metadata extraction → rights evaluation → catalog publication.

    Args:
        title: Release title.
        artist_name: Primary artist display name.
        genre: Genre classification (e.g. 'electronic', 'hip-hop').
        moods: Mood tags (e.g. ['chill', 'atmospheric']).
        audio_url: URL or path to the audio file to upload.
        explicit: Whether the release contains explicit content.

    Returns:
        Dictionary with release_id, processing status, and expected stems.
    """
    payload = {
        "title": title,
        "artistName": artist_name,
        "genre": genre,
        "moods": moods or [],
        "audioUrl": audio_url,
        "explicit": explicit,
    }

    try:
        data = await api_post("/api/releases/upload", json=payload, timeout=120.0)
        return {
            "status": "uploaded",
            "release_id": data.get("id", ""),
            "title": title,
            "processing_status": data.get("status", "processing"),
            "stem_types": list(STEM_TYPES),
            "message": "Release uploaded. Stem separation in progress (htdemucs_6s); the original mix is kept as a 7th stem.",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def stem_price(
    stem_id: str,
    base_price_usd: float = PRICE_PERSONAL_USD,
    remix_price_usd: float = PRICE_REMIX_USD,
    commercial_price_usd: float = PRICE_COMMERCIAL_USD,
) -> dict:
    """Set pricing tiers for a stem.

    STUB: returns a synthetic acknowledgement. The real implementation must
    persist pricing to the backend for the given stem.

    Args:
        stem_id: The stem to price.
        base_price_usd: Personal use price in USD (default $0.05).
        remix_price_usd: Remix license price in USD (default $5.00).
        commercial_price_usd: Commercial license price in USD (default $25.00).

    Returns:
        Dictionary confirming the pricing configuration.
    """
    return {
        "status": "priced",
        "stem_id": stem_id,
        "pricing": {
            "personal_usd": base_price_usd,
            "remix_usd": remix_price_usd,
            "commercial_usd": commercial_price_usd,
        },
        "stub": True,
        "message": "STUB — pricing was not persisted to the backend.",
    }


def stem_mint(
    stem_id: str,
    royalty_bps: int = 500,
    remixable: bool = True,
) -> dict:
    """Mint a stem as an ERC-1155 NFT on-chain.

    STUB: returns a synthetic acknowledgement. The real implementation must
    submit the on-chain mint transaction and return the real token_id / tx hash.

    Args:
        stem_id: The stem to mint.
        royalty_bps: Royalty percentage in basis points (500 = 5%).
        remixable: Whether derivative works are allowed.

    Returns:
        Dictionary with token_id, contract address, and transaction hash.
    """
    return {
        "status": "minted",
        "stem_id": stem_id,
        "token_id": 0,
        "royalty_bps": royalty_bps,
        "remixable": remixable,
        "stub": True,
        "message": "STUB — no on-chain mint transaction was submitted.",
    }


async def artist_analytics(artist_id: str) -> dict:
    """Get analytics and performance data for an artist.

    Returns play counts, revenue, stem sales, top tracks, and revenue trends.

    Args:
        artist_id: The artist whose analytics to retrieve.

    Returns:
        Dictionary with plays, revenue, sales, and top tracks.
    """
    try:
        try:
            data = await api_get(f"/analytics/artist/{artist_id}/v1", timeout=15.0)
            return {
                "status": "ok",
                "artist_id": artist_id,
                "total_plays": data.get("totalPlays", 0),
                "total_revenue_usd": data.get("totalRevenueUsd", 0.0),
                "total_stems_sold": data.get("totalStemsSold", 0),
                "top_tracks": data.get("topTracks", []),
            }
        except httpx.HTTPStatusError:
            return {
                "status": "ok",
                "artist_id": artist_id,
                "total_plays": 0,
                "total_revenue_usd": 0.0,
                "total_stems_sold": 0,
                "top_tracks": [],
                "message": "No analytics data available yet.",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
