import pytest
from backend.app.db.database import db
from backend.app.models.schemas import FeedbackSource, ServiceVertical

def test_database_tables():
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "feedback_items" in tables
        assert "opportunity_areas" in tables
        assert "investor_claims" in tables
        assert "simulation_logs" in tables

def test_feedback_items_retrieval():
    items = db.get_feedback_items(limit=50)
    assert len(items) > 0
    for item in items:
        assert item.id is not None
        assert item.source in list(FeedbackSource)
        assert item.service_vertical in list(ServiceVertical)
        assert len(item.text_raw) > 0

def test_opportunity_areas_retrieval():
    opps = db.get_opportunities()
    assert len(opps) >= 5
    for opp in opps:
        assert opp.id.startswith("OPP-")
        assert opp.rice_score > 0
        assert opp.reach_percentage > 0
        assert len(opp.causal_chains) > 0
        assert opp.suggested_action is not None

def test_executive_metrics():
    metrics = db.get_executive_metrics()
    assert metrics.total_feedback_items > 0
    assert -100.0 <= metrics.nps_proxy <= 100.0
    assert 0.0 <= metrics.high_risk_churn_rate <= 100.0
    assert metrics.active_opportunity_count >= 5
    assert len(metrics.source_distribution) > 0
    print("\n[Verification Passed] Executive Metrics:", metrics.model_dump())

