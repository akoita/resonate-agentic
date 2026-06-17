"""Community and social tools for the Resonate platform.

These tools manage community rooms, taste cohorts, and Shows fan-funding
campaigns. I/O tools are native ``async def``; pure stubs remain sync.
"""

from __future__ import annotations

import httpx

from app.tools._http import api_get


async def room_manage(
    action: str,
    room_type: str = "public",
    artist_id: str | None = None,
    title: str | None = None,
    user_id: str | None = None,
) -> dict:
    """Manage community rooms — create, join, leave, or list.

    Community rooms are spaces for listeners, holders, and supporters
    to interact around artists, campaigns, and shared taste.

    NOTE: only 'list' is backed by a real endpoint; create/join/leave are stubs.

    Args:
        action: One of 'create', 'join', 'leave', 'list'.
        room_type: Room type — 'public', 'holder', 'supporter', 'cohort'.
        artist_id: Artist the room belongs to (for create/list).
        title: Room title (for create).
        user_id: User performing the action (for join/leave).

    Returns:
        Dictionary with room details or list of rooms.
    """
    try:
        if action == "list" and artist_id:
            rooms = await api_get(f"/community/artists/{artist_id}/rooms", timeout=15.0)
            return {"status": "ok", "action": "list", "rooms": rooms}

        return {
            "status": "ok",
            "action": action,
            "room_type": room_type,
            "artist_id": artist_id,
            "title": title,
            "stub": True,
            "message": f"STUB — room '{action}' was not persisted.",
        }
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def cohort_discover(user_id: str) -> dict:
    """Discover taste-based cohorts the listener might be interested in.

    Taste cohorts are groups of listeners with similar preferences,
    generated from safe transactional signals. Joining a cohort
    can influence AI DJ recommendations.

    Args:
        user_id: The listener to find cohorts for.

    Returns:
        Dictionary with suggested cohorts and their descriptions.
    """
    try:
        try:
            cohorts = await api_get("/community/cohorts/suggestions", timeout=15.0)
            return {"status": "ok", "user_id": user_id, "cohorts": cohorts}
        except httpx.HTTPStatusError:
            return {
                "status": "ok",
                "user_id": user_id,
                "cohorts": [],
                "message": "No cohort suggestions available.",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def shows_campaign(
    action: str,
    campaign_id: str | None = None,
    title: str | None = None,
    artist_id: str | None = None,
    city: str | None = None,
    funding_goal_usd: float | None = None,
    pledge_amount_usd: float | None = None,
    user_id: str | None = None,
) -> dict:
    """Manage Resonate Shows — fan-funded artist booking campaigns.

    STUB: returns a synthetic acknowledgement. The real implementation must call
    the Shows campaign endpoints and manage the funding escrow.

    Args:
        action: One of 'create', 'pledge', 'activate', 'cancel', 'view'.
        campaign_id: Campaign ID (for pledge/activate/cancel/view).
        title: Campaign title (for create).
        artist_id: Artist to book (for create).
        city: Target city (for create).
        funding_goal_usd: Funding target in USD (for create).
        pledge_amount_usd: Pledge amount in USD (for pledge).
        user_id: User performing the action.

    Returns:
        Dictionary with campaign details, funding status, and backer info.
    """
    return {
        "status": "ok",
        "action": action,
        "campaign_id": campaign_id,
        "title": title,
        "artist_id": artist_id,
        "city": city,
        "funding_goal_usd": funding_goal_usd,
        "stub": True,
        "message": f"STUB — campaign '{action}' was not persisted.",
    }
