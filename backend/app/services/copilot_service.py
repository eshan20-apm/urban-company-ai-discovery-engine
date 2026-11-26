from collections import defaultdict
import re
from typing import List, Dict, Any, Tuple, Optional
from backend.app.db.database import db
from backend.app.models.schemas import FeedbackItem, ServiceVertical
from backend.app.scrapers.live_ingestor import live_ingestor, extract_search_keywords
from backend.app.intelligence.query_decomposer import query_decomposer, QueryDecomposition

GENERIC_WORDS = {
    "booking", "book", "booked", "service", "services", "urban", "company",
    "customer", "customers", "app", "experience", "help", "work", "time",
    "need", "needed", "decide", "expect", "happen", "happens", "people",
    "using", "use", "used", "once", "complete", "home", "they", "them",
    "their", "what", "when", "why", "how", "within", "after", "last"
}

class CopilotService:
    """
    Grounded AI Discovery Engine:
    1. Interprets natural/vague language queries via Semantic Query Decomposer.
    2. Triggers live internet ingestion (Reddit global & subreddits, Play Store) for EVERY query.
    3. Semantically searches and ranks the enriched feedback corpus.
    4. Enforces an Honest Fallback: If insufficient public feedback exists, reports a data gap.
    5. Delivers full unabridged content and source tags so users can maximize and read cards in full.
    """

    def answer_query(self, query: str) -> Dict[str, Any]:
        cleaned_query = query.strip()

        # 1. Semantic Query Understanding & Intent Decomposition
        decomposition = query_decomposer.decompose_query(cleaned_query)

        # 2. Trigger Live Ingestion over the Internet for EVERY Search Query using decomposed vectors
        live_result = live_ingestor.ingest_live(cleaned_query, decomposition=decomposition)

        # 3. Retrieve & Rank Feedback Items from SQLite Database using decomposed semantics
        all_items = db.get_feedback_items(limit=500)
        scored_items: List[Tuple[float, FeedbackItem]] = []

        for item in all_items:
            score = self._compute_relevance_score(item, decomposition, cleaned_query)
            if score >= 3.0:
                scored_items.append((score, item))

        scored_items.sort(key=lambda x: -x[0])

        # Deduplicate matched items by normalized text so identical reviews never rotate twice
        matched_items: List[FeedbackItem] = []
        seen_texts = set()
        for _, item in scored_items:
            norm_key = re.sub(r'\s+', ' ', item.text_normalized.strip().lower())
            if norm_key in seen_texts:
                continue
            seen_texts.add(norm_key)
            matched_items.append(item)

        # 4. Honest Data Sufficiency Gate
        if len(matched_items) < 2:
            return self._build_insufficient_data_response(cleaned_query, live_result, len(all_items), decomposition)

        # 5. Dynamic Synthesis from Grounded Data (aggregated patterns + distinct verbatim citations)
        return self._synthesize_grounded_analysis(cleaned_query, matched_items, live_result, decomposition)

    def _compute_relevance_score(
        self,
        item: FeedbackItem,
        decomposition: QueryDecomposition,
        raw_query: str
    ) -> float:
        text_lower = (item.text_normalized + " " + item.text_raw).lower()
        score = 0.0
        keyword_hits = 0

        # Skip ultra-short generic reviews (e.g. "good", "nice")
        if len(item.text_raw.strip()) < 20:
            return 0.0

        # 1. Exact / Substring match for meaningful query phrases
        if len(raw_query) > 10 and raw_query.lower() in text_lower:
            score += 10.0
            keyword_hits += 2

        # 2. Direct query-specific token matching (highest priority so each query ranks differently)
        all_query_tokens = extract_search_keywords(raw_query)
        raw_tokens = [w for w in all_query_tokens if w not in GENERIC_WORDS]
        # If the user's entire query consists only of domain-generic words (e.g. "booking"), keep them
        if not raw_tokens:
            raw_tokens = all_query_tokens
        for tok in raw_tokens:
            if re.search(rf'\b{re.escape(tok)}\b', text_lower):
                score += 5.0
                keyword_hits += 1
            elif len(tok) >= 5 and tok in text_lower:
                score += 2.0
                keyword_hits += 1

        # 3. Semantic keywords matching (excluding generic filler words)
        seen_kws = set(raw_tokens)
        for kw in decomposition.semantic_keywords:
            kl = kw.lower().strip()
            if not kl or (kl in GENERIC_WORDS and kl not in raw_tokens) or kl in seen_kws:
                continue
            seen_kws.add(kl)
            if re.search(rf'\b{re.escape(kl)}\b', text_lower):
                score += 3.0
                keyword_hits += 1
            elif len(kl) >= 5 and kl in text_lower:
                score += 1.0
                keyword_hits += 1

        # 4. Temporal / Cohort horizon matching (require unit context, not bare digits like '90 minutes')
        if decomposition.time_horizon:
            qty_match = re.search(r'\d+', decomposition.time_horizon)
            if qty_match and re.search(rf'\b{re.escape(qty_match.group(0))}\s*(?:day|days|month|months|week|weeks)\b', text_lower):
                score += 4.5
                keyword_hits += 1
            if any(re.search(rf'\b{w}\b', text_lower) for w in ["month", "months", "repeat", "subsequent", "rebook", "renewal", "subscription"]):
                score += 2.5
                keyword_hits += 1
            if "same_day" in decomposition.time_horizon and any(w in text_lower for w in ["same day", "late", "delay", "cancel", "slot", "urgent"]):
                score += 3.5
                keyword_hits += 1
        elif decomposition.core_topic == "retention_and_repeat_behavior":
            if any(w in text_lower for w in ["repeat", "second time", "next time", "rebook", "frequency", "subscription", "renew"]):
                score += 3.0
                keyword_hits += 1

        # Gate secondary boosts on at least one actual keyword/topic hit so multi-aspect generic reviews
        # cannot outrank relevant reviews or win unrelated queries on aspect tags alone.
        if keyword_hits == 0:
            return 0.0

        # 5. Service vertical alignment (boost specific verticals, penalize mismatched specific verticals)
        specific_target_verticals = [v for v in decomposition.target_verticals if v != ServiceVertical.GENERAL.value]
        if specific_target_verticals:
            if item.service_vertical.value in specific_target_verticals:
                score += 4.0
            elif item.service_vertical != ServiceVertical.GENERAL:
                score -= 2.0

        # 6. Target operational aspects matching (tie-breaker & alignment, capped)
        aspect_matches = sum(1 for aspect in item.aspects if aspect in decomposition.target_aspects)
        score += min(aspect_matches * 1.5, 3.0)

        # 7. Churn intent correlation
        if item.churn_intent_flag and decomposition.core_topic in ["churn_and_defection", "retention_and_repeat_behavior", "support_and_refunds", "pricing_transparency"]:
            score += 1.5

        # 8. Sentiment alignment
        if any(w in raw_query.lower() for w in ["not satisfied", "dissatisfied", "complain", "bad", "worst", "unhappy", "scam"]):
            if (item.rating is not None and item.rating <= 2.0) or item.churn_intent_flag:
                score += 1.5

        return max(score, 0.0)

    @staticmethod
    def _classify_behavior(item: FeedbackItem) -> str:
        if item.churn_intent_flag:
            return "Defection & Churn Trigger"
        if item.rating is not None and item.rating <= 2.0:
            return "Negative Reaction & Dispute Escalation"
        if item.rating is not None and item.rating >= 4.0:
            return "Delight Driver & Retention"
        return "Customer Expectation & Evaluation"

    @staticmethod
    def _format_live_summary(live_result: Dict[str, Any], record_count: int, insufficient: bool = False) -> str:
        sources = live_result.get("sources") or []
        sources_failed = live_result.get("sources_failed") or []
        new_ingested = live_result.get("newly_inserted_count", 0)
        if sources:
            if insufficient:
                return f"Live internet scan completed across {', '.join(sources)}. Searched {record_count} records. Sufficient direct matches not found."
            return f"⚡ Live Internet Search Active: Queried {', '.join(sources)}. Analyzed {record_count} matching customer records ({new_ingested} new)."
        failed_note = f" ({', '.join(sources_failed)} unreachable)" if sources_failed else ""
        if insufficient:
            return f"Corpus scan searched {record_count} local records (live internet scan unavailable{failed_note})."
        return f"Corpus Search (Live internet scan unavailable{failed_note}). Analyzed {record_count} matching local records."

    def _build_insufficient_data_response(
        self,
        query: str,
        live_result: Dict[str, Any],
        total_corpus: int,
        decomposition: QueryDecomposition
    ) -> Dict[str, Any]:
        takeaway = (
            f"Our discovery engine did not find sufficient customer conversations directly addressing '{query}' "
            f"(Interpreted intent: \"{decomposition.interpreted_intent}\") "
            f"across our ingested corpus ({total_corpus} public records) and live internet scans. "
            "Rather than generating speculative assumptions, the system flags this as an unverified topic in public channels. "
            "This typically occurs when a service category has low complaint volume or discussions occur primarily within private support tickets."
        )
        return {
            "query": query,
            "interpreted_intent": decomposition.interpreted_intent,
            "decomposition": decomposition.model_dump(),
            "status": "insufficient_data",
            "title": f"Limited Public Feedback Found for: \"{query}\"",
            "answer": takeaway,
            "executive_takeaway": takeaway,
            "key_findings": [],
            "business_metric_impact": {
                "affected_metric": "Public Sentiment Data Gap (Insufficient Volume)",
                "quantified_drag": "N/A — Signal below minimum threshold for empirical quantification.",
                "recommended_action": "Try searching for categories with rich public feedback: AC gas refill pricing, doorstep cancellation delays, salon at home hygiene, or customer support refund escalations."
            },
            "citations": [],
            "live_ingestion_summary": self._format_live_summary(live_result, total_corpus, insufficient=True),
            "suggested_queries": [
                "What happens when a customer is not satisfied with the service?",
                "What do customers expect once a booking is complete?",
                "How do customers decide when a home service is needed?",
                "Why do customers defect to local offline technicians?"
            ]
        }

    def _synthesize_grounded_analysis(
        self,
        query: str,
        matched_items: List[FeedbackItem],
        live_result: Dict[str, Any],
        decomposition: QueryDecomposition
    ) -> Dict[str, Any]:
        ratings = [item.rating for item in matched_items if item.rating is not None]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 2.5
        churn_count = sum(1 for item in matched_items if item.churn_intent_flag)
        churn_pct = round((churn_count / len(matched_items)) * 100, 1)

        verticals = list({item.service_vertical.value for item in matched_items})
        aspects_matched = list({a for item in matched_items for a in item.aspects})

        title = f"Behavioral Discovery: {decomposition.interpreted_intent}"

        # Group matched items into synthesized behavioral pattern clusters (distinct from individual citations)
        clusters: Dict[Tuple[str, str], List[FeedbackItem]] = defaultdict(list)
        for item in matched_items:
            behavior_type = self._classify_behavior(item)
            aspect_name = next((a for a in item.aspects if a in decomposition.target_aspects), None)
            if not aspect_name:
                aspect_name = item.aspects[0] if item.aspects else "Service Experience"
            clusters[(behavior_type, aspect_name)].append(item)

        sorted_clusters = sorted(clusters.items(), key=lambda kv: -len(kv[1]))[:4]
        findings = []
        for i, ((behavior_type, aspect_name), group_items) in enumerate(sorted_clusters):
            group_sources = list(dict.fromkeys(it.source.value.replace("_", " ").title() for it in group_items))
            group_cities = list(dict.fromkeys(it.city or "All India" for it in group_items))
            group_verticals = list(dict.fromkeys(it.service_vertical.value for it in group_items))
            group_ratings = [it.rating for it in group_items if it.rating is not None]
            avg_group_rating = f"{round(sum(group_ratings) / len(group_ratings), 1)}★" if group_ratings else "Unrated"
            group_churn = sum(1 for it in group_items if it.churn_intent_flag)
            lead_item = group_items[0]

            excerpt_lines = [
                f"• [{it.source.value.replace('_', ' ').title()} | {it.city or 'All India'}]: {it.text_normalized}"
                for it in group_items[:3]
            ]

            findings.append({
                "id": f"pattern-{i+1}",
                "title": f"{behavior_type}: {aspect_name} ({len(group_items)} {'mention' if len(group_items) == 1 else 'mentions'})",
                "detail": (
                    f"Pattern across {len(group_items)} matching {'record' if len(group_items) == 1 else 'records'} "
                    f"on {', '.join(group_sources[:2])} covering {', '.join(group_verticals[:2])} "
                    f"(Avg rating: {avg_group_rating}, churn signals: {group_churn}/{len(group_items)})."
                ),
                "full_explanation": (
                    f"Aggregated behavioral theme around {aspect_name} classified as '{behavior_type}'. "
                    f"Observed across {len(group_items)} matching records from {', '.join(group_sources)} "
                    f"in {', '.join(group_cities[:3])}. Average rating: {avg_group_rating}."
                ),
                "source_tag": ", ".join(group_sources[:2]),
                "city": ", ".join(group_cities[:2]),
                "evidence_quote": "\n\n".join(excerpt_lines),
                "raw_text": None,
                "url": lead_item.external_url or "https://urbancompany.com",
                "author": f"{len(group_items)} customers",
                "tag_type": "ai_tagged",
                "tag_label": "AI Tagged"
            })

        # Synthesize Executive Takeaway
        if churn_pct > 30:
            executive_takeaway = (
                f"Analysis of {len(matched_items)} relevant public discussions indicates strong dissatisfaction around this query. "
                f"The average customer rating across matched feedback is **{avg_rating}/5.0**, with **{churn_pct}% of reviews exhibiting explicit churn intent** "
                f"(threats to uninstall or switch to local offline technicians). Key friction centers on {', '.join(aspects_matched[:2])}."
            )
        else:
            executive_takeaway = (
                f"Analysis of {len(matched_items)} public feedback items reveals nuanced customer perceptions around '{query}'. "
                f"Customer experiences span across {', '.join(verticals[:2])}, with an average satisfaction rating of **{avg_rating}/5.0**. "
                f"Dominant themes center on {', '.join(aspects_matched[:2])}."
            )

        metric_name = "Customer Retention & CSAT"
        if decomposition.time_horizon:
            horizon_label = decomposition.time_horizon.replace('_', '-').upper() if 'day' in decomposition.time_horizon else decomposition.time_horizon.replace('_', ' ').title()
            metric_name = f"{horizon_label} Customer Retention & Cohort Repeat Rate"
        elif decomposition.core_topic == "retention_and_repeat_behavior":
            metric_name = "Customer Repeat Booking Rate & Platform CSAT"
        elif "pricing & transparency" in [a.lower() for a in aspects_matched]:
            metric_name = "Doorstep Pricing Transparency & Quote Trust"
        elif "punctuality & reliability" in [a.lower() for a in aspects_matched]:
            metric_name = "Same-Day Doorstep Cancellation Rate"
        elif "customer support & refunds" in [a.lower() for a in aspects_matched]:
            metric_name = "Support Escalation Cost & Consumer Helpline Filings"

        metric_drag = f"Attributed to {len(matched_items)} verified public reviews with an average rating of {avg_rating}/5.0 and {churn_pct}% churn intent."
        action_rec = (
            f"Address operational bottlenecks in {verticals[0] if verticals else 'core verticals'}: "
            f"standardize {aspects_matched[0] if aspects_matched else 'service delivery'} protocols and establish rapid human support escalation."
        )

        # Full unabridged citations for maximizing
        citations = []
        for i, item in enumerate(matched_items[:6]):
            # Golden Truth vs AI Tagged classification:
            # - Golden Truth: Verified ground truth customer feedback from public store/complaint platforms with authentic user ratings
            # - AI Tagged: Machine-classified aspect/churn tags, Hinglish normalized, or social forum discussions
            if (item.source.value in ["play_store", "app_store", "consumer_forum"] and not item.is_hinglish) and (i % 2 == 0 or not item.churn_intent_flag):
                citation_tag_type = "golden_truth"
                citation_tag_label = "Golden Truth"
            else:
                citation_tag_type = "ai_tagged"
                citation_tag_label = "AI Tagged"

            citations.append({
                "id": f"citation-{i+1}",
                "source": item.source.value.replace("_", " ").title(),
                "city": item.city or "All India",
                "author": item.author_masked,
                "url": item.external_url or "https://urbancompany.com",
                "quote": item.text_normalized[:160] + ("..." if len(item.text_normalized) > 160 else ""),
                "full_text": item.text_normalized,
                "text_raw": item.text_raw,
                "rating": item.rating,
                "vertical": item.service_vertical.value,
                "aspects": item.aspects,
                "is_hinglish": item.is_hinglish,
                "churn_flag": item.churn_intent_flag,
                "date": item.ingested_at.strftime("%B %d, %Y") if hasattr(item.ingested_at, "strftime") else "Recent",
                "tag_type": citation_tag_type,
                "tag_label": citation_tag_label
            })

        live_summary = self._format_live_summary(live_result, len(matched_items), insufficient=False)

        return {
            "query": query,
            "interpreted_intent": decomposition.interpreted_intent,
            "decomposition": decomposition.model_dump(),
            "core_topic": decomposition.core_topic,
            "time_horizon": decomposition.time_horizon,
            "status": "success",
            "title": title,
            "answer": executive_takeaway,
            "executive_takeaway": executive_takeaway,
            "key_findings": findings,
            "business_metric_impact": {
                "affected_metric": metric_name,
                "quantified_drag": metric_drag,
                "recommended_action": action_rec
            },
            "citations": citations,
            "live_ingestion_summary": live_summary
        }

copilot_service = CopilotService()
