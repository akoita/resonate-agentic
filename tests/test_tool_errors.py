"""Error-path tests for backend tools (offline via respx).

Tools must honor the "dict with a 'status' key" contract on failure paths —
4xx/5xx, 402 challenges, and transport errors — not just happy paths.
Also pins the 7-stem-type contract (vocals … other + original, ADR-0001).
"""

from __future__ import annotations

import httpx
import respx

from app.config import config
from app.schemas import STEM_TYPES
from app.tools.artist import release_upload
from app.tools.catalog import catalog_search, stem_info
from app.tools.commerce import budget_check, stem_purchase

BASE = config.api_base


@respx.mock
async def test_catalog_search_5xx_returns_error_status():
    respx.get(f"{BASE}/api/storefront/stems").mock(return_value=httpx.Response(500))
    out = await catalog_search("lofi bass")
    assert out["status"] == "error"
    assert out["query"] == "lofi bass"


@respx.mock
async def test_stem_info_404_returns_not_found():
    respx.get(f"{BASE}/api/stems/missing/x402/info").mock(
        return_value=httpx.Response(404)
    )
    out = await stem_info("missing")
    assert out["status"] == "not_found"
    assert out["stem_id"] == "missing"


@respx.mock
async def test_stem_purchase_402_surfaces_challenge():
    respx.get(f"{BASE}/api/stems/s1/x402").mock(
        return_value=httpx.Response(402, headers={"PAYMENT-REQUIRED": "challenge-blob"})
    )
    out = await stem_purchase("s1", license_type="remix")
    assert out["status"] == "payment_required"
    assert out["challenge"] == "challenge-blob"


@respx.mock
async def test_stem_purchase_success_returns_receipt():
    respx.get(f"{BASE}/api/stems/s1/x402").mock(
        return_value=httpx.Response(
            200,
            headers={"X-Resonate-Receipt-Id": "r-1", "X-Resonate-Receipt": "sig"},
            content=b"audio-bytes",
        )
    )
    out = await stem_purchase("s1", payment_proof="proof-b64")
    assert out["status"] == "purchased"
    assert out["receipt_id"] == "r-1"
    assert out["size_bytes"] == len(b"audio-bytes")


@respx.mock
async def test_stem_purchase_sends_auth_and_payment_headers():
    route = respx.get(f"{BASE}/api/stems/s1/x402").mock(
        return_value=httpx.Response(402)
    )
    await stem_purchase("s1", payment_proof="proof-b64", buyer_wallet="0xabc")
    sent = route.calls.last.request.headers
    assert sent["X-PAYMENT"] == "proof-b64"
    assert sent["X-Resonate-Buyer"] == "0xabc"


@respx.mock
async def test_stem_purchase_transport_error_returns_error():
    respx.get(f"{BASE}/api/stems/s1/x402").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    out = await stem_purchase("s1")
    assert out["status"] == "error"
    assert "error" in out


@respx.mock
async def test_budget_check_falls_back_to_default_cap_on_404():
    respx.get(f"{BASE}/api/wallet/budget/u1").mock(return_value=httpx.Response(404))
    out = await budget_check("u1")
    assert out["status"] == "ok"
    assert out["remaining_usd"] == config.default_budget_usd
    assert out["can_purchase"] is True


@respx.mock
async def test_budget_check_transport_error_returns_error():
    respx.get(f"{BASE}/api/wallet/budget/u1").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    out = await budget_check("u1")
    assert out["status"] == "error"


@respx.mock
async def test_release_upload_exposes_all_seven_stem_types():
    respx.post(f"{BASE}/api/releases/upload").mock(
        return_value=httpx.Response(200, json={"id": "rel-1", "status": "processing"})
    )
    out = await release_upload(title="T", artist_name="A")
    assert out["status"] == "uploaded"
    assert set(out["stem_types"]) == set(STEM_TYPES)
    assert "original" in out["stem_types"]
