# Implementation plans

One plan per non-trivial issue/feature — the **orchestrator-mode** artifact: write the plan, get it
reviewed, *then* delegate or implement. This is the improved version of `resonate`'s
`issue-*-implementation-plan.md` (here: a dedicated subdir + a template + a two-way link to the issue).

## When to write one

- Multi-file or multi-step work, an `agent-task` issue, or anything touching a hard rule / ADR.
- Skip it for trivial one-liners (a PR description is enough).

## How

1. Copy [`_TEMPLATE.md`](_TEMPLATE.md) → `plans/<issue-number>-<slug>.md` (e.g. `7-mcp-toolset.md`).
2. Fill it in; link it from the GitHub issue (and link the issue from the plan).
3. Implement against the plan's **acceptance/evals**. Update the plan if the approach changes.
4. The PR that closes the issue references the plan.

Plans are living until the issue closes, then they stand as the record of *why* it was built that way
(complementing the ADR, which records the *decision*).
