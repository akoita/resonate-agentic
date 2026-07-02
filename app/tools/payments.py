"""x402 payment client (EVM "exact" scheme) for stem purchases — #9.

Builds an httpx ``AsyncClient`` that transparently answers x402 402
challenges: on a 402 the x402 SDK signs an EIP-3009 authorization with the
configured wallet key and retries with the payment header. Settlement is
gasless for the payer (the facilitator submits the transfer).

Two hard limits are enforced *inside* the client, independent of the agent
budget guardrail (defense in depth, see docs/plans/9-x402-proof.md):
- only challenges on ``config.x402_network`` are payable (a mainnet quote
  can never be paid with a testnet-scoped configuration, and vice versa);
- a single payment is capped at ``config.max_purchase_usd``.

The wallet key comes from ``X402_PRIVATE_KEY`` (env / managed secret —
never committed, AGENTS.md rule 5). No key → payments disabled and
``stem_purchase`` falls back to returning the 402 challenge.
"""

from __future__ import annotations

import httpx

from app.config import config

USDC_DECIMALS = 6


def x402_enabled() -> bool:
    """True when a payer wallet key is configured."""
    return bool(config.x402_private_key)


def payer_address() -> str:
    """Address of the configured payer wallet ("" when disabled)."""
    if not x402_enabled():
        return ""
    from eth_account import Account

    return Account.from_key(config.x402_private_key).address


def payment_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """httpx client that auto-pays x402 challenges within the configured limits.

    Raises:
        ValueError: if no wallet key is configured.
    """
    if not x402_enabled():
        raise ValueError("x402 payments disabled: X402_PRIVATE_KEY is not set")

    from eth_account import Account
    from x402.client import max_amount, x402Client
    from x402.http.clients.httpx import wrapHttpxWithPayment
    from x402.mechanisms.evm.exact import register_exact_evm_client
    from x402.mechanisms.evm.signers import EthAccountSigner

    account = Account.from_key(config.x402_private_key)
    client = x402Client()
    register_exact_evm_client(
        client,
        EthAccountSigner(account),
        networks=config.x402_network,
        policies=[max_amount(int(config.max_purchase_usd * 10**USDC_DECIMALS))],
    )
    return wrapHttpxWithPayment(client, base_url=config.api_base, timeout=timeout)
