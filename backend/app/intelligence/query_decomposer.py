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

        # B. Service Vertical Detection (word-boundary matched so e.g. 'facial' doesn't match 'ac')
        verticals = []
        if re.search(r'\b(?:ac|air\s*conditioner|fridge|refrigerator|washing\s*machine|ro|water\s*purifier|geyser|microwave)\b', query_lower):
            verticals.append(ServiceVertical.APPLIANCE_REPAIR.value)
        if re.search(r'\b(?:clean|cleaning|deep\s*clean|bathroom|sofa|kitchen)\b', query_lower):
            verticals.append(ServiceVertical.CLEANING.value)
        if re.search(r'\b(?:salon|spa|facial|wax|waxing|haircut|makeup|massage|pedicure|hygiene)\b', query_lower):
            verticals.append(ServiceVertical.SALON_SPA.value)
        if re.search(r'\b(?:plumber|plumbing|pipe|tap|electrician|wire|wiring|carpenter|drill)\b', query_lower):
            verticals.append(ServiceVertical.PLUMBING_CARPENTRY.value)
        if re.search(r'\b(?:paint|painting|waterproofing|dampness)\b', query_lower):
            verticals.append(ServiceVertical.PAINTING.value)
        if not verticals:
            verticals.append(ServiceVertical.GENERAL.value)

        # C. Intent & Topic Pattern Matching
        # 1. Offline Technician Leakage / Direct Contact / WhatsApp / Cash outside app
        if any(p in query_lower for p in ["direct", "whatsapp", "outside app", "cash payment directly", "without app", "deal directly"]):
            interpreted_intent = "Doorstep Disintermediation & Offline Technician Contact Defection"
            core_topic = "offline_defection"
            target_aspects = ["Pricing & Transparency", "Partner Conduct & Safety"]
            search_vectors = [
                "Urban Company technician contact directly whatsapp cash",
                "Urban company technician deal outside app",
                "Urban company offline service booking"
            ]
            semantic_keywords = ["whatsapp", "cash", "offline", "direct", "outside", "phone", "number", "local"]
            is_vague = False

        # 2. Retention, Cohort Windows, Repeat Booking & Post-Booking Behavior
        elif any(p in query_lower for p in ["repeat", "retention", "rebook", "next booking", "subsequent", "after the last booking", "what customers are doing", "what urban company customers are doing", "cohort", "come back"]):
            if time_horizon:
                qty_unit = time_horizon.replace('_', '-').upper() if 'day' in time_horizon else time_horizon.replace('_', ' ').title()
                interpreted_intent = f"{qty_unit} Customer Retention & Repeat Booking Dynamics"
                search_vectors = [
                    f"Urban company repeat booking {time_horizon.replace('_', ' ')}",
                    "Urban company customer retention repeat service dropoff",
                    f"Urban company rebook after {time_horizon.replace('_', ' ')}"
                ]
            else:
                interpreted_intent = "Customer Repeat Booking Behavior & Platform Re-engagement"
                search_vectors = [
                    "Urban company repeat booking service frequency",
                    "Urban company customer rebooking dropoff pattern",
                    "Urban company repeat customer experience"
                ]
            core_topic = "retention_and_repeat_behavior"
            target_aspects = ["Pricing & Transparency", "App UX & UC Plus", "Customer Support & Refunds"]
            semantic_keywords = ["repeat", "retention", "subsequent", "frequency", "dropoff", "rebook", "subscription", "renew", "renewal", "regular", "again"]
            is_vague = False

        # 3. Explicit Churn / Defection / Stopping usage / Switching to local technicians
        elif any(p in query_lower for p in ["stop using", "stopped using", "leave", "leaving", "uninstall", "delete app", "delete the app", "switch to local", "never book again", "defect", "defection", "local offline", "local technician", "local vendor"]):
            interpreted_intent = "Customer Churn Triggers, Platform Defection & Local Technician Switch"
            core_topic = "churn_and_defection"
            target_aspects = ["Pricing & Transparency", "Customer Support & Refunds", "Service Quality"]
            search_vectors = [
                "Urban company worst app uninstall delete account",
                "Urban company switching to local offline vendors",
                "Urban company unfair charges customer care no help"
            ]
            semantic_keywords = ["uninstall", "delete", "switch", "local", "vendor", "offline", "scam", "churn", "stop", "never again"]
            is_vague = True if len(raw_query.split()) < 6 else False

        # 4. Doorstep Pricing & Cash/Overcharging
        elif any(p in query_lower for p in ["extra money", "taking extra", "overcharging", "overcharge", "hidden charge", "rate card", "asking cash", "cash payment", "bill mismatch"]):
            interpreted_intent = "Doorstep Pricing Transparency, Cash Surcharges & Spare Parts Disputes"
            core_topic = "pricing_transparency"
            target_aspects = ["Pricing & Transparency", "Partner Conduct & Safety"]
            search_vectors = [
                "Urban company technician asking cash extra money",
                "Urban company spare parts rate card bill overcharge",
                "Urban company visiting charge without parts"
            ]
            semantic_keywords = ["extra", "cash", "overcharge", "overcharging", "parts", "bill", "hidden", "doorstep", "expensive", "inspection", "visitation"]
            is_vague = False

        # 5. Delays, Cancellations, No-shows
        elif any(p in query_lower for p in ["cancel", "cancelled", "delay", "reschedule", "didn't show", "not turn up", "late", "punctual"]):
            interpreted_intent = "Doorstep Arrival Reliability, Partner No-Shows & Cancellation Frictions"
            core_topic = "punctuality_and_cancellation"
            target_aspects = ["Punctuality & Reliability", "Customer Support & Refunds"]
            search_vectors = [
                "Urban company partner did not turn up cancelled",
                "Urban company appointment rescheduled delay emergency",
                "Urban company missed call policy cancellation fine"
            ]
            semantic_keywords = ["cancel", "cancelled", "cancellation", "delay", "delayed", "reschedule", "rescheduled", "waiting", "turn up", "arrive", "late", "slot", "fine"]
            is_vague = False

        # 6. Service Quality / Poor workmanship / Broken item
        elif any(p in query_lower for p in ["gas leak", "gas charging", "cooling issue", "compressor", "foam jet", "diagnostic", "poor work", "shoddy", "damaged", "broken", "not working after", "failed repair"]):
            interpreted_intent = "Appliance & Service Diagnostic Integrity, Workmanship & Repair Failure Risks"
            core_topic = "service_quality_and_damages"
            target_aspects = ["Service Quality", "Pricing & Transparency"]
            search_vectors = [
                "Urban company AC gas leak recharge scam charge",
                "Urban company repair failed not working damage",
                "Urban company technician broke laptop appliance"
            ]
            semantic_keywords = ["quality", "damaged", "damage", "broken", "failed", "gas", "leak", "cooling", "rework", "warranty", "shoddy", "compressor"]
            is_vague = False

        # 7a. Post-Booking Expectations (Distinct from Pre-Booking Decision Triggers)
        elif any(p in query_lower for p in ["booking is complete", "expect once", "after booking", "confirmation", "post booking", "post-booking"]):
            interpreted_intent = "Post-Booking Customer Expectations, Arrival Assurance & Price Clarity"
            core_topic = "post_booking_expectations"
            target_aspects = ["Punctuality & Reliability", "Pricing & Transparency", "App UX & UC Plus"]
            search_vectors = [
                "Urban company expectations once booking complete confirmation",
                "Urban company assigned professional did not arrive after booking",
                "Urban company hidden charges after booking confirmation"
            ]
            semantic_keywords = ["confirm", "confirmed", "confirmation", "assigned", "slot", "arrive", "arrived", "show up", "turn up", "estimate", "included", "punctual", "reschedule"]
            is_vague = False

        # 7b. Customer Decision Triggers / When service needed
        elif any(p in query_lower for p in ["decide", "decision", "when is needed", "is needed", "trigger", "why do they call", "when a home service"]):
            interpreted_intent = "Customer Need Triggers, Urgency Drivers & Service Selection Factors"
            core_topic = "customer_decision_triggers"
            target_aspects = ["Service Quality", "App UX & UC Plus"]
            search_vectors = [
                "Urban company how customers decide book home service",
                "Urban company routine cleaning festival emergency instant",
                "Urban company why book vs local technician"
            ]
            semantic_keywords = ["routine", "emergency", "festival", "diwali", "summer", "monsoon", "instant", "urgent", "maintenance", "convenient", "worth", "trusted", "hygiene"]
            is_vague = False

        # 8. Customer Support, Refunds & Disputes
        elif any(p in query_lower for p in ["refund", "customer care", "helpdesk", "bot", "ticket", "dispute", "not satisfied with the serv"]):
            interpreted_intent = "Customer Support Bottlenecks, Automated Bot Frustration & Refund Delays"
            core_topic = "support_and_refunds"
            target_aspects = ["Customer Support & Refunds", "Pricing & Transparency"]
            search_vectors = [
                "Urban company refund not processed invalid ARN number",
                "Urban company chatbot loop support ticket closed without help",
                "Urban company consumer court dispute escalation"
            ]
            semantic_keywords = ["refund", "refunded", "support", "helpdesk", "bot", "chatbot", "ticket", "escalation", "dissatisfied", "complain", "complaint", "care", "dispute", "resolution"]
            is_vague = False

        # 9. Generalized Fallback for any other natural query
        else:
            clean_tokens = [w for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', query_lower) if w not in {"what", "how", "why", "when", "where", "which", "does", "did", "are", "the", "and", "for", "with", "urban", "company", "customer", "customers", "service", "services"}]
            topic_str = " ".join(clean_tokens[:3]).title() if clean_tokens else "Service Experience"
            interpreted_intent = f"Customer Perceptions & Feedback Analysis: {topic_str}"
            core_topic = "general_exploration"
            target_aspects = ["Service Quality", "Pricing & Transparency"]
            search_vectors = [
                f"Urban company {' '.join(clean_tokens[:3])}",
                f"Urban company customer reviews {' '.join(clean_tokens[:2])}"
            ]
            semantic_keywords = clean_tokens if clean_tokens else ["quality", "pricing", "experience"]
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
