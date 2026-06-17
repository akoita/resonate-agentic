# Security Policy

This is an experimental project, but it handles **payments (x402/USDC)** and talks to a real
backend, so we take security seriously — with extra attention to the failure modes of
**AI-generated code**.

## Reporting a vulnerability

Please report privately — do **not** open a public issue for security problems.

- Use [GitHub Security Advisories](https://github.com/akoita/resonate-agentic/security/advisories/new), or
- email the maintainer (see the GitHub profile for `akoita`).

Include reproduction steps, impact, and affected versions/commits. We aim to acknowledge within a
few days.

## Scope & threat model

- **Payments:** the agent constructs/forwards x402 proofs. Spending must be bounded by an
  agent-side budget guardrail (BL-04); never auto-purchase without an explicit budget check.
- **Secrets:** none in the repo. Config via env; `.env` is git-ignored; deployment hostnames are
  redacted in favor of `$RESONATE_API_BASE`. Enforced by `scripts/harness_guardrails.py` + CI.
- **Backend auth:** JWT-gated endpoints are out of the public agent contract; do not hardcode or
  embed tokens (see [ADR-0002](docs/adr/ADR-0002-feature-scope-compute-vs-data.md)).
- **Supply chain:** dependencies are pinned (`requirements.txt`); CI runs a dependency audit and
  Dependabot proposes updates.

## AI-generated-code review focus

Per the project's review checklist, reviewers (human and the AI first-pass) specifically check for:

- **Hallucinated dependencies** — every imported package must exist and be intended.
- **Inadequate error handling** — network/tool calls must handle failure paths.
- **Silent partial features** — stubs must self-flag `"stub": True`.
- **Secret/PII leakage** — no secrets, tokens, wallet data, or private hosts in code or logs.
- **Over-broad capability** — tools scoped to the public contract unless auth is explicitly designed.

## Automated controls

- `make guardrails` / CI: secret patterns, leaked-host, portability, async-tool rules.
- `ruff --select S` (bandit-style) in the security workflow.
- Dependency audit (`pip-audit`) — informational, reviewed each release.
