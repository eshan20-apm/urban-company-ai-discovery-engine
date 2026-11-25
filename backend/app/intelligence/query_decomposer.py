import re
import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.models.schemas import ServiceVertical

class QueryDecomposition(BaseModel):
    raw_query: str
    interpreted_intent: str
    core_topic: str
    time_horizon: Optional[str] = None
    target_verticals: List[str] = Field(default_factory=list)
    target_aspects: List[str] = Field(default_factory=list)
    search_vectors: List[str] = Field(default_factory=list)
    semantic_keywords: List[str] = Field(default_factory=list)
    is_vague: bool = False

class QueryDecomposer:
    """
    Intelligent Query Understanding & Decomposition Engine:
    Translates raw, colloquial, informal, or vague natural language queries
    into structured business intent, resolved temporal horizons, target operational aspects,
    and realistic human search vectors for live web scraping (Reddit, Play Store) and database matching.
    """

    def decompose_query(self, raw_query: str) -> QueryDecomposition:
        cleaned = raw_query.strip()

        # 1. Attempt LLM-assisted zero-shot decomposition if API key is provided
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10:
            try:
                llm_res = self._decompose_with_llm(cleaned)
                if llm_res:
                    return llm_res
            except Exception:
                pass  # Fall back to high-coverage domain taxonomy engine

        # 2. Deterministic Domain Taxonomy & Semantic Intent Matcher (Instant, robust, zero-downtime)
        return self._decompose_with_taxonomy(cleaned)

    def _decompose_with_taxonomy(self, raw_query: str) -> QueryDecomposition:
        query_lower = raw_query.lower()

        # A. Temporal / Cohort Horizon Detection (handles '90days', '90 days', '3 months', 'same day', etc.)
        time_horizon = None
        temporal_match = re.search(r'(\d+)\s*(days?|months?|weeks?|hours?)', query_lower)
        if temporal_match:
            qty, unit = temporal_match.group(1), temporal_match.group(2)
            time_horizon = f"{qty}_{unit.rstrip('s')}"
        elif "same day" in query_lower or "same-day" in query_lower:
            time_horizon = "same_day"
        elif any(f in query_lower for f in ["diwali", "festive", "festival", "summer", "monsoon"]):
            time_horizon = "seasonal_peak"

        # B. Service Vertical Detection
        verticals = []
        if any(w in query_lower for w in ["ac", "air conditioner", "fridge", "refrigerator", "washing machine", "ro", "water purifier", "geyser", "microwave"]):
            verticals.append(ServiceVertical.APPLIANCE_REPAIR.value)
        if any(w in query_lower for w in ["clean", "cleaning", "deep clean", "bathroom", "sofa", "kitchen"]):
            verticals.append(ServiceVertical.CLEANING.value)
        if any(w in query_lower for w in ["salon", "spa", "facial", "wax", "waxing", "haircut", "makeup", "massage", "pedicure"]):
            verticals.append(ServiceVertical.SALON_SPA.value)
        if any(w in query_lower for w in ["plumber", "plumbing", "pipe", "tap", "electrician", "wire", "carpenter", "drill"]):
            verticals.append(ServiceVertical.PLUMBING_CARPENTRY.value)
        if any(w in query_lower for w in ["paint", "painting", "waterproofing", "dampness"]):
            verticals.append(ServiceVertical.PAINTING.value)
        if not verticals:
            verticals.append(ServiceVertical.GENERAL.value)

        # C. Intent & Topic Pattern Matching
        # 1. Retention, 90-Day window, Repeat Booking, Offline Technician Leakage
        if any(p in query_lower for p in ["90", "90day", "repeat", "after booking", "next booking", "what customers are doing", "subsequent", "months after"]):
            interpreted_intent = "90-Day Cohort Retention, Repeat Booking Behavior & Offline Vendor Defection"
            core_topic = "retention_and_repeat_behavior"
            target_aspects = ["Pricing & Transparency", "App UX & UC Plus", "Customer Support & Refunds"]
            search_vectors = [
                "Urban Company technician contact directly whatsapp cash",
                "Urban company repeat booking service dropoff months",
                "Urban company warranty claim after booking"
            ]
            semantic_keywords = ["repeat", "retention", "whatsapp", "cash", "offline", "technician", "direct", "booking", "again", "churn", "warranty"]
            is_vague = False

        # 2. Explicit Churn / Defection / Stopping usage
        elif any(p in query_lower for p in ["stop using", "stopped using", "leave", "leaving", "uninstall", "delete app", "switch to local", "never book again"]):
            interpreted_intent = "Customer Churn Triggers, Platform Defection & Local Technician Switch"
            core_topic = "churn_and_defection"
            target_aspects = ["Pricing & Transparency", "Customer Support & Refunds", "Service Quality"]
            search_vectors = [
                "Urban company worst app uninstall delete account",
                "Urban company switching to local offline vendors",
                "Urban company unfair charges customer care no help"
            ]
            semantic_keywords = ["uninstall", "delete", "worst", "never", "again", "switch", "local", "scam", "charges", "churn", "stop"]
            is_vague = True if len(raw_query.split()) < 6 else False

        # 3. Doorstep Pricing & Cash/Overcharging
        elif any(p in query_lower for p in ["extra money", "taking extra", "overcharging", "hidden charge", "rate card", "asking cash", "cash payment", "bill mismatch"]):
            interpreted_intent = "Doorstep Pricing Transparency, Cash Surcharges & Spare Parts Disputes"
            core_topic = "pricing_transparency"
            target_aspects = ["Pricing & Transparency", "Partner Conduct & Safety"]
            search_vectors = [
                "Urban company technician asking cash extra money",
                "Urban company spare parts rate card bill overcharge",
                "Urban company visiting charge without parts"
            ]
            semantic_keywords = ["extra", "money", "cash", "charge", "overcharge", "parts", "bill", "hidden", "doorstep", "expensive"]
            is_vague = False

        # 4. Delays, Cancellations, No-shows
        elif any(p in query_lower for p in ["cancel", "cancelled", "delay", "reschedule", "didn't show", "not turn up", "late", "punctual"]):
            interpreted_intent = "Doorstep Arrival Reliability, Partner No-Shows & Cancellation Frictions"
            core_topic = "punctuality_and_cancellation"
            target_aspects = ["Punctuality & Reliability", "Customer Support & Refunds"]
            search_vectors = [
                "Urban company partner did not turn up cancelled",
                "Urban company appointment rescheduled delay emergency",
                "Urban company missed call policy cancellation fine"
            ]
            semantic_keywords = ["cancel", "cancelled", "delay", "reschedule", "waiting", "turn up", "arrive", "slot", "fine", "show"]
            is_vague = False

        # 5. Service Quality / Poor workmanship / Broken item
        elif any(p in query_lower for p in ["gas leak", "gas charging", "cooling issue", "compressor", "foam jet", "diagnostic", "poor work", "shoddy", "damaged", "broken", "not working after", "failed repair"]):
            interpreted_intent = "Appliance & Service Diagnostic Integrity, Workmanship & Repair Failure Risks"
            core_topic = "service_quality_and_damages"
            target_aspects = ["Service Quality", "Pricing & Transparency"]
            search_vectors = [
                "Urban company AC gas leak recharge scam charge",
                "Urban company repair failed not working damage",
                "Urban company technician broke laptop appliance"
            ]
            semantic_keywords = ["quality", "damaged", "broken", "failed", "gas", "leak", "cooling", "rework", "warranty", "shoddy"]
            is_vague = False

        # 6. Customer Decision Triggers / When service needed
        elif any(p in query_lower for p in ["decide", "decision", "when is needed", "trigger", "why do they call", "booking is complete", "expect once"]):
            interpreted_intent = "Customer Need Triggers, Pre-Booking Expectations & Trust Drivers"
            core_topic = "customer_decision_triggers"
            target_aspects = ["Service Quality", "Pricing & Transparency", "App UX & UC Plus"]
            search_vectors = [
                "Urban company expectations once booking complete confirmation",
                "Urban company how customers decide book home service",
                "Urban company routine cleaning festival emergency"
            ]
            semantic_keywords = ["decide", "need", "booking", "expect", "confirmation", "service", "trust", "routine", "emergency"]
            is_vague = False

        # 7. Customer Support, Refunds & Disputes
        elif any(p in query_lower for p in ["refund", "customer care", "helpdesk", "bot", "ticket", "dispute", "not satisfied with the serv"]):
            interpreted_intent = "Customer Support Bottlenecks, Automated Bot Frustration & Refund Delays"
            core_topic = "support_and_refunds"
            target_aspects = ["Customer Support & Refunds", "Pricing & Transparency"]
            search_vectors = [
                "Urban company refund not processed invalid ARN number",
                "Urban company chatbot loop support ticket closed without help",
                "Urban company consumer court dispute escalation"
            ]
            semantic_keywords = ["refund", "support", "help", "bot", "ticket", "escalation", "dissatisfied", "complain", "care"]
            is_vague = False

        # 8. Generalized Fallback for any other natural query
        else:
            clean_tokens = [w for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', query_lower) if w not in {"what", "how", "why", "when", "does", "the", "and", "for", "with", "urban", "company"}]
            topic_str = " ".join(clean_tokens[:3]).title() if clean_tokens else "Service Experience"
            interpreted_intent = f"Customer Perceptions & Feedback Analysis: {topic_str}"
            core_topic = "general_exploration"
            target_aspects = ["Service Quality", "Pricing & Transparency"]
            search_vectors = [
                f"Urban company {' '.join(clean_tokens[:3])}",
                f"Urban company customer reviews {' '.join(clean_tokens[:2])}"
            ]
            semantic_keywords = clean_tokens if clean_tokens else ["urban", "company", "service"]
            is_vague = True if len(clean_tokens) <= 2 else False

        return QueryDecomposition(
            raw_query=raw_query,
            interpreted_intent=interpreted_intent,
            core_topic=core_topic,
            time_horizon=time_horizon,
            target_verticals=verticals,
            target_aspects=target_aspects,
            search_vectors=search_vectors,
            semantic_keywords=semantic_keywords,
            is_vague=is_vague
        )

    def _decompose_with_llm(self, raw_query: str) -> Optional[QueryDecomposition]:
        """Optionally uses Gemini API to produce structured decomposition."""
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        
        prompt = f"""
You are the query understanding module for the Urban Company AI Discovery Engine.
Analyze the user's inquiry: "{raw_query}"
Decompose into a valid JSON object matching this schema:
{{
  "interpreted_intent": "Clear, professional title of what the user is asking regarding customer behavior or operational friction",
  "core_topic": "short_topic_slug",
  "time_horizon": "e.g. 90_days, same_day, or null",
  "target_verticals": ["Appliance Repair", "Home Cleaning", "Salon & Spa", "Plumber & Electrician", or "General / Platform"],
  "target_aspects": ["Pricing & Transparency", "Punctuality & Reliability", "Service Quality", "Partner Conduct & Safety", "Customer Support & Refunds", "App UX & UC Plus"],
  "search_vectors": ["2-3 realistic phrases real users search/write on Reddit or Play Store"],
  "semantic_keywords": ["list of 6-10 conceptual keywords associated with this intent"]
}}
Return ONLY raw JSON. No markdown ticks, no preamble.
"""
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                cleaned_text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE).strip()
                data = json.loads(cleaned_text)
                return QueryDecomposition(
                    raw_query=raw_query,
                    interpreted_intent=data.get("interpreted_intent", raw_query),
                    core_topic=data.get("core_topic", "general_exploration"),
                    time_horizon=data.get("time_horizon"),
                    target_verticals=data.get("target_verticals", [ServiceVertical.GENERAL.value]),
                    target_aspects=data.get("target_aspects", ["Service Quality"]),
                    search_vectors=data.get("search_vectors", [f"Urban Company {raw_query}"]),
                    semantic_keywords=data.get("semantic_keywords", []),
                    is_vague=False
                )
        return None

query_decomposer = QueryDecomposer()
