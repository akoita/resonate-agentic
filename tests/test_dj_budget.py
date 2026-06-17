"""Offline tests for the DJ's agent-side compute (ADR-0002).

The DJ workflow's intelligence nodes are LLMs (need credentials), but the
budget/loop control and candidate normalization are pure compute — testable
offline. These prove budget is enforced agent-side without any backend call.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.workflows.dj_session import _compact_candidates, advance


def _ctx(**state) -> SimpleNamespace:
    """Minimal stand-in for ADK Context: only `.state` is used by advance()."""
    return SimpleNamespace(state=state)


def test_compact_candidates_normalizes_storefront_items():
    raw = {
        "results": {
            "items": [
                {"id": "s1", "title": "T", "artist": "A", "stemType": "bass",
                 "price": {"usd": 0.05}},
                {"id": "s2", "title": "U", "artist": "B", "stemType": "vocals"},  # no price
                "not-a-dict",
            ]
        }
    }
    out = _compact_candidates(raw)
    assert [c["stem_id"] for c in out] == ["s1", "s2"]
    assert out[0]["price_usd"] == 0.05
    assert out[1]["price_usd"] == 0.0


def _route(event) -> str:
    return event.actions.route


def _delta(event) -> dict:
    return event.actions.state_delta


def test_advance_continues_and_records_under_budget():
    ctx = _ctx(
        current_pick={"stem_id": "s1", "price_usd": 0.05, "should_continue": True},
        picks_count=0, max_picks=5, budget_usd=10.0, total_spend=0.0,
        played_stem_ids=[], picks=[],
    )
    ev = advance(ctx, None)
    assert _route(ev) == "continue"
    d = _delta(ev)
    assert d["played_stem_ids"] == ["s1"]
    assert d["picks_count"] == 1
    assert abs(d["total_spend"] - 0.05) < 1e-9


def test_advance_exits_when_budget_would_be_exceeded():
    ctx = _ctx(
        current_pick={"stem_id": "s9", "price_usd": 5.0, "should_continue": True},
        picks_count=1, max_picks=5, budget_usd=4.0, total_spend=2.0,  # 2+5 > 4
        played_stem_ids=["s0"], picks=[{}],
    )
    ev = advance(ctx, None)
    assert _route(ev) == "exit"
    assert ev.output["recorded"] is False


def test_advance_exits_when_max_picks_reached():
    ctx = _ctx(
        current_pick={"stem_id": "s5", "price_usd": 0.05, "should_continue": True},
        picks_count=4, max_picks=5, budget_usd=10.0, total_spend=0.2,
        played_stem_ids=["a", "b", "c", "d"], picks=[{}, {}, {}, {}],
    )
    ev = advance(ctx, None)  # records the 5th, then exits (5 == max)
    assert _route(ev) == "exit"
    assert _delta(ev)["picks_count"] == 5


def test_advance_exits_when_llm_stops():
    ctx = _ctx(
        current_pick={"stem_id": "s5", "price_usd": 0.05, "should_continue": False},
        picks_count=1, max_picks=5, budget_usd=10.0, total_spend=0.05,
        played_stem_ids=["a"], picks=[{}],
    )
    ev = advance(ctx, None)
    assert _route(ev) == "exit"
