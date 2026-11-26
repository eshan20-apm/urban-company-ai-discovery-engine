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
        sources_contacted: List[str] = []
        sources_failed: List[str] = []

        # 1. Global Reddit Search over the internet using primary search vector
        reddit_global, global_ok, global_connect_err = self._search_reddit_global(primary_vector)
        if global_ok:
            sources_contacted.append("Reddit (Global Search)")
            if reddit_global:
                new_items.extend(reddit_global)
        else:
            sources_failed.append("Reddit (Global Search)")

        # 2. Targeted Indian Metro Subreddits using secondary/targeted vector (skip if network/DNS is unreachable)
        if not global_connect_err:
            reddit_metro, metro_ok = self._search_reddit_subreddits(secondary_vector)
            if metro_ok:
                sources_contacted.append("Reddit (r/india, r/bangalore, r/delhi)")
                if reddit_metro:
                    new_items.extend(reddit_metro)
            else:
                sources_failed.append("Reddit (Subreddits)")

        # 3. Google Play Store Live Search using query-specific + semantic keywords
        query_tokens = extract_search_keywords(query)
        play_items, play_ok = self._search_play_store_live(
            primary_vector,
            decomposition.semantic_keywords,
            query_tokens=query_tokens,
        )
        if play_ok:
            sources_contacted.append("Google Play Store")
            if play_items:
                new_items.extend(play_items)
        else:
            sources_failed.append("Google Play Store")

        # Deduplicate fetched items in-memory by ID and normalized raw text before DB persistence
        deduped_items: List[FeedbackItem] = []
        seen_ids = set()
        seen_texts = set()
        for item in new_items:
            norm_key = item.text_raw.strip().lower()
            if item.id in seen_ids or norm_key in seen_texts:
                continue
            seen_ids.add(item.id)
            seen_texts.add(norm_key)
            deduped_items.append(item)

        # Process through PII, Hinglish, Aspect pipelines and persist to DB
        inserted_count = 0
        if deduped_items:
            processed_items = self._process_items(deduped_items)
            inserted_count = db.insert_feedback_batch(processed_items)

        return {
            "query": query,
            "interpreted_intent": decomposition.interpreted_intent,
            "search_vectors": decomposition.search_vectors,
            "search_keywords": decomposition.semantic_keywords,
            "decomposition": decomposition.model_dump(),
            "fetched_count": len(deduped_items),
            "newly_inserted_count": inserted_count,
            "sources": sources_contacted,
            "sources_failed": sources_failed,
            "live_search_succeeded": len(sources_contacted) > 0,
        }

    def _search_reddit_global(self, search_term: str) -> tuple[List[FeedbackItem], bool, bool]:
        items: List[FeedbackItem] = []
        term_clean = search_term.strip()
        if not term_clean.lower().startswith("urban company") and not term_clean.lower().startswith("urbancompany"):
            query_str = f"Urban Company {term_clean}"
        else:
            query_str = term_clean
        encoded = urllib.parse.quote(query_str)
        url = f"https://www.reddit.com/search.json?q={encoded}&sort=relevance&limit=8"

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
                        post_uid = post.get("id") or permalink or title
                        item_id = generate_hash_id("reddit", f"{post_uid}_{title}")
                        upvotes = post.get("ups", 1)
                        created_utc = post.get("created_utc")
                        ingested_at = datetime.utcfromtimestamp(created_utc) if created_utc else datetime.utcnow()

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
                            ingested_at=ingested_at
                        ))
                    return items, True, False
        except httpx.ConnectError:
            return items, False, True
        except Exception:
            pass

        return items, False, False

    def _search_reddit_subreddits(self, search_term: str) -> tuple[List[FeedbackItem], bool]:
        items: List[FeedbackItem] = []
        any_ok = False
        term_clean = search_term.strip()
        if not term_clean.lower().startswith("urban company") and not term_clean.lower().startswith("urbancompany"):
            query_str = f"Urban Company {term_clean}"
        else:
            query_str = term_clean
        encoded = urllib.parse.quote(query_str)
        subreddits = ["bangalore", "delhi", "mumbai", "india"]

        try:
            with httpx.Client(timeout=3.0, headers=self.headers) as client:
                for sub in subreddits:
                    try:
                        url = f"https://www.reddit.com/r/{sub}/search.json?q={encoded}&restrict_sr=1&sort=relevance&limit=4"
                        resp = client.get(url)
                        if resp.status_code == 200:
                            any_ok = True
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
                                post_uid = post.get("id") or permalink or title
                                item_id = generate_hash_id("reddit", f"{post_uid}_{title}")
                                upvotes = post.get("ups", 1)
                                created_utc = post.get("created_utc")
                                ingested_at = datetime.utcfromtimestamp(created_utc) if created_utc else datetime.utcnow()

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
                                    ingested_at=ingested_at
                                ))
                    except httpx.ConnectError:
                        break
                    except Exception:
                        continue
        except Exception:
            pass

        return items, any_ok

    def _search_play_store_live(
        self,
        search_term: str,
        semantic_keywords: Optional[List[str]] = None,
        query_tokens: Optional[List[str]] = None,
    ) -> tuple[List[FeedbackItem], bool]:
        items: List[FeedbackItem] = []
        try:
            # Fetch newest reviews (not just static MOST_RELEVANT) to capture fresh feedback
            newest_result, _ = reviews(
                settings.GOOGLE_PLAY_APP_ID,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=80,
            )
            relevant_result, _ = reviews(
                settings.GOOGLE_PLAY_APP_ID,
                lang="en",
                country="in",
                sort=Sort.MOST_RELEVANT,
                count=40,
            )

            seen_review_ids = set()
            combined_reviews = []
            for r in (newest_result or []) + (relevant_result or []):
                rid = r.get("reviewId", "")
                if rid and rid in seen_review_ids:
                    continue
                if rid:
                    seen_review_ids.add(rid)
                combined_reviews.append(r)

            if not combined_reviews:
                return items, False

            tokens = [t.lower() for t in (query_tokens or []) if len(t) > 2 and t.lower() not in STOP_WORDS]
            for k in (semantic_keywords or []):
                kl = k.lower().strip()
                if len(kl) > 2 and kl not in STOP_WORDS and kl not in tokens:
                    tokens.append(kl)
            if not tokens:
                tokens = [t for t in search_term.lower().split() if len(t) > 3 and t not in STOP_WORDS]

            scored_matches = []
            for r in combined_reviews:
                content = r.get("content", "").strip()
                if len(content) < 25:
                    continue
                content_lower = content.lower()
                match_hits = sum(1 for t in tokens if re.search(rf'\b{re.escape(t)}\b', content_lower))
                if match_hits > 0:
                    scored_matches.append((match_hits, r))

            scored_matches.sort(key=lambda x: -x[0])

            for _, r in scored_matches[:6]:
                content = r.get("content", "").strip()
                rating = float(r.get("score", 3.0))
                item_id = generate_hash_id("play_store", f"{r.get('reviewId', '')}_{content}")
                date_val = r.get("at", datetime.utcnow())
                if isinstance(date_val, str):
                    try:
                        date_val = datetime.fromisoformat(date_val)
                    except Exception:
                        date_val = datetime.utcnow()

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
                    ingested_at=date_val
                ))
            return items, True
        except Exception:
            return items, False

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
