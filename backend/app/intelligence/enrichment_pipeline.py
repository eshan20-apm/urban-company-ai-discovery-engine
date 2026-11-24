import json
from typing import Dict, Any, List
from backend.app.db.database import db
from backend.app.intelligence.pii_redactor import pii_redactor
from backend.app.intelligence.hinglish_engine import hinglish_engine
from backend.app.intelligence.aspect_classifier import aspect_classifier
from backend.app.intelligence.causal_extractor import causal_extractor

class EnrichmentPipeline:
    """Orchestrates Phase 2 & 3 preprocessing, PII masking, Hinglish translation, and causal enrichment."""

    def run_pipeline(self) -> Dict[str, Any]:
        print("[EnrichmentPipeline] Starting text preprocessing & causal enrichment on SQLite database...")
        items = db.get_feedback_items(limit=1000)
        
        updated_count = 0
        hinglish_detected_count = 0
        pii_masked_count = 0
        churn_intent_count = 0

        with db.get_connection() as conn:
            cursor = conn.cursor()
            for item in items:
                # 1. PII Redaction
                text_sanitized, pii_types = pii_redactor.redact(item.text_raw)
                if pii_types:
                    pii_masked_count += 1

                # 2. Hinglish Normalization
                text_norm, is_h, _ = hinglish_engine.normalize(text_sanitized)
                if is_h:
                    hinglish_detected_count += 1

                # 3. Re-classify Verticals & Aspects
                vertical = aspect_classifier.classify_vertical(text_norm)
                aspects = aspect_classifier.classify_aspects(text_norm)

                # 4. Churn Intent Evaluation
                rating_val = item.rating if item.rating is not None else 3.0
                churn_flag, sentiment = aspect_classifier.evaluate_churn_intent(text_norm, rating_val)
                if churn_flag:
                    churn_intent_count += 1

                # 5. Update row in database
                cursor.execute("""
                UPDATE feedback_items
                SET text_normalized = ?,
                    service_vertical = ?,
                    aspects = ?,
                    sentiment_score = ?,
                    churn_intent_flag = ?,
                    is_hinglish = ?
                WHERE id = ?
                """, (
                    text_norm,
                    vertical.value,
                    json.dumps(aspects),
                    sentiment,
                    1 if churn_flag else 0,
                    1 if is_h else 0,
                    item.id
                ))
                updated_count += 1

            conn.commit()

        stats = {
            "total_processed": updated_count,
            "pii_masked_items": pii_masked_count,
            "hinglish_normalized_items": hinglish_detected_count,
            "churn_intent_flagged": churn_intent_count
        }
        print("[EnrichmentPipeline] Completed successfully! Stats:", stats)
        return stats

enrichment_pipeline = EnrichmentPipeline()

if __name__ == "__main__":
    enrichment_pipeline.run_pipeline()

