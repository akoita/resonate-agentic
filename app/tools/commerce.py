"""Commerce and payment tools for the Resonate platform.

These tools handle stem purchases via x402, marketplace listings,
and budget management for autonomous agent spending.

I/O tools are native ``async def``; pure stubs remain sync.
"""

from __future__ import annotations

import httpx

from app.config import config
from app.tools._http import _auth_headers, api_get, api_get_raw
from app.tools.payments import payer_address, payment_client, x402_enabled


def _receipt(resp: httpx.Response, stem_id: str, license_type: str) -> dict:
    """Normalize a successful purchase response into the tool result."""
    return {
        "status": "purchased",
        "stem_id": stem_id,
        "license_type": license_type,
        "receipt_id": resp.headers.get("X-Resonate-Receipt-Id", ""),
        "receipt": resp.headers.get("X-Resonate-Receipt", ""),
        "license": resp.headers.get("X-Resonate-License", ""),
        "payment_response": resp.headers.get("PAYMENT-RESPONSE", ""),
        "content_type": resp.headers.get("content-type", ""),
        "size_bytes": len(resp.content),
    }


async def stem_purchase(
    stem_id: str,
    license_type: str = "personal",
    payment_proof: str | None = None,
    buyer_wallet: str | None = None,
) -> dict:
    """Purchase a stem via the x402 payment protocol.

    With a configured payer wallet (``X402_PRIVATE_KEY``), executes the full
    flow — challenge → signed EIP-3009 payment → settlement → receipt — via
    the in-app x402 client (network + per-payment cap enforced; see
    ``app/tools/payments.py``). Without one, returns the 402 challenge, or
    forwards an externally produced ``payment_proof`` if given.

    Args:
        stem_id: The stem to purchase.
        license_type: License tier — 'personal', 'remix', or 'commercial'.
        payment_proof: Pre-built x402 payment header value (base64). Optional.
        buyer_wallet: Recipient wallet address for NFT delivery.

    Returns:
        Dict with 'purchased' status + receipt on success, 'payment_required'
        + challenge when unpaid, or 'error'.
    """
    extra: dict[str, str] = {}
    if buyer_wallet:
        extra["X-Resonate-Buyer"] = buyer_wallet

    try:
        if payment_proof is None and x402_enabled():
            # Auto-pay: the x402 transport answers the 402 with a signed
            # authorization and retries; a still-402 means payment was refused.
            async with payment_client(timeout=60.0) as client:
                resp = await client.get(
                    f"/api/stems/{stem_id}/x402",
                    params={"licenseType": license_type},
                    headers=_auth_headers(extra),
                )
                if resp.status_code == 402:
                    return {
                        "status": "payment_required",
                        "stem_id": stem_id,
                        "license_type": license_type,
                        "challenge": resp.headers.get("PAYMENT-REQUIRED", ""),
                        "payer": payer_address(),
                        "detail": "payment attempted but not accepted",
                    }
                resp.raise_for_status()
                return _receipt(resp, stem_id, license_type) | {
                    "payer": payer_address()
                }

        headers = dict(extra)
        if payment_proof:
            headers["X-PAYMENT"] = payment_proof
        resp = await api_get_raw(
            f"/api/stems/{stem_id}/x402",
            params={"licenseType": license_type},
            headers=headers,
            timeout=60.0,
        )

        if resp.status_code == 402:
            return {
                "status": "payment_required",
                "stem_id": stem_id,
                "license_type": license_type,
                "challenge": resp.headers.get("PAYMENT-REQUIRED", ""),
            }

        resp.raise_for_status()
        return _receipt(resp, stem_id, license_type)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def marketplace_list(
    stem_id: str,
    price_usd: float,
    license_type: str = "personal",
    duration_days: int = 30,
) -> dict:
    """List a stem for sale on the Resonate marketplace.

    STUB: returns a synthetic acknowledgement. The real implementation must call
    the marketplace listing endpoint and submit the on-chain listing transaction.

    Args:
        stem_id: The stem to list.
        price_usd: Price in USD (will be converted to USDC).
        license_type: License tier — 'personal', 'remix', or 'commercial'.
        duration_days: How many days the listing stays active (default 30).

    Returns:
        Dictionary with listing details including status.
    """
    return {
        "status": "listed",
        "stem_id": stem_id,
        "price_usd": price_usd,
        "license_type": license_type,
        "duration_days": duration_days,
        "stub": True,
        "message": "STUB — no backend/on-chain listing was created.",
    }


async def budget_check(user_id: str) -> dict:
    """Check the current budget and spending status for an agent wallet.

    Use this before purchases to verify the agent has sufficient funds
    and hasn't exceeded its monthly spending cap.

    Args:
        user_id: The user whose agent budget to check.

    Returns:
        Dictionary with balance, monthly cap, spent amount, remaining budget,
        and whether purchases are allowed.
    """
    try:
        try:
            data = await api_get(f"/api/wallet/budget/{user_id}", timeout=15.0)
            remaining = data.get("monthlyCapUsd", 50.0) - data.get("spentUsd", 0.0)
            return {
                "status": "ok",
                "user_id": user_id,
                "balance_usd": data.get("balanceUsd", 0.0),
                "monthly_cap_usd": data.get("monthlyCapUsd", 50.0),
                "spent_usd": data.get("spentUsd", 0.0),
                "remaining_usd": max(0.0, remaining),
                "can_purchase": remaining > 0,
            }
        except httpx.HTTPStatusError:
            # No budget record yet — fall back to the configured default cap.
            return {
                "status": "ok",
                "user_id": user_id,
                "balance_usd": config.default_budget_usd,
                "monthly_cap_usd": config.default_budget_usd,
                "spent_usd": 0.0,
                "remaining_usd": config.default_budget_usd,
                "can_purchase": True,
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
