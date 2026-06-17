<!-- Keep PRs small and agent-sized (one BACKLOG item where possible). -->

## What & why

<!-- One paragraph. Link the backlog item / ADR. -->
Closes: <!-- BL-?? / #issue -->
ADR: <!-- docs/adr/ADR-00xx-… if this is a decision -->

## Checklist

- [ ] `make check` passes (lint + tests + guardrails)
- [ ] Behavior change → test/eval added or updated
- [ ] New decision → ADR added under `docs/adr/`
- [ ] No new AGENTS.md hard-rule violation

## AI-generated-code review (per SECURITY.md)

- [ ] **Dependencies** are real and intended (no hallucinated imports)
- [ ] **Error handling** covers network/tool failure paths
- [ ] **No secrets / tokens / deployment hostnames** added
- [ ] **Stubs self-flag** `"stub": True`
- [ ] **Scope** stays on the public contract unless auth is explicitly designed
