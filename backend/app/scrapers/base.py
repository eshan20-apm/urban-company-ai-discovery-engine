import hashlib
import re
from datetime import datetime
from typing import List, Tuple, Optional
from backend.app.models.schemas import FeedbackItem, FeedbackSource, ServiceVertical

HINGLISH_KEYWORDS = {
    "hai", "nahi", "tha", "thi", "the", "bhi", "kuch", "kar", "karo", "diya",
    "dega", "bol", "bola", "raha", "rahi", "wala", "wali", "zyada", "accha",
    "bahut", "paise", "kaam", "paisa", "rupaye", "mat", "karna", "lut", "loot",
    "chor", "bakwas", "bekar", "ghatia", "kharab", "dhokha", "gaya", "aaya"
}

CHURN_PHRASES = [
    "never book", "never use", "uninstalled", "uninstalling", "worst app",
    "cheating customers", "scam company", "loot macha", "boycott",
    "switching to", "local vendor", "local technician", "delete account",
    "fraud company", "never again", "consumer court"
]

def generate_hash_id(source: str, unique_str: str) -> str:
    payload = f"{source}::{unique_str.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

def detect_hinglish(text: str) -> bool:
    tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    matches = tokens.intersection(HINGLISH_KEYWORDS)
    return len(matches) >= 2

def detect_churn_intent(text: str) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in CHURN_PHRASES)

def detect_vertical(text: str) -> ServiceVertical:
    t = text.lower()
    if any(w in t for w in ["ac", "air conditioner", "refrigerator", "fridge", "washing machine", "geyser", "microwave", "ro water", "water purifier", "cooling", "compressor"]):
        return ServiceVertical.APPLIANCE_REPAIR
    elif any(w in t for w in ["cleaning", "deep clean", "bathroom", "kitchen clean", "sofa", "carpet", "house clean", "dusting", "mop"]):
        return ServiceVertical.CLEANING
    elif any(w in t for w in ["salon", "spa", "facial", "waxing", "haircut", "pedicure", "manicure", "massage", "beard", "cleanup", "grooming"]):
        return ServiceVertical.SALON_SPA
    elif any(w in t for w in ["plumber", "plumbing", "electrician", "wiring", "switchboard", "carpenter", "tap leak", "flush", "drill", "fuse"]):
        return ServiceVertical.PLUMBING_CARPENTRY
    elif any(w in t for w in ["paint", "painting", "waterproofing", "wall paint", "roller"]):
        return ServiceVertical.PAINTING
    elif any(w in t for w in ["native", "purifier", "smart lock", "native m1", "smart device"]):
        return ServiceVertical.NATIVE_DEVICES
    return ServiceVertical.GENERAL

def detect_aspects(text: str) -> List[str]:
    t = text.lower()
    aspects = []
    if any(w in t for w in ["price", "cost", "charge", "expensive", "hidden", "rate card", "extra money", "bill", "gst", "fee", "overcharge"]):
        aspects.append("Pricing & Transparency")
    if any(w in t for w in ["late", "delay", "on time", "punctual", "reschedule", "waiting", "cancel", "slot"]):
        aspects.append("Punctuality & Reliability")
    if any(w in t for w in ["quality", "workmanship", "skill", "damaged", "repair failed", "not working", "properly"]):
        aspects.append("Service Quality")
    if any(w in t for w in ["behavior", "rude", "polite", "professional", "uniform", "argument", "safety", "unprofessional"]):
        aspects.append("Partner Conduct & Safety")
    if any(w in t for w in ["support", "customer care", "helpdesk", "refund", "ticket", "bot", "resolution", "warranty"]):
        aspects.append("Customer Support & Refunds")
    if any(w in t for w in ["app", "plus", "membership", "subscription", "crash", "ui", "otp", "booking"]):
        aspects.append("App UX & UC Plus")
    return aspects if aspects else ["General Experience"]

def detect_city(text: str) -> str:
    t = text.lower()
    cities = {
        "bangalore": "Bangalore",
        "bengaluru": "Bangalore",
        "delhi": "Delhi-NCR",
        "noida": "Delhi-NCR",
        "gurgaon": "Delhi-NCR",
        "gurugram": "Delhi-NCR",
        "mumbai": "Mumbai",
        "thane": "Mumbai",
        "pune": "Pune",
        "hyderabad": "Hyderabad",
        "chennai": "Chennai",
        "kolkata": "Kolkata",
        "ahmedabad": "Ahmedabad"
    }
    for k, v in cities.items():
        if k in t:
            return v
    return "All India"

def heuristic_sentiment(rating: Optional[float], text: str) -> float:
    if rating is not None:
        return round((rating - 3.0) / 2.0, 2)
    # Text fallback
    t = text.lower()
    neg_score = sum(1 for w in ["worst", "bad", "scam", "poor", "loot", "terrible", "waste", "horrible", "fraud"] if w in t)
    pos_score = sum(1 for w in ["great", "good", "excellent", "best", "awesome", "prompt", "clean", "satisfied"] if w in t)
    total = neg_score + pos_score
    if total == 0:
        return 0.0
    return round((pos_score - neg_score) / total, 2)

