import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_dashboard_serving():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Urban Company" in resp.text
    assert "AI Discovery Engine" in resp.text

    resp2 = client.get("/dashboard")
    assert resp2.status_code == 200
    assert "Urban Company" in resp2.text

def test_executive_metrics_endpoint():
    resp = client.get("/api/v1/metrics/executive")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_feedback_items"] > 0
    assert "nps_proxy" in data
    assert "high_risk_churn_rate" in data

def test_opportunities_endpoint():
    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    opps = resp.json()
    assert len(opps) >= 5
    assert opps[0]["id"] == "OPP-01"
    assert opps[0]["rice_score"] > 0

def test_opportunity_dossier_endpoint():
    resp = client.get("/api/v1/opportunities/OPP-01/dossier")
    assert resp.status_code == 200
    dossier = resp.json()
    assert dossier["id"] == "OPP-01"
    assert len(dossier["causal_chains"]) > 0
    assert "suggested_action" in dossier

def test_simulate_endpoint():
    payload = {
        "opportunity_id": "OPP-01",
        "friction_reduction_percentage": 50.0
    }
    resp = client.post("/api/v1/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunity_id"] == "OPP-01"
    assert data["friction_reduction_percentage"] == 50.0
    assert "+" in data["projected_nps_delta"]
    assert "+" in data["projected_repeat_rate_uplift"]

def test_strategy_gap_endpoint():
    resp = client.get("/api/v1/strategy-gap")
    assert resp.status_code == 200
    claims = resp.json()
    assert len(claims) >= 4
    for claim in claims:
        assert claim["ground_truth_verdict"] in ["CONFIRMED", "DIVERGENT", "CRITICAL_RISK"]

def test_feed_endpoint():
    resp = client.get("/api/v1/feed?limit=10")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) <= 10
    assert len(items) > 0

def test_copilot_chat_endpoint():
    resp = client.post("/api/v1/copilot/chat", json={"query": "Why are AC repair cancellations high in Bangalore?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "OPP-01" in data["answer"] or "OPP-02" in data["answer"] or len(data["key_findings"]) > 0
    assert len(data["citations"]) > 0

def test_discovery_search_endpoints():
    # Test example 1: What do customers expect once a booking is complete?
    resp1 = client.get("/api/v1/discovery/search?q=What%20do%20customers%20expect%20once%20a%20booking%20is%20complete?")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "Discovery" in data1["title"]
    assert "interpreted_intent" in data1
    assert "decomposition" in data1
    assert "key_findings" in data1
    assert "business_metric_impact" in data1
    assert len(data1["key_findings"]) > 0
    assert data1["key_findings"][0]["tag_type"] == "ai_tagged"
    assert data1["key_findings"][0]["tag_label"] == "AI Tagged"
    assert len(data1["citations"]) > 0
    assert data1["citations"][0]["tag_type"] in ["golden_truth", "ai_tagged"]
    assert data1["citations"][0]["tag_label"] in ["Golden Truth", "AI Tagged"]

    # Test example 2: How do they decide that a home service is needed, and when?
    resp2 = client.get("/api/v1/discovery/search?q=How%20do%20they%20decide%20that%20a%20home%20service%20is%20needed,%20and%20when?")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "Discovery" in data2["title"]
    assert "key_findings" in data2
    assert "business_metric_impact" in data2

    # Test example 3: Natural conversational query with 90-days cohort retention
    resp3 = client.get("/api/v1/discovery/search?q=what%20urban%20company%20customers%20are%20doing%20within%2090days%20after%20the%20last%20booking?")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert "interpreted_intent" in data3
    assert "90-DAY" in data3["interpreted_intent"] or "90-Day" in data3["interpreted_intent"] or "Retention" in data3["interpreted_intent"]
    assert "decomposition" in data3
    assert data3["decomposition"]["time_horizon"] == "90_day"

    # Test example 4: Repeat booking query without cohort window (should NOT have 90)
    resp4 = client.get("/api/v1/discovery/search?q=what%20is%20the%20repeat%20booking%20behaviour%20of%20the%20customers?")
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert "interpreted_intent" in data4
    assert "90" not in data4["interpreted_intent"]
    assert "Repeat Booking" in data4["interpreted_intent"]
    assert data4["decomposition"]["time_horizon"] is None

    # Test example 5: Distinct queries return distinct citations (no rotation of identical top items)
    resp_ac = client.get("/api/v1/discovery/search?q=AC%20gas%20leak%20overcharging")
    resp_salon = client.get("/api/v1/discovery/search?q=Salon%20hygiene%20and%20cleanup")
    assert resp_ac.status_code == 200 and resp_salon.status_code == 200
    ac_texts = {c["full_text"] for c in resp_ac.json()["citations"]}
    salon_texts = {c["full_text"] for c in resp_salon.json()["citations"]}
    assert len(ac_texts) >= 2 and len(salon_texts) >= 2
    assert ac_texts != salon_texts
    # Citations within a response must be unique (no duplicate verbatim texts)
    ac_list = [c["full_text"] for c in resp_ac.json()["citations"]]
    assert len(ac_list) == len(set(ac_list))
    # Key findings should be aggregated patterns, not verbatim duplicates of citations
    ac_finding_titles = [f["title"] for f in resp_ac.json()["key_findings"]]
    assert len(ac_finding_titles) > 0
    assert any("mention" in t for t in ac_finding_titles)

def test_export_csv_endpoints():
    # 1. Export all feedback items
    resp_all = client.get("/api/v1/export/csv")
    assert resp_all.status_code == 200
    assert "text/csv" in resp_all.headers["content-type"]
    assert resp_all.content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM verification
    csv_text = resp_all.content.decode("utf-8-sig")
    assert "Feedback ID,Data Tag,Source Platform,Service Vertical" in csv_text
    assert "Play Store" in csv_text
    assert ("Golden Truth" in csv_text or "AI Tagged" in csv_text)

    # 2. Export search results with query
    resp_search = client.get("/api/v1/export/csv?q=booking")
    assert resp_search.status_code == 200
    assert "text/csv" in resp_search.headers["content-type"]
    assert resp_search.content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM verification
    search_csv_text = resp_search.content.decode("utf-8-sig")
    assert "Search Query,Interpreted Intent,Analysis Title,Executive Behavioral Takeaway,Item Type,Data Tag" in search_csv_text
    assert "booking" in search_csv_text
    assert ("Golden Truth" in search_csv_text or "AI Tagged" in search_csv_text)

