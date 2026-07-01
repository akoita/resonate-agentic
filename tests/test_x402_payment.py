"""Offline x402 payment tests (#9).

Prove the in-app payment client end-to-end without any network: a respx-mocked
backend issues a V2 402 challenge (``PAYMENT-REQUIRED`` header), the x402 SDK
signs an EIP-3009 authorization, and the retried request carries
``PAYMENT-SIGNATURE``. The signature is verified by EIP-712 recovery, so the
signing path is proven correct offline; the real settlement is covered by the
gated live test in ``test_x402_live.py``.

Also prove the two in-client guards: challenges on a foreign network or above
the per-purchase cap are never paid.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx
from eth_account import Account
from eth_account.messages import encode_typed_data

import app.tools.payments as payments
from app.config import ResonateConfig
from app.tools.commerce import stem_purchase

# Throwaway deterministic test wallet (valid secp256k1 scalar, no funds).
TEST_WALLET_HEX = "0x" + "ab" * 32
TEST_WALLET_ADDRESS = Account.from_key(TEST_WALLET_HEX).address

USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
PAY_TO = "0x1111111111111111111111111111111111111111"


@pytest.fixture
def x402_config(monkeypatch):
    """Enable auto-pay with the test wallet (overrides the conftest default)."""
    monkeypatch.setenv("X402_PRIVATE_KEY", TEST_WALLET_HEX)
    cfg = ResonateConfig()
    monkeypatch.setattr(payments, "config", cfg)
    return cfg


def _challenge(amount: str, network: str) -> str:
    """Encode a V2 PAYMENT-REQUIRED header for the given amount/network."""
    from x402.http.utils import encode_payment_required_header
    from x402.schemas.payments import PaymentRequired, PaymentRequirements

    return encode_payment_required_header(
        PaymentRequired(
            accepts=[
                PaymentRequirements(
                    scheme="exact",
                    network=network,
                    asset=USDC,
                    amount=amount,
                    payTo=PAY_TO,
                    maxTimeoutSeconds=300,
                    extra={"name": "USDC", "version": "2"},
                )
            ]
        )
    )


def _paywall(challenge_header: str, captured: dict):
    """Responder: 402 until a PAYMENT-SIGNATURE arrives, then 200 + receipt."""

    def responder(request: httpx.Request) -> httpx.Response:
        sig = request.headers.get("PAYMENT-SIGNATURE")
        if sig:
            captured["signature_header"] = sig
            return httpx.Response(
                200,
                headers={"X-Resonate-Receipt-Id": "r-test-1"},
                content=b"stem-bytes",
            )
        return httpx.Response(402, headers={"PAYMENT-REQUIRED": challenge_header})

    return responder


@respx.mock
async def test_stem_purchase_auto_pays_and_signature_recovers(x402_config):
    captured: dict = {}
    respx.get(f"{x402_config.api_base}/api/stems/s1/x402").mock(
        side_effect=_paywall(_challenge("50000", x402_config.x402_network), captured)
    )

    out = await stem_purchase("s1", license_type="personal")

    assert out["status"] == "purchased"
    assert out["receipt_id"] == "r-test-1"
    assert out["payer"] == TEST_WALLET_ADDRESS

    payload = json.loads(base64.b64decode(captured["signature_header"]))
    auth = payload["payload"]["authorization"]
    assert auth["to"] == PAY_TO
    assert auth["value"] == "50000"

    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USDC",
            "version": "2",
            "chainId": int(x402_config.x402_network.split(":")[1]),
            "verifyingContract": USDC,
        },
        "message": {
            "from": auth["from"],
            "to": auth["to"],
            "value": int(auth["value"]),
            "validAfter": int(auth["validAfter"]),
            "validBefore": int(auth["validBefore"]),
            "nonce": bytes.fromhex(auth["nonce"].removeprefix("0x")),
        },
    }
    recovered = Account.recover_message(
        encode_typed_data(full_message=typed),
        signature=payload["payload"]["signature"],
    )
    assert recovered == TEST_WALLET_ADDRESS


@respx.mock
async def test_foreign_network_challenge_is_never_paid(x402_config):
    """A mainnet challenge must not be payable with a testnet-scoped client."""
    captured: dict = {}
    respx.get(f"{x402_config.api_base}/api/stems/s1/x402").mock(
        side_effect=_paywall(_challenge("50000", "eip155:8453"), captured)
    )

    out = await stem_purchase("s1")

    assert out["status"] == "error"
    assert "signature_header" not in captured


@respx.mock
async def test_over_cap_challenge_is_never_paid(x402_config):
    """A quote above max_purchase_usd must not be paid (cap = 25 USDC)."""
    captured: dict = {}
    over_cap = str(int((x402_config.max_purchase_usd + 1) * 10**6))
    respx.get(f"{x402_config.api_base}/api/stems/s1/x402").mock(
        side_effect=_paywall(_challenge(over_cap, x402_config.x402_network), captured)
    )

    out = await stem_purchase("s1")

    assert out["status"] == "error"
    assert "signature_header" not in captured


@respx.mock
async def test_without_wallet_key_returns_challenge():
    """No key configured (conftest default) → old behavior: surface the 402."""
    cfg = payments.config
    assert not payments.x402_enabled()
    respx.get(f"{cfg.api_base}/api/stems/s1/x402").mock(
        return_value=httpx.Response(
            402, headers={"PAYMENT-REQUIRED": _challenge("50000", cfg.x402_network)}
        )
    )

    out = await stem_purchase("s1")

    assert out["status"] == "payment_required"
    assert out["challenge"]
