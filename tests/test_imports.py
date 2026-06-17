"""Test suite to verify that all modules, agents, and workflows import correctly."""

def test_imports():
    from app.config import config
    from app.schemas import LicenseType, TrackInfo
    from app.tools import catalog_search, stem_purchase
    from app.agents import catalog_agent, dj_agent, commerce_agent, artist_agent, community_agent
    from app.workflows import discovery_purchase_workflow, artist_upload_workflow, dj_session_workflow
    from app.agent import root_agent

    assert config.model_name is not None
    assert catalog_agent.name == "catalog_agent"
    assert dj_agent.name == "dj_agent"
    assert commerce_agent.name == "commerce_agent"
    assert artist_agent.name == "artist_agent"
    assert community_agent.name == "community_agent"
    assert root_agent.name == "resonate"
    assert discovery_purchase_workflow.name == "discovery_purchase"
    assert artist_upload_workflow.name == "artist_upload"
    assert dj_session_workflow.name == "dj_session"
    assert callable(catalog_search) and callable(stem_purchase)
    assert LicenseType.personal.value == "personal"
    assert TrackInfo.__name__ == "TrackInfo"
