"""Artist Upload workflow using ADK 2.0 Workflow API.

Orchestrates: START → validate → (parallel: stem_separation, metadata) → join
→ rights_evaluation → pricing → mint → publish
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.workflow import JoinNode, Workflow
from pydantic import BaseModel

from app.config import (
    PRICE_COMMERCIAL_USD,
    PRICE_PERSONAL_USD,
    PRICE_REMIX_USD,
    config,
)
from app.schemas import STEM_TYPES
from app.tools.artist import release_upload
from app.workflows._parsing import node_text, parse_upload_input


# ─── Schemas ─────────────────────────────────────────────────────────


class RightsEvaluation(BaseModel):
    rights_route: str  # verified_independent, unverified_uploader, trusted_creator
    can_publish: bool
    reason: str


# ─── Nodes ───────────────────────────────────────────────────────────


def validate_upload(ctx: Context, node_input: Any) -> Event:
    """Validate and parse the upload request (JSON or natural language)."""
    text = node_text(node_input)
    parsed, issues = parse_upload_input(node_input)
    if parsed is None:
        return Event(
            output={"is_valid": False, "issues": issues, "raw_input": text},
            state={"upload_input": text, "upload_valid": False},
        )
    return Event(
        output={
            "is_valid": True,
            "issues": [],
            "raw_input": text,
            **parsed.model_dump(mode="json"),
        },
        state={"upload_input": text, "upload_valid": True},
    )


async def process_stems(node_input: dict) -> dict:
    """Trigger stem separation via Demucs."""
    if not node_input.get("is_valid", True):
        return {"status": "invalid_upload", "issues": node_input.get("issues", [])}
    return await release_upload(
        title=node_input.get("title", "Untitled"),
        artist_name=node_input.get("artist_name", "Unknown"),
        genre=node_input.get("genre"),
        moods=node_input.get("moods", []),
        audio_url=node_input.get("audio_url", ""),
    )


def extract_metadata(node_input: dict) -> dict:
    """Extract and enrich release metadata."""
    if not node_input.get("is_valid", True):
        return {"status": "invalid_upload", "issues": node_input.get("issues", [])}
    return {
        "title": node_input.get("title", "Untitled"),
        "artist": node_input.get("artist_name", "Unknown"),
        "genre": node_input.get("genre"),
        "moods": node_input.get("moods", []),
        "stem_types": list(STEM_TYPES),
    }


join_processing = JoinNode(name="join_processing")


rights_evaluator = LlmAgent(
    name="rights_evaluator",
    model=config.model_name,
    instruction="""You are evaluating the rights status of a music upload.
Based on the upload metadata and processing results, determine:
- Whether this is original work or requires verification
- The appropriate rights route (verified_independent, unverified_uploader, trusted_creator)
- Whether the release can proceed to publication

Be conservative — flag anything that needs human review.""",
    output_schema=RightsEvaluation,
    output_key="rights_evaluation",
)


def set_pricing(ctx: Context, node_input: Any) -> dict:
    """Configure default pricing for all stems."""
    rights = ctx.state.get("rights_evaluation", {})
    if not rights.get("can_publish", False):
        return Event(
            output={"status": "blocked", "reason": rights.get("reason", "Rights review needed")},
            route="blocked",
        )
    return {
        "status": "priced",
        "pricing": {
            "personal_usd": PRICE_PERSONAL_USD,
            "remix_usd": PRICE_REMIX_USD,
            "commercial_usd": PRICE_COMMERCIAL_USD,
        },
    }


def mint_stems(node_input: dict) -> dict:
    """Mint all stems as NFTs."""
    if node_input.get("status") == "blocked":
        return node_input
    return {
        "status": "minted",
        "stem_count": 6,
        "message": "All 6 stems minted as ERC-1155 NFTs with 5% royalty.",
    }


def publish_release(node_input: dict) -> dict:
    """Publish the release to the catalog."""
    if node_input.get("status") == "blocked":
        return node_input
    return {
        "status": "published",
        "message": "Release published to the Resonate catalog. Stems are now purchasable.",
    }


# ─── Workflow Graph ──────────────────────────────────────────────────

artist_upload_workflow = Workflow(
    name="artist_upload",
    description="Full artist upload pipeline: validate → process stems + metadata → rights → price → mint → publish.",
    edges=[
        ("START", validate_upload),
        (validate_upload, (process_stems, extract_metadata)),
        ((process_stems, extract_metadata), join_processing),
        (join_processing, rights_evaluator),
        (rights_evaluator, set_pricing),
        (set_pricing, mint_stems),
        (mint_stems, publish_release),
    ],
)
