#!/usr/bin/env python3
"""Deterministic harness guardrails for Resonate Agentic.

These encode the hard rules from AGENTS.md as code so they cannot silently
regress. Run by `make check`, pre-commit, and CI. Exit non-zero on violation.

Each check maps to an AGENTS.md rule / ADR:
  1. async-only tools           — no event-loop anti-pattern in app/   (rule 2)
  2. portability                — no GCP-only imports in app/          (rule 3, ADR-0003)
  3. no leaked deployment host  — no private staging hostname anywhere (rule 5)
  4. no hardcoded secrets       — no long literals on secret-named vars (rule 5)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [ROOT / p for p in out]


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return ""


def check_async_tools(files: list[Path]) -> list[str]:
    bad = []
    # match real calls, not prose/docstrings that name the anti-pattern
    pat = re.compile(r"\.run_until_complete\(|get_event_loop\(|asyncio\.run\(")
    for f in files:
        if f.suffix == ".py" and "app/tools/" in f.as_posix():
            for i, line in enumerate(read(f).splitlines(), 1):
                if pat.search(line):
                    bad.append(f"{f.relative_to(ROOT)}:{i}: event-loop anti-pattern in a tool (rule 2)")
    return bad


def check_portability(files: list[Path]) -> list[str]:
    bad = []
    pat = re.compile(r"^\s*(?:import|from)\s+(vertexai|google\.cloud)\b")
    for f in files:
        posix = f.as_posix()
        in_app = posix.startswith("app/") or "/app/" in posix
        if f.suffix == ".py" and in_app:
            for i, line in enumerate(read(f).splitlines(), 1):
                if pat.search(line):
                    bad.append(f"{f.relative_to(ROOT)}:{i}: GCP-only import in app/ (rule 3, ADR-0003)")
    return bad


def check_no_host(files: list[Path]) -> list[str]:
    bad = []
    pat = re.compile(r"pydes\.xyz")
    for f in files:
        if f.name == "harness_guardrails.py":
            continue  # this file names the pattern intentionally
        for i, line in enumerate(read(f).splitlines(), 1):
            if pat.search(line):
                bad.append(f"{f.relative_to(ROOT)}:{i}: leaked private deployment host (rule 5)")
    return bad


def check_no_secrets(files: list[Path]) -> list[str]:
    bad = []
    # secret-named var assigned a long literal, ignoring env/placeholder contexts
    pat = re.compile(
        r"""(?i)\b(secret|token|passwd|password|api[_-]?key|private[_-]?key)\b\s*[:=]\s*["'][A-Za-z0-9_\-/+]{16,}["']"""
    )
    allow = re.compile(r"getenv|environ|os\.environ|Field\(|description=|example|your-|<|\$\{|placeholder")
    skip_names = {"poetry.lock", "LICENSE", ".env.example"}
    for f in files:
        if f.name in skip_names or f.name == "harness_guardrails.py":
            continue
        if f.suffix not in {".py", ".md", ".toml", ".yaml", ".yml", ".env", ".json", ".sh"}:
            continue
        for i, line in enumerate(read(f).splitlines(), 1):
            if pat.search(line) and not allow.search(line):
                bad.append(f"{f.relative_to(ROOT)}:{i}: possible hardcoded secret (rule 5)")
    return bad


CHECKS = {
    "async-only tools": check_async_tools,
    "portability (no GCP-only imports in app/)": check_portability,
    "no leaked deployment host": check_no_host,
    "no hardcoded secrets": check_no_secrets,
}


def main() -> int:
    files = tracked_files()
    violations: list[str] = []
    for name, fn in CHECKS.items():
        found = fn(files)
        status = "FAIL" if found else "ok"
        print(f"[{status}] {name}")
        violations.extend(found)
    if violations:
        print("\nHarness guardrail violations:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print("\nSee AGENTS.md for the rule. Fix the harness, not just the symptom.", file=sys.stderr)
        return 1
    print("\nAll harness guardrails passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
