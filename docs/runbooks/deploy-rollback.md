# Runbook: roll back a bad agent deploy

**Applies to:** the agent deployed via the control plane ([`resonate-agentic-iac`](https://github.com/akoita/resonate-agentic-iac)).
**Principle:** Agent Runtime has **no revision rollback** — recovery is **git-based**: redeploy the
last-good app `release_sha`. (Cloud Run, the portable target, additionally supports traffic shifting.)

## 1. Confirm the regression
- Check Cloud Trace + logs / eval-monitor; confirm the bad behavior and the deploy that introduced it.
- Note the current (bad) `release_sha` and the last-known-good one.

## 2. Roll back (Agent Runtime)
- In `resonate-agentic-iac`, run the deploy workflow (`workflow_dispatch`) with the **last-good
  `release_sha`** for the affected environment. (See iac issue: deploy-specific-SHA workflow.)
- The CD checks out the app at that SHA and re-runs the source-based deploy.

## 3. Roll back (Cloud Run, portable target)
```bash
gcloud run revisions list --service=SERVICE --region=REGION
gcloud run services update-traffic SERVICE --to-revisions=GOOD_REVISION=100 --region=REGION
```

## 4. After
- Open an issue with the failing `release_sha`; if the eval gate missed it, add an eval that catches it
  (quality flywheel).
- If a decision changes, record an ADR.

> Prod deploys are manual-only; this runbook assumes operator access to the private control plane.
