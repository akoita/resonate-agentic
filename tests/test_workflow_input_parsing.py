"""Offline tests for workflow entry-node input parsing (#33).

The entry nodes must populate their Pydantic input schemas from real input
(JSON or natural language) — no hardcoded titles/queries/budgets.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import respx

from app.config import config
from app.schemas import LicenseType
from app.workflows._parsing import parse_discovery_input, parse_upload_input
from app.workflows.artist_upload import (
    extract_metadata,
    process_stems,
    validate_upload,
)
from app.workflows.discovery_purchase import check_budget_node, parse_input


# ─── Discovery: natural language ─────────────────────────────────────


def test_discovery_nl_extracts_license_budget_and_intent():
    p = parse_discovery_input("Buy me a chill lofi bass stem to remix, budget $5")
    assert p.license_type == LicenseType.remix
    assert p.max_budget_usd == 5.0
    assert p.auto_purchase is True
    assert "lofi bass" in p.query


def test_discovery_nl_bare_dollar_amount():
    p = parse_discovery_input("find ambient textures under $2.50")
    assert p.max_budget_usd == 2.5
    assert p.auto_purchase is False


def test_discovery_nl_defaults():
    p = parse_discovery_input("find jazzy piano stems")
    assert p.license_type == LicenseType.personal
    assert p.max_budget_usd == 10.0
    assert p.auto_purchase is False
    assert p.query == "find jazzy piano stems"


def test_discovery_json_passthrough():
    payload = {
        "query": "dark techno drums",
        "license_type": "commercial",
        "max_budget_usd": 30,
        "auto_purchase": True,
    }
    p = parse_discovery_input(json.dumps(payload))
    assert p.query == "dark techno drums"
    assert p.license_type == LicenseType.commercial
    assert p.max_budget_usd == 30.0
    assert p.auto_purchase is True


def test_discovery_node_emits_parsed_state():
    ev = parse_input(None, "find ambient textures under $2")
    assert ev.output["query"] == "find ambient textures under $2"
    delta = ev.actions.state_delta
    assert delta["search_query"] == "find ambient textures under $2"
    assert delta["max_budget_usd"] == 2.0
    assert delta["license_type"] == "personal"


@respx.mock
async def test_budget_gate_honors_parsed_request_budget():
    """Wallet has plenty, but the request capped spend at $1 → rejected."""
    respx.get(f"{config.api_base}/api/wallet/budget/u1").mock(
        return_value=httpx.Response(404)  # falls back to the default $50 cap
    )
    ctx = SimpleNamespace(
        state={
            "user_id": "u1",
            "max_budget_usd": 1.0,
            "quote": {"quote": {"priceUsdc": 5.0}},
        }
    )
    ev = await check_budget_node(ctx, {})
    assert ev.actions.route == "rejected"
    assert ev.output["max_budget_usd"] == 1.0


@respx.mock
async def test_budget_gate_approves_within_both_limits():
    respx.get(f"{config.api_base}/api/wallet/budget/u1").mock(
        return_value=httpx.Response(404)
    )
    ctx = SimpleNamespace(
        state={
            "user_id": "u1",
            "max_budget_usd": 1.0,
            "quote": {"quote": {"priceUsdc": 0.05}},
        }
    )
    ev = await check_budget_node(ctx, {})
    assert ev.actions.route == "approved"


# ─── Artist upload ────────────────────────────────────────────────────


def test_upload_json_valid():
    payload = {
        "title": "Night Drive",
        "artist_name": "Koita",
        "audio_url": "https://cdn.example.test/night_drive.wav",
        "genre": "electronic",
    }
    ev = validate_upload(None, json.dumps(payload))
    assert ev.output["is_valid"] is True
    assert ev.output["title"] == "Night Drive"
    assert ev.output["artist_name"] == "Koita"
    assert ev.actions.state_delta["upload_valid"] is True


def test_upload_natural_language():
    parsed, issues = parse_upload_input(
        'Upload "Night Drive" by Koita from ./tracks/night_drive.wav'
    )
    assert issues == []
    assert parsed.title == "Night Drive"
    assert parsed.artist_name == "Koita"
    assert parsed.audio_url == "./tracks/night_drive.wav"


def test_upload_missing_fields_reported():
    ev = validate_upload(None, "please upload my new song")
    assert ev.output["is_valid"] is False
    joined = " ".join(ev.output["issues"])
    assert "title" in joined and "artist_name" in joined and "audio_url" in joined


def test_upload_json_missing_required_field_reports_issue():
    ev = validate_upload(None, json.dumps({"title": "No Audio"}))
    assert ev.output["is_valid"] is False
    assert any("artist_name" in i for i in ev.output["issues"])
    assert any("audio_url" in i for i in ev.output["issues"])


async def test_invalid_upload_passes_through_processing_nodes():
    invalid = {"is_valid": False, "issues": ["audio_url: not found"]}
    assert (await process_stems(invalid))["status"] == "invalid_upload"
    assert extract_metadata(invalid)["status"] == "invalid_upload"
