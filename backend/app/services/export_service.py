import csv
import io
from typing import List, Optional
from datetime import datetime
from backend.app.db.database import db
from backend.app.models.schemas import FeedbackItem
from backend.app.services.copilot_service import copilot_service

class ExportService:
    """Generates cross-platform CSV exports with UTF-8 BOM for Excel, Google Sheets, and Mac Numbers."""

    @staticmethod
    def export_all_feedback_csv() -> bytes:
        items = db.get_feedback_items(limit=1000)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header Row
        writer.writerow([
            "Feedback ID",
            "Data Tag",
            "Source Platform",
            "Service Vertical",
            "City / Location",
            "Star Rating",
            "Sentiment Score (-1 to 1)",
            "Churn Risk Flag",
            "Hinglish Detected",
            "Key Aspects",
            "Author Handle",
            "Normalized Text (English)",
            "Raw Original Feedback",
            "Original Source URL",
            "Ingestion Date"
        ])

        for item in items:
            data_tag = "Golden Truth" if (item.source.value in ["play_store", "app_store", "consumer_forum"] and not item.is_hinglish) else "AI Tagged"
            writer.writerow([
                item.id,
                data_tag,
                item.source.value.replace("_", " ").title(),
                item.service_vertical.value,
                item.city or "All India",
                f"{item.rating:.1f}" if item.rating is not None else "Unrated",
                f"{item.sentiment_score:.2f}",
                "YES" if item.churn_intent_flag else "NO",
                "YES" if item.is_hinglish else "NO",
                ", ".join(item.aspects),
                item.author_masked,
                item.text_normalized,
                item.text_raw,
                item.external_url or "https://urbancompany.com",
                item.ingested_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(item.ingested_at, "strftime") else str(item.ingested_at)
            ])

        # Encode with UTF-8 BOM (\ufeff) for flawless Excel / Numbers / Sheets opening
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def export_search_results_csv(query: str) -> bytes:
        data = copilot_service.answer_query(query)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Search Query",
            "Analysis Title",
            "Executive Behavioral Takeaway",
            "Item Type",
            "Data Tag",
            "Behavior Pattern / Aspect",
            "Observed Detail / Quote",
            "Source Platform",
            "City / Location",
            "Author Handle",
            "Star Rating",
            "Original Source URL"
        ])

        # Write Findings
        for f in data.get("key_findings", []):
            writer.writerow([
                query,
                data.get("title", ""),
                data.get("executive_takeaway", ""),
                "Behavioral Pattern",
                f.get("tag_label", "AI Tagged"),
                f.get("title", ""),
                f.get("evidence_quote") or f.get("detail", ""),
                f.get("source_tag", "Public Source"),
                f.get("city", "All India"),
                f.get("author", "User"),
                "N/A",
                f.get("url", "https://urbancompany.com")
            ])

        # Write Citations
        for c in data.get("citations", []):
            writer.writerow([
                query,
                data.get("title", ""),
                data.get("executive_takeaway", ""),
                "Verbatim Customer Review",
                c.get("tag_label", "Golden Truth"),
                ", ".join(c.get("aspects", [])),
                c.get("full_text") or c.get("quote", ""),
                c.get("source", "Public Review"),
                c.get("city", "All India"),
                c.get("author", "User"),
                f"{c.get('rating', 'Unrated')}",
                c.get("url", "https://urbancompany.com")
            ])

        return output.getvalue().encode("utf-8-sig")

export_service = ExportService()

