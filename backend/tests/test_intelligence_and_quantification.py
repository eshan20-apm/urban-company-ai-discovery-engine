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

def test_query_decomposer_retention_and_cohort():
    from backend.app.intelligence.query_decomposer import query_decomposer
    res = query_decomposer.decompose_query("what urban company customers are doing within 90days after the last booking?")
    assert res.time_horizon == "90_day"
    assert "90-DAY" in res.interpreted_intent or "90-Day" in res.interpreted_intent or "Retention" in res.interpreted_intent
    assert res.core_topic == "retention_and_repeat_behavior"
    assert len(res.search_vectors) >= 2
    assert "repeat" in res.semantic_keywords or "retention" in res.semantic_keywords

def test_query_decomposer_repeat_booking_without_cohort():
    from backend.app.intelligence.query_decomposer import query_decomposer
    # Test query WITHOUT 90 days - must not contain '90' in intent or title
    res = query_decomposer.decompose_query("what is the repeat booking behaviour of the customers?")
    assert res.time_horizon is None
    assert "90" not in res.interpreted_intent
    assert "Repeat Booking" in res.interpreted_intent
    assert res.core_topic == "retention_and_repeat_behavior"

def test_query_decomposer_pricing_and_vague_queries():
    from backend.app.intelligence.query_decomposer import query_decomposer
    # Doorstep cash / extra charge
    res_price = query_decomposer.decompose_query("technicians taking extra money")
    assert res_price.core_topic == "pricing_transparency"
    assert "Pricing" in res_price.interpreted_intent or "Cash" in res_price.interpreted_intent

    # Churn / App delete
    res_churn = query_decomposer.decompose_query("why do people stop using it and delete the app")
    assert res_churn.core_topic == "churn_and_defection"
    assert "Churn" in res_churn.interpreted_intent or "Defection" in res_churn.interpreted_intent

    # Delays & cancellations
    res_cancel = query_decomposer.decompose_query("partner cancelled slot at the last minute")
    assert res_cancel.core_topic == "punctuality_and_cancellation"

    # Generalized topic
    res_general = query_decomposer.decompose_query("salon hygiene and facial cleanup")
    assert ServiceVertical.SALON_SPA.value in res_general.target_verticals


