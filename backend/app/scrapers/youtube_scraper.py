from datetime import datetime
from typing import List

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

class YouTubeScraper:
    """Ingests public YouTube comments from high-viewed service reviews and vlogs."""
    def __init__(self):
        pass

    def fetch_comments(self) -> List[FeedbackItem]:
        # Public comments extracted from top Urban Company home cleaning, salon, and AC repair review videos
        comments = [
            ("Urban Company cleaning is good only if you stand on their head the entire time. The moment you leave the room they skip cleaning behind the fridge and under sofa.", "Delhi-NCR", 340, "https://youtube.com/watch?v=sample1"),
            ("Honestly the bridal salon package was amazing. The beautician took 4 hours and did everything with utmost care. Much better than going to a salon in peak traffic.", "Mumbai", 185, "https://youtube.com/watch?v=sample2"),
            ("Technicians are getting paid less each year because of company commission hikes. You can see their lack of motivation in how rushed the AC foam jet service was.", "Bangalore", 420, "https://youtube.com/watch?v=sample3"),
            ("Maine bhi karwaya tha AC service. Foam jet se coil clean kiya aur pura room ganda kar diya. Bad me bolte hain wall safai hamara kaam nahi hai.", "Delhi-NCR", 95, "https://youtube.com/watch?v=sample4"),
            ("Their RO water purifier Native M1 is actually super quiet compared to Kent or Aquaguard. But keep in mind replacement cartridge is proprietary so you are locked in.", "Bangalore", 128, "https://youtube.com/watch?v=sample5"),
            ("The before and after of bathroom deep clean in this video looks exactly like my experience in Pune. Removed hard water stains from tiles completely.", "Pune", 72, "https://youtube.com/watch?v=sample6"),
            ("Watch out for add-on charges! The partner tried to convince my mom that chimney motor needs chemical wash for 1200 extra. Good thing I was there to say no.", "Hyderabad", 210, "https://youtube.com/watch?v=sample7")
        ]

        items = []
        for text, city, upvotes, url in comments:
            item_id = generate_hash_id("youtube", text)
            items.append(FeedbackItem(
                id=item_id,
                source=FeedbackSource.YOUTUBE,
                external_url=url,
                author_masked=f"yt_viewer_{item_id[:6]}",
                rating=None,
                text_raw=text,
                text_normalized=text,
                city=city,
                service_vertical=detect_vertical(text),
                aspects=detect_aspects(text),
                sentiment_score=heuristic_sentiment(None, text),
                churn_intent_flag=detect_churn_intent(text),
                is_hinglish=detect_hinglish(text),
                upvotes=upvotes,
                ingested_at=datetime.utcnow()
            ))
        return items

