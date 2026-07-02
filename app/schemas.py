"""Pydantic domain models for Resonate Agentic.

These schemas define the typed interfaces between agents, tools,
and the Resonate backend API. They mirror the Prisma data model
from the original Resonate platform.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.config import PRICE_COMMERCIAL_USD, PRICE_PERSONAL_USD, PRICE_REMIX_USD

# The live backend exposes 7 stem types per track: 6 AI-separated
# (Demucs htdemucs_6s) plus the original mix (verified in ADR-0001).
STEM_TYPES: tuple[str, ...] = (
    "vocals",
    "drums",
    "bass",
    "guitar",
    "piano",
    "other",
    "original",
)


# ─── Enums ───────────────────────────────────────────────────────────


class LicenseType(str, Enum):
    """Stem license tiers matching the on-chain contract."""

    personal = "personal"
    remix = "remix"
    commercial = "commercial"
    sync = "sync"
    sample = "sample"
    broadcast = "broadcast"


class SessionAction(str, Enum):
    """AI DJ session lifecycle actions."""

    start = "start"
    stop = "stop"
    pause = "pause"
    resume = "resume"


class PlaybackAction(str, Enum):
    """Playback control actions."""

    play = "play"
    pause = "pause"
    skip = "skip"
    queue = "queue"


class RoomAction(str, Enum):
    """Community room management actions."""

    create = "create"
    join = "join"
    leave = "leave"
    list_rooms = "list"


class CampaignAction(str, Enum):
    """Shows campaign lifecycle actions."""

    create = "create"
    pledge = "pledge"
    activate = "activate"
    cancel = "cancel"
    view = "view"


# ─── Core Domain Models ─────────────────────────────────────────────


class ArtistInfo(BaseModel):
    """Artist profile summary."""

    id: str
    display_name: str
    payout_address: Optional[str] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None


class ReleaseInfo(BaseModel):
    """Music release metadata."""

    id: str
    title: str
    artist_id: str
    artist_name: Optional[str] = None
    genre: Optional[str] = None
    moods: list[str] = Field(default_factory=list)
    release_date: Optional[datetime] = None
    artwork_url: Optional[str] = None
    track_count: int = 0
    explicit: bool = False
    status: str = "published"


class StemInfo(BaseModel):
    """Individual stem asset details."""

    id: str
    track_id: str
    stem_type: str = Field(description=f"One of: {', '.join(STEM_TYPES)}")
    title: Optional[str] = None
    artist: Optional[str] = None
    duration_seconds: Optional[float] = None
    is_encrypted: bool = False
    artwork_url: Optional[str] = None


class TrackInfo(BaseModel):
    """Track with its stems and metadata."""

    id: str
    title: str
    artist: Optional[str] = None
    release_id: str
    position: int = 1
    explicit: bool = False
    stems: list[StemInfo] = Field(default_factory=list)
    genre: Optional[str] = None
    moods: list[str] = Field(default_factory=list)


# ─── Pricing & Commerce ─────────────────────────────────────────────


class StemPricing(BaseModel):
    """Pricing tiers for a stem."""

    stem_id: str
    base_play_price_usd: float = PRICE_PERSONAL_USD
    remix_license_usd: float = PRICE_REMIX_USD
    commercial_license_usd: float = PRICE_COMMERCIAL_USD
    floor_usd: float = 0.01
    ceiling_usd: float = 50.0


class StemQuote(BaseModel):
    """Quote for purchasing a stem via x402."""

    stem_id: str
    license_type: LicenseType
    price_usdc: float
    price_summary: str
    expires_at: Optional[datetime] = None
    payment_challenge: Optional[dict[str, Any]] = None
    rights: Optional[dict[str, Any]] = None
    available_actions: list[str] = Field(default_factory=list)


class PurchaseReceipt(BaseModel):
    """Receipt from a successful stem purchase."""

    receipt_id: str
    stem_id: str
    license_type: LicenseType
    price_usd: float
    settlement_amount: Optional[str] = None
    settlement_asset: str = "USDC"
    payment_rail: str = "x402"
    status: str = "confirmed"
    receipt_data: Optional[dict[str, Any]] = None


class ListingInfo(BaseModel):
    """Marketplace listing details."""

    id: str
    listing_id: int
    stem_id: str
    token_id: int
    seller_address: str
    price_per_unit: str
    payment_token: str
    license_type: LicenseType = LicenseType.personal
    status: str = "active"
    expires_at: Optional[datetime] = None


class BudgetStatus(BaseModel):
    """Agent wallet budget status."""

    user_id: str
    wallet_address: Optional[str] = None
    balance_usd: float = 0.0
    monthly_cap_usd: float = 50.0
    spent_usd: float = 0.0
    remaining_usd: float = 50.0
    can_purchase: bool = True


# ─── AI DJ & Recommendations ────────────────────────────────────────


class TasteProfile(BaseModel):
    """Listener taste analysis results."""

    user_id: str
    preferred_genres: list[str] = Field(default_factory=list)
    preferred_moods: list[str] = Field(default_factory=list)
    energy_preference: Optional[str] = None
    top_artists: list[str] = Field(default_factory=list)
    listen_history_count: int = 0
    taste_signals: list[dict[str, Any]] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    """AI DJ recommendation output."""

    status: str = Field(description="ok, no_tracks, all_rejected, session_inactive")
    track: Optional[TrackInfo] = None
    license_type: Optional[LicenseType] = None
    price_usd: Optional[float] = None
    runtime_status: str = "approved"
    score: Optional[int] = None
    explanation: list[str] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)


class SessionInfo(BaseModel):
    """AI DJ session state."""

    session_id: str
    user_id: str
    status: str = "active"
    tracks_played: int = 0
    total_spend_usd: float = 0.0
    preferences: Optional[dict[str, Any]] = None


# ─── Artist ─────────────────────────────────────────────────────────


class UploadResult(BaseModel):
    """Result of an artist release upload."""

    release_id: str
    title: str
    status: str = "processing"
    track_count: int = 0
    stems_processing: bool = True
    rights_route: Optional[str] = None


class MintResult(BaseModel):
    """Result of minting a stem as an NFT."""

    stem_id: str
    token_id: int
    chain_id: int
    contract_address: str
    transaction_hash: str
    royalty_bps: int = 500
    remixable: bool = True


class ArtistAnalytics(BaseModel):
    """Artist analytics summary."""

    artist_id: str
    total_plays: int = 0
    total_revenue_usd: float = 0.0
    total_stems_sold: int = 0
    top_tracks: list[dict[str, Any]] = Field(default_factory=list)
    revenue_by_period: list[dict[str, Any]] = Field(default_factory=list)


# ─── Community ──────────────────────────────────────────────────────


class RoomInfo(BaseModel):
    """Community room details."""

    id: str
    room_type: str
    title: str
    description: Optional[str] = None
    artist_id: Optional[str] = None
    member_count: int = 0
    status: str = "active"


class CohortInfo(BaseModel):
    """Taste cohort suggestion."""

    id: str
    cohort_type: str
    title: str
    safe_explanation: str
    member_count: int = 0
    status: str = "suggested"


class CampaignInfo(BaseModel):
    """Shows campaign details."""

    id: str
    title: str
    artist_id: str
    city: Optional[str] = None
    status: str = "draft"
    funding_goal_usd: Optional[float] = None
    current_funding_usd: float = 0.0
    backer_count: int = 0


# ─── Workflow I/O Schemas ────────────────────────────────────────────


class DiscoveryPurchaseInput(BaseModel):
    """Input for the discovery-to-purchase workflow."""

    query: str = Field(description="Search query or natural language description")
    license_type: LicenseType = LicenseType.personal
    max_budget_usd: float = 10.0
    auto_purchase: bool = False


class DiscoveryPurchaseOutput(BaseModel):
    """Output from the discovery-to-purchase workflow."""

    stems_found: list[StemInfo] = Field(default_factory=list)
    selected_stem: Optional[StemInfo] = None
    quote: Optional[StemQuote] = None
    receipt: Optional[PurchaseReceipt] = None
    status: str = Field(description="found, quoted, purchased, no_results, budget_exceeded")
    message: str = ""


class ArtistUploadInput(BaseModel):
    """Input for the artist upload workflow."""

    title: str
    artist_name: str
    genre: Optional[str] = None
    moods: list[str] = Field(default_factory=list)
    audio_url: str = Field(description="URL or local path to the audio file")
    base_price_usd: float = PRICE_PERSONAL_USD
    remix_price_usd: float = PRICE_REMIX_USD
    commercial_price_usd: float = PRICE_COMMERCIAL_USD
    royalty_bps: int = 500
    auto_mint: bool = True


class ArtistUploadOutput(BaseModel):
    """Output from the artist upload workflow."""

    release: Optional[UploadResult] = None
    stems: list[StemInfo] = Field(default_factory=list)
    pricing_set: bool = False
    mint_results: list[MintResult] = Field(default_factory=list)
    status: str = Field(description="uploaded, processing, priced, minted, failed")
    message: str = ""


class DJSessionInput(BaseModel):
    """Input for the AI DJ session workflow."""

    user_id: str
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    energy: Optional[str] = None
    license_type: LicenseType = LicenseType.personal
    budget_usd: float = 10.0
    max_picks: int = 5


class DJSessionOutput(BaseModel):
    """Output from the AI DJ session workflow."""

    session_id: str
    picks: list[RecommendationResult] = Field(default_factory=list)
    total_spend_usd: float = 0.0
    tracks_played: int = 0
    status: str = "completed"
    message: str = ""
