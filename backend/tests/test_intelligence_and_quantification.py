import pytest
from backend.app.models.schemas import ServiceVertical, OpportunityArea
from backend.app.intelligence.pii_redactor import pii_redactor
from backend.app.intelligence.hinglish_engine import hinglish_engine
from backend.app.intelligence.aspect_classifier import aspect_classifier
from backend.app.intelligence.causal_extractor import causal_extractor
from backend.app.intelligence.quantification import quantification_engine
from backend.app.db.database import db

def test_pii_redactor():
    sample = "Call me at +91 9876543210 or email test.user@gmail.com. Technician Ramesh Sharma arrived late."
    sanitized, redactions = pii_redactor.redact(sample)
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "Ramesh Sharma" not in sanitized
    assert "PHONE" in redactions
    assert "EMAIL" in redactions
    assert "NAME" in redactions

def test_hinglish_engine():
    sample = "AC cooling nahi ho rahi thi, technician bola gas leak hai aur paise mang raha tha."
    normalized, is_hinglish, terms = hinglish_engine.normalize(sample)
    assert is_hinglish is True
    assert "not cooling properly" in normalized or "demanded extra money" in normalized
    assert len(terms) > 0

def test_aspect_classifier():
    sample = "Technician arrived 1 hour late and cancelled my washing machine repair. Never using UC again, switching to local vendor."
    vertical = aspect_classifier.classify_vertical(sample)
    aspects = aspect_classifier.classify_aspects(sample)
    churn_flag, sentiment = aspect_classifier.evaluate_churn_intent(sample, rating=1.0)

    assert vertical == ServiceVertical.APPLIANCE_REPAIR
    assert "Punctuality & Reliability" in aspects
    assert churn_flag is True
    assert sentiment < 0.0

def test_causal_extractor():
    sample = "Technician demanded 3000 cash for AC gas without app bill."
    chain = causal_extractor.extract_causal_chain(
        text=sample,
        vertical=ServiceVertical.APPLIANCE_REPAIR,
        aspects=["Pricing & Transparency"]
    )
    assert chain is not None
    assert "gas recharge" in chain.friction_trigger.lower() or "pricing" in chain.friction_trigger.lower()
    assert "churn" in chain.metric_impact.lower() or "repeat" in chain.metric_impact.lower()

def test_quantification_and_simulation():
    opps = db.get_opportunities()
    assert len(opps) > 0
    test_opp = opps[0]

    # Test What-If Simulation at 40% friction reduction
    sim_result = quantification_engine.simulate_friction_reduction(
        opp=test_opp,
        friction_reduction_pct=40.0
    )
    assert sim_result.opportunity_id == test_opp.id
    assert sim_result.friction_reduction_percentage == 40.0
    assert "+" in sim_result.projected_nps_delta
    assert "+" in sim_result.projected_repeat_rate_uplift
    assert "₹" in sim_result.recovered_annual_revenue
    print(f"\n[Simulation Passed for {test_opp.id}]:", sim_result.model_dump())

