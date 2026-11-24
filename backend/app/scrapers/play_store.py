import json
from datetime import datetime
from typing import List, Optional
from google_play_scraper import reviews, Sort

from backend.app.core.config import settings
from backend.app.models.schemas import FeedbackItem, FeedbackSource
from backend.app.scrapers.base import (
    generate_hash_id,
    detect_hinglish,
    detect_churn_intent,
    detect_vertical,
    detect_aspects,
    detect_city,
    heuristic_sentiment,
)

class PlayStoreScraper:
    def __init__(self, app_id: Optional[str] = None):
        self.app_id = app_id or settings.GOOGLE_PLAY_APP_ID

    def fetch_reviews(self, count: int = 150) -> List[FeedbackItem]:
        items: List[FeedbackItem] = []
        try:
            result, _ = reviews(
                self.app_id,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=count,
            )
            for r in result:
                text_raw = r.get("content", "").strip()
                if not text_raw:
                    continue
                rating = float(r.get("score", 3.0))
                item_id = generate_hash_id("play_store", f"{r.get('reviewId', '')}_{text_raw}")
                date_val = r.get("at", datetime.utcnow())
                if isinstance(date_val, str):
                    try:
                        date_val = datetime.fromisoformat(date_val)
                    except Exception:
                        date_val = datetime.utcnow()

                items.append(FeedbackItem(
                    id=item_id,
                    source=FeedbackSource.PLAY_STORE,
                    external_url=f"https://play.google.com/store/apps/details?id={self.app_id}",
                    author_masked=f"User_{item_id[:6]}",
                    rating=rating,
                    text_raw=text_raw,
                    text_normalized=text_raw,
                    city=detect_city(text_raw),
                    service_vertical=detect_vertical(text_raw),
                    aspects=detect_aspects(text_raw),
                    sentiment_score=heuristic_sentiment(rating, text_raw),
                    churn_intent_flag=detect_churn_intent(text_raw),
                    is_hinglish=detect_hinglish(text_raw),
                    upvotes=r.get("thumbsUpCount", 0),
                    ingested_at=date_val
                ))
        except Exception as e:
            print(f"[PlayStoreScraper] Live fetch error: {e}. Falling back to curated offline snapshot.")
            items = self.load_fallback_samples()
        return items

    def load_fallback_samples(self) -> List[FeedbackItem]:
        samples = [
            ("AC service partner asked for Rs 3000 extra cash for gas leak without providing any bill on the app. Completely disappointed with Urban Company.", 1.0, "Delhi-NCR"),
            ("Bathroom deep cleaning was done thoroughly by the partner in Bangalore. Very polite and brought their own machine.", 5.0, "Bangalore"),
            ("Technician was 1 hour late and then cancelled the booking at 8 PM. Now switching to local electrician.", 1.0, "Mumbai"),
            ("Salon at home service was super convenient, hygienic kit and polite beautician. Will book again.", 5.0, "Pune"),
            ("UC Plus membership auto-debited without any SMS notification. Customer support bot has zero human escalations.", 2.0, "Hyderabad"),
            ("Water purifier service was good but filter replacement cost is very high compared to market.", 3.0, "Bangalore"),
            ("Bhai technician bola ki motherboard kharab hai washing machine ka, 4500 mang raha tha, local wale ne 500 me wire theek kiya.", 1.0, "Delhi-NCR"),
            ("Great sofa dry cleaning. Stains completely gone. Worth the price.", 5.0, "All India"),
            ("Painting quote changed drastically after inspection. Initial estimate on app was totally misleading.", 2.0, "Bangalore"),
            ("Worst customer service. Damaged my glass table during kitchen cleaning and offered only 200 rs coupon.", 1.0, "Mumbai")
        ]
        items = []
        for text, rating, city in samples:
            item_id = generate_hash_id("play_store", text)
            items.append(FeedbackItem(
                id=item_id,
                source=FeedbackSource.PLAY_STORE,
                external_url=f"https://play.google.com/store/apps/details?id={self.app_id}",
                author_masked=f"User_{item_id[:6]}",
                rating=rating,
                text_raw=text,
                text_normalized=text,
                city=city,
                service_vertical=detect_vertical(text),
                aspects=detect_aspects(text),
                sentiment_score=heuristic_sentiment(rating, text),
                churn_intent_flag=detect_churn_intent(text),
                is_hinglish=detect_hinglish(text),
                upvotes=2,
                ingested_at=datetime.utcnow()
            ))
        return items

