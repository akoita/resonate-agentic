"""Shared test fixtures."""

from __future__ import annotations

import pytest

import app.tools.payments as payments
from app.config import ResonateConfig


@pytest.fixture(autouse=True)
def _x402_disabled_by_default(monkeypatch):
    """Keep tests hermetic: a developer's exported X402_PRIVATE_KEY must not
    flip ``stem_purchase`` into auto-pay mode outside the explicit x402 tests
    (which override ``payments.config`` with their own fixture)."""
    monkeypatch.delenv("X402_PRIVATE_KEY", raising=False)
    monkeypatch.setattr(payments, "config", ResonateConfig())
