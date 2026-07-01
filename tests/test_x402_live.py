"""Gated LIVE x402 settlement test (#9) — one real ~0.05-USDC purchase.

Never runs in CI. Requires explicit opt-in via env:

- ``RESONATE_X402_LIVE=1``           — explicit opt-in flag
- ``RESONATE_X402_TESTNET_KEY``      — funded **Base Sepolia** payer key (testnet only!)
- ``RESONATE_API_BASE``              — the staging backend base URL (never committed)
- ``RESONATE_X402_LIVE_STEM_ID``     — optional: pin the stem to buy; otherwise the
  cheapest personal-license stem in the storefront is used.

Safety rails: refuses to run unless the configured network is Base Sepolia
(``eip155:84532``), and refuses any stem priced above $0.10.
"""

from __future__ import annotations

import os

import pytest

import app.tools.payments as payments
from app.config import ResonateConfig

_ENABLED = bool(
    os.getenv("RESONATE_X402_LIVE") == "1"
    and os.getenv("RESONATE_X402_TESTNET_KEY")
    and os.getenv("RESONATE_API_BASE")
)

pytestmark = pytest.mark.skipif(
    not _ENABLED,
    reason=(
        "live x402 settlement needs RESONATE_X402_LIVE=1 + "
        "RESONATE_X402_TESTNET_KEY + RESONATE_API_BASE"
    ),
)

MAX_LIVE_PRICE_USD = 0.10


@pytest.fixture
def live_config(monkeypatch):
    monkeypatch.setenv("X402_PRIVATE_KEY", os.environ["RESONATE_X402_TESTNET_KEY"])
    cfg = ResonateConfig()
    assert cfg.x402_network == "eip155:84532", "live settlement is testnet-only"
    monkeypatch.setattr(payments, "config", cfg)
    return cfg


def _iter_stems(payload) -> list[dict]:
    """Normalize the storefront listing payload into a flat stem list."""
    if isinstance(payload, dict):
        for key in ("items", "stems", "results", "data"):
            if isinstance(payload.get(key), list):
                return [s for s in payload[key] if isinstance(s, dict)]
    if isinstance(payload, list):
        return [s for s in payload if isinstance(s, dict)]
    return []


def _price_usd(stem: dict) -> float | None:
    price = stem.get("price")
    if isinstance(price, dict) and isinstance(price.get("usd"), (int, float)):
        return float(price["usd"])
    for key in ("priceUsd", "price_usd", "basePlayPriceUsd"):
        if isinstance(stem.get(key), (int, float)):
            return float(stem[key])
    return None


async def test_live_discover_quote_pay_receipt(live_config):
    from app.tools.catalog import catalog_browse, stem_quote
    from app.tools.commerce import stem_purchase

    stem_id = os.getenv("RESONATE_X402_LIVE_STEM_ID", "")
    if not stem_id:
        browse = await catalog_browse(limit=50)
        assert browse["status"] == "ok", f"storefront browse failed: {browse}"
        stems = _iter_stems(browse.get("releases"))
        priced = [(s, _price_usd(s)) for s in stems]
        affordable = [
            (s, p) for s, p in priced if p is not None and 0 < p <= MAX_LIVE_PRICE_USD
        ]
        assert affordable, f"no stem priced ≤ ${MAX_LIVE_PRICE_USD} found in storefront"
        stem, price = min(affordable, key=lambda sp: sp[1])
        stem_id = stem.get("id") or stem.get("stemId")
        assert stem_id, f"stem entry has no id: {stem}"

    quote = await stem_quote(stem_id, license_type="personal")
    assert quote["status"] == "ok", f"quote failed: {quote}"

    out = await stem_purchase(stem_id, license_type="personal")
    assert out["status"] == "purchased", f"live purchase failed: {out}"
    assert out["size_bytes"] > 0
    assert out["receipt_id"] or out["receipt"] or out["payment_response"], (
        f"settled but no receipt surfaced: {out}"
    )
    print(  # visible with pytest -s: the settlement evidence for #9
        f"LIVE RECEIPT stem={stem_id} receipt_id={out['receipt_id']!r} "
        f"payment_response={out['payment_response'][:120]!r} payer={out['payer']}"
    )
