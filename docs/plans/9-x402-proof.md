# Issue #9 (BL-03) — x402 proof generation / real purchase · implementation plan

**Issue:** https://github.com/akoita/resonate-agentic/issues/9 · **ADR:** ADR-0001 · **Status:** implemented (PR #36) — client + offline proof landed; live settlement gated on the owner-run test

## Goal
Turn the 402 challenge into a real **discover → quote → pay → receipt**: the agent supplies a valid
x402 payment proof to `stem.download` / `GET /api/stems/{id}/x402` and receives the stem + receipt.

## Findings that change the original approach (investigated 2026-06-17)

The original idea ("pay via the agentcash MCP") does **not** work here:

- **agentcash holds real money, not testnet.** Balances: **Base mainnet $3.54**, tempo $17.60,
  solana $0 — and **no Base Sepolia** account.
- **Network mismatch.** The Resonate staging endpoint settles on **Base Sepolia** (`eip155:84532`,
  Circle USDC `0x036cbd…`, facilitator `x402.org`). agentcash can only pay Base **mainnet** — so it
  cannot pay staging, and attempting it would risk real funds.
- **Not a runtime mechanism.** agentcash's wallet is session-local (`~/.agentcash/wallet.json`) — a
  tool for the coding agent, not something the **deployed** Resonate agent can reach.

Conclusion: agentcash is unsuitable both for the testnet validation **and** for runtime payment.

## Decision / design (revised)

The agent needs its **own x402 client** bound to the endpoint's network:

- **Payment client:** an in-app x402 "exact"-scheme signer (e.g. the `x402` Python SDK / Coinbase
  x402 client) that, on a 402, builds and signs `PAYMENT-SIGNATURE` from a wallet key and retries.
- **Wallet/key by environment:** a **Base Sepolia testnet** EOA for dev/staging (key via env in dev,
  Secret Manager for deployed staging); a real wallet via **Cloud KMS** for prod (control-plane repo,
  ADR-0005). The key **never** lands in the public app repo.
- **Flow:** `stem.quote` → `stem_purchase` tool builds proof via the x402 client → `stem.download` /
  `…/x402` with the proof → receipt headers (`X-Resonate-Receipt[-Id]`, `X-Resonate-License`).
- **Guardrail:** the budget `before_tool_callback` (#10) MUST gate spend before any payment fires.

## Decisions resolved (2026-07-02)

1. ✅ **Testnet wallet** — a throwaway Base-Sepolia EOA was created and faucet-funded
   (key outside the repo, injected via `RESONATE_X402_TESTNET_KEY` / `X402_PRIVATE_KEY`).
2. ✅ **x402 client choice** — the `x402` Python SDK (v2.14, x402 Foundation), V2 wire format
   (`PAYMENT-REQUIRED` header challenge → EIP-3009 signature → `PAYMENT-SIGNATURE` retry).
   Chosen over a hand-rolled signer per rule 1 (reuse); signing correctness is proven offline
   by EIP-712 recovery in `tests/test_x402_payment.py`.
3. Prod key management (Cloud KMS) — still deferred to deployment (control-plane repo).

## Scope when unblocked
- `app/tools/payments.py` x402 client + a `stem_purchase` tool using it.
- Unit tests with a **mocked** facilitator/challenge (offline).
- A **gated** live test (`RESONATE_X402_TESTNET_KEY` present) that does one real testnet settlement —
  **never in CI**, never with mainnet funds.

## Explicitly out / forbidden
- ❌ No spending of agentcash mainnet/tempo funds.
- ❌ No unvalidated signing code merged as if it works (avoid the 80% problem) — live-validate first.

## Validation

**Offline (proven, in CI):** mocked V2 paywall → the SDK signs → retry carries
`PAYMENT-SIGNATURE` → receipt; the EIP-712 signature is verified by recovery against the payer
address; foreign-network and over-cap challenges are never paid (`tests/test_x402_payment.py`).

**Live run (2026-07-02) — blocked by a backend bug, not the client:**
- The staging challenge advertises `extra.name: "Circle USDC"`, but the Circle USDC contract on
  Base Sepolia (`0x036CbD…dCF7e`) has `name() = "USDC"` (checked on-chain). `extra.name/version`
  is the EIP-712 domain for EIP-3009 signing, so the challenge is self-inconsistent:
  - signing with the challenge's domain → `invalid_exact_evm_token_name_mismatch`;
  - signing with the token's true domain → `invalid_exact_evm_signature` (verifier reconstructs
    from its own `extra.name`).
  **No spec-compliant client can settle** until the backend middleware sets `extra.name: "USDC"`.
- Fixed upstream: akoita/resonate#1309 → PR akoita/resonate#1310 (merged + deployed to staging
  2026-07-02).

**Live settlement PROVEN (2026-07-02, post-backend-fix):** the gated test
(`tests/test_x402_live.py`) ran the full discover → quote → pay → receipt against staging and
passed — one real **0.05-USDC** `stem.download` settlement on Base Sepolia via the exact scheme
(EIP-3009, gasless for the payer). On-chain evidence: payer EOA balance moved 20.00 → 19.95 USDC.
This issue's goal is met; #37 leaves draft.
