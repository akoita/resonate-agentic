# Issue #9 (BL-03) — x402 proof generation / real purchase · implementation plan

**Issue:** https://github.com/akoita/resonate-agentic/issues/9 · **ADR:** ADR-0001 · **Status:** blocked (needs a funded Base-Sepolia testnet wallet + a decision)

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

## Blocked on (decisions for the owner)

1. **A funded Base-Sepolia testnet wallet** (private key) to validate a real ~0.05-USDC purchase.
   (Get test USDC from a Base Sepolia faucet → an EOA we control.)
2. **x402 client choice** — confirm the Python lib (`x402` SDK vs hand-rolled EIP-712 signer).
3. Prod key management (Cloud KMS) — deferred to deployment (control-plane repo).

## Scope when unblocked
- `app/tools/payments.py` x402 client + a `stem_purchase` tool using it.
- Unit tests with a **mocked** facilitator/challenge (offline).
- A **gated** live test (`RESONATE_X402_TESTNET_KEY` present) that does one real testnet settlement —
  **never in CI**, never with mainnet funds.

## Explicitly out / forbidden
- ❌ No spending of agentcash mainnet/tempo funds.
- ❌ No unvalidated signing code merged as if it works (avoid the 80% problem) — live-validate first.

## Validation
- Pending a testnet wallet. Until then: design only; no settlement performed.
