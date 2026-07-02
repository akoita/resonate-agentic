"""Input parsing for workflow entry nodes (#33).

Entry nodes receive either structured JSON (from a calling agent or API) or
free natural language (from a user). Parsing is deterministic — no LLM call —
so it is testable offline and cannot invent fields:

- a JSON object is validated directly against the Pydantic input schema;
- otherwise conservative keyword/regex extraction fills the schema, falling
  back to its defaults.
"""

from __future__ import annotations

import json
import re
from typing import Any

from google.genai import types
from pydantic import ValidationError

from app.schemas import ArtistUploadInput, DiscoveryPurchaseInput, LicenseType


def node_text(node_input: Any) -> str:
    """Extract the raw text from an ADK workflow node input."""
    if isinstance(node_input, types.Content):
        return node_input.parts[0].text if node_input.parts else ""
    if isinstance(node_input, str):
        return node_input
    return str(node_input)


def _try_json(text: str) -> dict | None:
    text = text.strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ─── Discovery → purchase ───────────────────────────────────────────

# "budget $5", "under 5 USDC", "max $0.50", "up to 5 dollars", or a bare "$5"
_BUDGET_RE = re.compile(
    r"(?:budget(?:\s+of)?|under|max(?:imum)?|up\s+to|at\s+most|less\s+than)"
    r"[^\d$]{0,12}\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_AUTO_PURCHASE_RE = re.compile(r"\b(buy|purchase|get\s+me)\b", re.IGNORECASE)


def parse_discovery_input(node_input: Any) -> DiscoveryPurchaseInput:
    """Parse a discovery request (JSON or natural language) into the schema."""
    text = node_text(node_input)

    data = _try_json(text)
    if data is not None:
        try:
            return DiscoveryPurchaseInput.model_validate(data)
        except ValidationError:
            pass  # malformed structure — treat the raw text as a query

    license_type = LicenseType.personal
    for lic in LicenseType:
        if re.search(rf"\b{lic.value}\b", text, re.IGNORECASE):
            license_type = lic
            break

    match = _BUDGET_RE.search(text)
    budget = float(match.group(1) or match.group(2)) if match else 10.0

    return DiscoveryPurchaseInput(
        query=text,
        license_type=license_type,
        max_budget_usd=budget,
        auto_purchase=bool(_AUTO_PURCHASE_RE.search(text)),
    )


# ─── Artist upload ───────────────────────────────────────────────────

_QUOTED_TITLE_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{1,120})[\"“”'‘’]")
_BY_ARTIST_RE = re.compile(
    r"\bby\s+([A-Za-z0-9][\w .&-]{0,60}?)(?=\s*(?:[,.;!\n]|$|\bwith\b|\bfrom\b))",
    re.IGNORECASE,
)
_AUDIO_URL_RE = re.compile(
    r"(https?://\S+|(?:/|\./|~/)?[\w./-]+\.(?:wav|mp3|flac|aiff?|m4a|ogg))",
    re.IGNORECASE,
)


def parse_upload_input(node_input: Any) -> tuple[ArtistUploadInput | None, list[str]]:
    """Parse an upload request into (schema, issues).

    Returns ``(None, issues)`` when required fields can't be recovered —
    the caller decides how to surface the validation failure.
    """
    text = node_text(node_input)

    data = _try_json(text)
    if data is not None:
        try:
            return ArtistUploadInput.model_validate(data), []
        except ValidationError as e:
            return None, [
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in e.errors()
            ]

    title_match = _QUOTED_TITLE_RE.search(text)
    artist_match = _BY_ARTIST_RE.search(text)
    audio_match = _AUDIO_URL_RE.search(text)

    issues: list[str] = []
    if not title_match:
        issues.append("title: not found — put the release title in quotes")
    if not artist_match:
        issues.append("artist_name: not found — say 'by <artist name>'")
    if not audio_match:
        issues.append("audio_url: not found — include a URL or audio file path")
    if issues:
        return None, issues

    return (
        ArtistUploadInput(
            title=title_match.group(1).strip(),
            artist_name=artist_match.group(1).strip(),
            audio_url=audio_match.group(1).strip(),
        ),
        [],
    )
