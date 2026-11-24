import re
from typing import Tuple, List, Dict

# High-frequency Hinglish phrase mappings to normalized English equivalents
HINGLISH_DICTIONARY: Dict[str, str] = {
    # Negations & Complaints
    "nahi kar raha tha": "was not working",
    "nahi ho raha tha": "was not happening",
    "cooling nahi ho rahi": "not cooling properly",
    "cooling band ho gaya": "cooling stopped working",
    "kharab ho gaya": "got damaged/broken",
    "paise mang raha tha": "demanded extra money",
    "paise maang raha tha": "demanded extra money",
    "bahut zyada charge": "heavily overcharged",
    "extra charge liya": "took unauthorized extra charge",
    "loot macha rakhi hai": "is outright looting customers",
    "bakwas service": "terrible/useless service",
    "bekar service": "poor/substandard service",
    "ghatia kaam": "shoddy workmanship",
    "dhokha hai": "is a fraud/scam",
    "time pe nahi aaya": "did not arrive on time",
    "late aaya": "arrived late",
    "aaya hi nahi": "never showed up",
    "cancel kar diya": "cancelled the booking",
    "paisa barbad": "waste of money",
    "fraud company": "fraudulent service",

    # Words
    "accha": "good",
    "achha": "good",
    "bahut": "very",
    "zyada": "excessive",
    "paisa": "money",
    "paise": "money",
    "rupaye": "rupees",
    "kaam": "workmanship",
    "theek": "satisfactory",
    "sahi": "correct",
    "galat": "wrong/unfair",
    "bhai": "mate/technician"
}

HINGLISH_DETECTION_WORDS = {
    "hai", "nahi", "tha", "thi", "the", "bhi", "kuch", "kar", "karo", "diya",
    "dega", "bol", "bola", "raha", "rahi", "wala", "wali", "zyada", "accha",
    "bahut", "paise", "kaam", "paisa", "rupaye", "mat", "karna", "lut", "loot",
    "chor", "bakwas", "bekar", "ghatia", "kharab", "dhokha", "gaya", "aaya",
    "bhai", "hua", "hoga", "bolo", "krte", "karega"
}

class HinglishEngine:
    """Detects and normalizes Hindi-English code-mixed idioms into standardized English."""

    def is_hinglish(self, text: str) -> bool:
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        matches = tokens.intersection(HINGLISH_DETECTION_WORDS)
        return len(matches) >= 2

    def normalize(self, text: str) -> Tuple[str, bool, List[str]]:
        """
        Normalizes code-mixed feedback into standardized English.
        Returns (normalized_text, is_hinglish_flag, matched_terms).
        """
        is_mixed = self.is_hinglish(text)
        if not is_mixed:
            return text, False, []

        normalized = text
        matched_terms: List[str] = []

        # 1. Replace multi-word idioms first
        for phrase, eng_replacement in sorted(HINGLISH_DICTIONARY.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(rf'\b{re.escape(phrase)}\b', re.IGNORECASE)
            if pattern.search(normalized):
                normalized = pattern.sub(eng_replacement, normalized)
                matched_terms.append(phrase)

        # 2. Contextual cleanups
        # e.g., "500 rs extra" -> "Rs 500 extra"
        normalized = re.sub(r'(\d+)\s*(?:rs|rupees|rupaye)\b', r'Rs \1', normalized, flags=re.IGNORECASE)

        # Clean multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized, True, matched_terms

hinglish_engine = HinglishEngine()

