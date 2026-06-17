"""AI DJ and recommendation tools for the Resonate platform.

These tools power the AI DJ agent — taste analysis, music recommendations,
session management, and playback control. All I/O tools are native ``async def``.
"""

from __future__ import annotations

import httpx

from app.tools._http import api_get, api_post


async def recommend_next(
    session_id: str,
    genres: list[str] | None = None,
    moods: list[str] | None = None,
    energy: str | None = None,
    license_type: str = "personal",
) -> dict:
    """Get the next AI DJ recommendation for an active session.

    Returns a taste-constrained, commerce-aware track recommendation
    with scoring, explanation signals, and purchase information.

    Args:
        session_id: Active AI DJ session ID.
        genres: Preferred genres (e.g. ['electronic', 'ambient']).
        moods: Preferred moods (e.g. ['chill', 'uplifting']).
        energy: Energy level — 'low', 'medium', or 'high'.
        license_type: Preferred license tier for purchases.

    Returns:
        Dictionary with recommended track, price, score, explanation,
        and runtime status.
    """
    preferences: dict = {"licenseType": license_type}
    if genres:
        preferences["genres"] = genres
    if moods:
        preferences["moods"] = moods
    if energy:
        preferences["energy"] = energy

    try:
        data = await api_post(
            "/sessions/agent/next",
            json={"sessionId": session_id, "preferences": preferences},
        )
        return {
            "status": data.get("status", "ok"),
            "track": data.get("track"),
            "license_type": data.get("licenseType"),
            "price_usd": data.get("priceUsd"),
            "runtime_status": data.get("runtimeStatus", "approved"),
            "score": data.get("score"),
            "explanation": data.get("explanation", []),
            "signals": data.get("signals", []),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def session_manage(
    action: str,
    user_id: str,
    genres: list[str] | None = None,
    moods: list[str] | None = None,
    energy: str | None = None,
    budget_usd: float | None = None,
) -> dict:
    """Manage an AI DJ session — start, stop, pause, or resume.

    Use 'start' to create a new AI DJ session with taste preferences.
    Use 'stop' to end the session and get a summary.

    Args:
        action: One of 'start', 'stop', 'pause', 'resume'.
        user_id: The listener's user ID.
        genres: Preferred genres (for start/resume).
        moods: Preferred moods (for start/resume).
        energy: Energy preference (for start/resume).
        budget_usd: Maximum spend budget for the session.

    Returns:
        Dictionary with session_id, status, and session details.
    """
    payload: dict = {"action": action, "userId": user_id}
    if genres:
        payload["genres"] = genres
    if moods:
        payload["moods"] = moods
    if energy:
        payload["energy"] = energy
    if budget_usd is not None:
        payload["budgetUsd"] = budget_usd

    try:
        data = await api_post("/agents/config/session", json=payload, timeout=15.0)
        return {
            "status": "ok",
            "action": action,
            "session_id": data.get("sessionId", data.get("id", "")),
            "user_id": user_id,
            "session": data,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def taste_analyze(user_id: str) -> dict:
    """Analyze a listener's taste profile based on their listening history.

    Returns genre preferences, mood affinities, energy preferences,
    and top artists — useful for tuning AI DJ recommendations.

    Args:
        user_id: The listener whose taste to analyze.

    Returns:
        Dictionary with preferred genres, moods, energy level, top artists,
        and taste signals.
    """
    try:
        try:
            data = await api_get(f"/recommendations/{user_id}", timeout=15.0)
            return {
                "status": "ok",
                "user_id": user_id,
                "preferred_genres": data.get("genres", []),
                "preferred_moods": data.get("moods", []),
                "energy_preference": data.get("energy"),
                "top_artists": data.get("topArtists", []),
                "taste_signals": data.get("signals", []),
            }
        except httpx.HTTPStatusError:
            return {
                "status": "ok",
                "user_id": user_id,
                "preferred_genres": [],
                "preferred_moods": [],
                "energy_preference": None,
                "top_artists": [],
                "taste_signals": [],
                "message": "No listening history yet.",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
