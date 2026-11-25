import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from google_play_scraper import reviews, Sort

from backend.app.core.config import settings
from backend.app.models.schemas import FeedbackItem, FeedbackSource
from backend.app.scrapers.base import generate_hash_id
from backend.app.intelligence.pii_redactor import pii_redactor
from backend.app.intelligence.hinglish_engine import hinglish_engine
from backend.app.intelligence.aspect_classifier import aspect_classifier
from backend.app.intelligence.query_decomposer import query_decomposer, QueryDecomposition
from backend.app.db.database import db

STOP_WORDS = {
    "what", "how", "when", "why", "where", "who", "which", "is", "are", "do",
    "does", "did", "the", "a", "an", "and", "or", "to", "for", "in", "on",
    "with", "about", "once", "after", "before", "they", "them", "their", "it",
    "its", "service", "services", "urban", "company", "uc", "customer", "customers"
}

def extract_search_keywords(query: str) -> List[str]:
    tokens = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
    meaningful = [t for t in tokens if t not in STOP_WORDS]
    return meaningful if meaningful else [t for t in tokens if t not in {"the", "and", "for"}]

class LiveIngestor:
    """
    Performs real-time live ingestion over the internet for EVERY search query:
    1. Queries Reddit search API globally (Urban Company + query terms).
    2. Queries key Indian metro subreddits (r/india, r/bangalore, r/delhi, r/mumbai, r/pune).
    3. Searches Google Play Store reviews for matching customer feedback.
    4. Sanitizes PII, normalizes Hinglish, tags aspects, and persists to SQLite.
    """

    def __init__(self):
        self.headers = {"User-Agent": "UrbanCompanyResearchBot/2.1 (Live Public Feedback Engine; Academic Research)"}

    def ingest_live(self, query: str, decomposition: Optional[QueryDecomposition] = None) -> Dict[str, Any]:
        if decomposition is None:
            decomposition = query_decomposer.decompose_query(query)

        primary_vector = decomposition.search_vectors[0] if decomposition.search_vectors else query.strip()
        secondary_vector = decomposition.search_vectors[1] if len(decomposition.search_vectors) > 1 else primary_vector

        new_items: List[FeedbackItem] = []
        sources_contacted = []

        # 1. Global Reddit Search over the internet using primary search vector
        reddit_global = self._search_reddit_global(primary_vector)
        if reddit_global:
            new_items.extend(reddit_global)
            sources_contacted.append("Reddit (Global Search)")

        # 2. Targeted Indian Metro Subreddits using secondary/targeted vector
        reddit_metro = self._search_reddit_subreddits(secondary_vector)
        if reddit_metro:
            new_items.extend(reddit_metro)
            sources_contacted.append("Reddit (r/india, r/bangalore, r/delhi)")

        # 3. Google Play Store Live Search using semantic keywords
        play_items = self._search_play_store_live(primary_vector, decomposition.semantic_keywords)
        if play_items:
            new_items.extend(play_items)
            sources_contacted.append("Google Play Store")

        # Process through PII, Hinglish, Aspect pipelines and persist to DB
        inserted_count = 0
        if new_items:
            processed_items = self._process_items(new_items)
            inserted_count = db.insert_feedback_batch(processed_items)

        return {
            "query": query,
            "interpreted_intent": decomposition.interpreted_intent,
            "search_vectors": decomposition.search_vectors,
            "search_keywords": decomposition.semantic_keywords,
            "decomposition": decomposition.model_dump(),
            "fetched_count": len(new_items),
            "newly_inserted_count": inserted_count,
            "sources": sources_contacted if sources_contacted else ["Reddit", "Google Play Store"]
        }

    def _search_reddit_global(self, search_term: str) -> List[FeedbackItem]:
        items: List[FeedbackItem] = []
        term_clean = search_term.strip()
        if not term_clean.lower().startswith("urban company") and not term_clean.lower().startswith("urbancompany"):
            query_str = f"Urban Company {term_clean}"
        else:
            query_str = term_clean
        encoded = urllib.parse.quote(query_str)
        url = f"https://www.reddit.com/search.json?q={encoded}&sort=relevance&limit=6"

        try:
            with httpx.Client(timeout=3.5, headers=self.headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        post = child.get("data", {})
                        title = post.get("title", "").strip()
                        selftext = post.get("selftext", "").strip()
                        full_text = f"{title}. {selftext}".strip()
                        if len(full_text) < 25:
                            continue

                        permalink = post.get("permalink", "")
                        sub = post.get("subreddit", "india")
                        item_id = generate_hash_id("reddit_global", f"{post.get('id', '')}_{title}")
                        upvotes = post.get("ups", 1)

                        items.append(FeedbackItem(
                            id=item_id,
                            source=FeedbackSource.REDDIT,
                            external_url=f"https://reddit.com{permalink}",
                            author_masked=f"redditor_{item_id[:6]}",
                            rating=None,
                            text_raw=full_text,
                            text_normalized=full_text,
                            city=sub.title() if sub not in ["india", "AskIndia"] else "All India",
                            upvotes=upvotes,
                            ingested_at=datetime.utcnow()
                        ))
        except Exception:
            pass

        return items

    def _search_reddit_subreddits(self, search_term: str) -> List[FeedbackItem]:
        items: List[FeedbackItem] = []
        term_clean = search_term.strip()
        if not term_clean.lower().startswith("urban company") and not term_clean.lower().startswith("urbancompany"):
            query_str = f"Urban Company {term_clean}"
        else:
            query_str = term_clean
        encoded = urllib.parse.quote(query_str)
        subreddits = ["bangalore", "delhi", "mumbai", "india"]

        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={encoded}&restrict_sr=1&sort=relevance&limit=3"
                with httpx.Client(timeout=3.0, headers=self.headers) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        children = data.get("data", {}).get("children", [])
                        for child in children:
                            post = child.get("data", {})
                            title = post.get("title", "").strip()
                            selftext = post.get("selftext", "").strip()
                            full_text = f"{title}. {selftext}".strip()
                            if len(full_text) < 25:
                                continue

                            permalink = post.get("permalink", "")
                            item_id = generate_hash_id("reddit_sub", f"{sub}_{post.get('id', '')}_{title}")
                            upvotes = post.get("ups", 1)

                            items.append(FeedbackItem(
                                id=item_id,
                                source=FeedbackSource.REDDIT,
                                external_url=f"https://reddit.com{permalink}",
                                author_masked=f"redditor_{item_id[:6]}",
                                rating=None,
                                text_raw=full_text,
                                text_normalized=full_text,
                                city=sub.title() if sub != "india" else "All India",
                                upvotes=upvotes,
                                ingested_at=datetime.utcnow()
                            ))
            except Exception:
                pass

        return items

    def _search_play_store_live(self, search_term: str, semantic_keywords: Optional[List[str]] = None) -> List[FeedbackItem]:
        items: List[FeedbackItem] = []
        try:
            result, _ = reviews(
                settings.GOOGLE_PLAY_APP_ID,
                lang="en",
                country="in",
                sort=Sort.MOST_RELEVANT,
                count=40,
            )
            tokens = [k.lower() for k in (semantic_keywords or []) if len(k) > 2]
            if not tokens:
                tokens = [t for t in search_term.lower().split() if len(t) > 3]

            for r in result:
                content = r.get("content", "").strip()
                content_lower = content.lower()
                if any(t in content_lower for t in tokens):
                    rating = float(r.get("score", 3.0))
                    item_id = generate_hash_id("play_store_live", f"{r.get('reviewId', '')}_{content}")
                    items.append(FeedbackItem(
                        id=item_id,
                        source=FeedbackSource.PLAY_STORE,
                        external_url=f"https://play.google.com/store/apps/details?id={settings.GOOGLE_PLAY_APP_ID}",
                        author_masked=f"User_{item_id[:6]}",
                        rating=rating,
                        text_raw=content,
                        text_normalized=content,
                        city="All India",
                        upvotes=r.get("thumbsUpCount", 0),
                        ingested_at=datetime.utcnow()
                    ))
                    if len(items) >= 4:
                        break
        except Exception:
            pass

        return items

    def _process_items(self, raw_items: List[FeedbackItem]) -> List[FeedbackItem]:
        processed = []
        for item in raw_items:
            sanitized, _ = pii_redactor.redact(item.text_raw)
            normalized, is_h, _ = hinglish_engine.normalize(sanitized)
            vertical = aspect_classifier.classify_vertical(normalized)
            aspects = aspect_classifier.classify_aspects(normalized)
            rating_val = item.rating if item.rating is not None else 3.0
            churn_flag, sentiment = aspect_classifier.evaluate_churn_intent(normalized, rating_val)

            item.text_normalized = normalized
            item.service_vertical = vertical
            item.aspects = aspects
            item.is_hinglish = is_h
            item.churn_intent_flag = churn_flag
            item.sentiment_score = sentiment
            processed.append(item)
        return processed

live_ingestor = LiveIngestor()
