"""Resonate Agentic configuration."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# Default license pricing tiers (USD) — the single source of truth for the
# defaults quoted in schemas, tools, and workflows. Artists override per stem.
PRICE_PERSONAL_USD = 0.05
PRICE_REMIX_USD = 5.0
PRICE_COMMERCIAL_USD = 25.0


@dataclass(frozen=True)
class ResonateConfig:
    """Central configuration for the Resonate agentic platform."""

    # Resonate backend
    api_base: str = field(
        default_factory=lambda: os.getenv("RESONATE_API_BASE", "http://localhost:3000")
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("RESONATE_API_KEY", "")
    )

    # Google AI
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )
    model_name: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL", "gemini-2.5-flash")
    )

    # x402 payment config
    x402_network: str = field(
        default_factory=lambda: os.getenv("X402_NETWORK", "eip155:84532")
    )
    x402_facilitator_url: str = field(
        default_factory=lambda: os.getenv(
            "X402_FACILITATOR_URL", "https://x402.org/facilitator"
        )
    )
    # Payer wallet key (hex). Testnet key via env in dev/staging; managed
    # secret in deployed envs (ADR-0005). Empty = payments disabled.
    x402_private_key: str = field(
        default_factory=lambda: os.getenv("X402_PRIVATE_KEY", "")
    )

    # Agent defaults
    default_budget_usd: float = field(
        default_factory=lambda: float(
            os.getenv("AGENT_DEFAULT_BUDGET_USD", "50.0")
        )
    )
    max_purchase_usd: float = field(
        default_factory=lambda: float(
            os.getenv("AGENT_MAX_PURCHASE_USD", "25.0")
        )
    )
    recommendation_strategy: str = field(
        default_factory=lambda: os.getenv(
            "AGENT_RECOMMENDATION_STRATEGY", "deterministic"
        )
    )

    @property
    def storefront_url(self) -> str:
        return f"{self.api_base}/api/storefront"

    @property
    def mcp_url(self) -> str:
        return f"{self.api_base}/mcp"


config = ResonateConfig()
