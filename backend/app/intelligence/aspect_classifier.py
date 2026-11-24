import re
from typing import List, Tuple
from backend.app.models.schemas import ServiceVertical

ASPECT_PATTERNS = {
    "Pricing & Transparency": [
        r'\b(?:price|pricing|cost|charge|charges|charging|expensive|hidden|rate\s*card|extra\s*money|bill|billing|gst|overcharge|overpriced)\b'
    ],
    "Punctuality & Reliability": [
        r'\b(?:late|delay|delayed|punctual|on\s*time|reschedule|rescheduled|waiting|wait|cancel|cancelled|cancellation|slot|morning|evening|arrival)\b'
    ],
    "Service Quality": [
        r'\b(?:quality|workmanship|skill|skilled|shoddy|damaged|damage|broken|scratch|scratched|repair\s*failed|not\s*working|cooling|leak|leakage)\b'
    ],
    "Partner Conduct & Safety": [
        r'\b(?:behavior|behaviour|rude|polite|professional|unprofessional|uniform|argument|argued|safety|drunk|alcohol|smell|harass|harassment|hygiene)\b'
    ],
    "Customer Support & Refunds": [
        r'\b(?:support|customer\s*care|helpdesk|refund|refunded|ticket|bot|chatbot|resolution|unresolved|escalate|escalation|compensation|voucher|nch|consumer\s*court)\b'
    ],
    "App UX & UC Plus": [
        r'\b(?:app|uc\s*plus|membership|subscription|auto[\-\s]?renew|renewed|crash|crashed|bug|ui|otp|login|debit|debit card)\b'
    ]
}

VERTICAL_PATTERNS = {
    ServiceVertical.APPLIANCE_REPAIR: [
        r'\b(?:ac|air\s*conditioner|compressor|gas\s*leak|gas\s*charging|foam\s*jet|coil|refrigerator|fridge|washing\s*machine|motherboard|pcb|geyser|microwave|water\s*purifier|ro)\b'
    ],
    ServiceVertical.CLEANING: [
        r'\b(?:cleaning|deep\s*clean|bathroom|kitchen\s*clean|sofa|carpet|tile|tiles|chimney|vacuum|scrubbing|dusting|mop|mop machine)\b'
    ],
    ServiceVertical.SALON_SPA: [
        r'\b(?:salon|spa|facial|wax|waxing|haircut|hair\s*color|pedicure|manicure|massage|grooming|beautician|stylist|bridal)\b'
    ],
    ServiceVertical.PLUMBING_CARPENTRY: [
        r'\b(?:plumber|plumbing|pipe|pipes|tap|leak|conduit|electrician|wiring|switchboard|switch|fuse|carpenter|wood|drilling|drill|furniture)\b'
    ],
    ServiceVertical.PAINTING: [
        r'\b(?:paint|painting|waterproofing|wall|walls|roller|primer|dampness|seepage)\b'
    ],
    ServiceVertical.NATIVE_DEVICES: [
        r'\b(?:native|native\s*m1|smart\s*lock|cartridge|purifier\s*filter)\b'
    ]
}

CHURN_INTENT_PATTERNS = [
    r'\b(?:never\s*(?:book|use|again)|uninstalled|uninstalling|worst\s*app|delete\s*account|boycott|switching\s*to\s*local|local\s*(?:vendor|technician)|consumer\s*(?:court|forum|helpline)|fraud\s*company|loot\s*macha)\b'
]

class AspectClassifier:
    """Enriches feedback with business aspects, service verticals, and churn intent flags."""

    def classify_aspects(self, text: str) -> List[str]:
        matched = []
        for aspect, patterns in ASPECT_PATTERNS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                matched.append(aspect)
        return matched if matched else ["General Experience"]

    def classify_vertical(self, text: str) -> ServiceVertical:
        for vertical, patterns in VERTICAL_PATTERNS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                return vertical
        return ServiceVertical.GENERAL

    def evaluate_churn_intent(self, text: str, rating: float = 3.0) -> Tuple[bool, float]:
        """Returns (churn_intent_flag, severity_score)."""
        has_churn_keywords = any(re.search(p, text, re.IGNORECASE) for p in CHURN_INTENT_PATTERNS)
        is_extreme_rating = (rating <= 1.0)
        
        churn_flag = has_churn_keywords or (is_extreme_rating and len(text) > 80)
        
        # Calculate severity score from -1.0 (extreme negative) to 1.0 (delight)
        base_score = (rating - 3.0) / 2.0 if rating is not None else 0.0
        if churn_flag:
            base_score = min(base_score, -0.75)

        return churn_flag, round(base_score, 2)

aspect_classifier = AspectClassifier()

