<!-- Ready-to-file issue for akoita/resonate (the backend repo). NOT tracked content
     for this repo — file it with:
     gh issue create --repo akoita/resonate --title "<title below>" --body-file <this file minus header>
-->

# Title

x402: challenge advertises wrong EIP-712 domain name ('Circle USDC') — no client can settle

# Body

Found while live-validating the agent-side x402 client (resonate-agentic #9, PR #36) against the staging deployment.

## Symptom

Every spec-compliant x402 payment is rejected at verification. `GET /api/stems/{id}/x402?licenseType=personal` (staging) returns a V2 challenge whose EVM `exact` requirements carry:

```json
"extra": {"name": "Circle USDC", "version": "2", ...}
```

`extra.name` / `extra.version` define the **EIP-712 domain** clients must sign EIP-3009 `TransferWithAuthorization` against. The actual Circle USDC contract on Base Sepolia (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`) has:

```
name() = "USDC"   (verified via eth_call on Base Sepolia)
```

## Evidence (both signing choices fail)

- Sign with the challenge's domain (`Circle USDC`) → `402 {"error":"Payment verification failed","message":"invalid_exact_evm_token_name_mismatch"}`
- Sign with the token's true domain (`USDC`) → `402 {"error":"Payment verification failed","message":"invalid_exact_evm_signature"}` (the verifier reconstructs using the challenge's own `extra.name`)

So the challenge is self-inconsistent: verification requires `extra.name` to equal the token's on-chain name, but the middleware emits a display label instead. **No client can settle.**

## Fix

In the x402 middleware/challenge config, set `extra.name` to the token's EIP-712 domain name — `"USDC"` for Circle USDC on Base Sepolia (keep `version: "2"`). "Circle USDC" belongs in a display field, not in `extra.name`.

Client side is ready to re-verify immediately: the agent repo has a gated live settlement test (`tests/test_x402_live.py`) that proves one 0.05-USDC purchase as soon as this lands.
