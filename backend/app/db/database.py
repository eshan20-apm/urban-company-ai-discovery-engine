import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.app.core.config import settings
from backend.app.models.schemas import (
    FeedbackItem,
    OpportunityArea,
    CausalChain,
    InvestorClaim,
    ExecutiveMetrics,
    FeedbackSource,
    ServiceVertical,
)

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Feedback Items Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_items (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                external_url TEXT,
                author_masked TEXT DEFAULT '[REDACTED_USER]',
                rating REAL,
                text_raw TEXT NOT NULL,
                text_normalized TEXT NOT NULL,
                city TEXT DEFAULT 'All India',
                service_vertical TEXT NOT NULL,
                aspects TEXT NOT NULL,          -- JSON list
                sentiment_score REAL DEFAULT 0.0,
                churn_intent_flag INTEGER DEFAULT 0,
                is_hinglish INTEGER DEFAULT 0,
                upvotes INTEGER DEFAULT 0,
                ingested_at TEXT NOT NULL
            );
            """)

            # 2. Opportunity Areas Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunity_areas (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                vertical TEXT NOT NULL,
                affected_business_metric TEXT NOT NULL,
                reach_percentage REAL NOT NULL,
                nps_drag REAL NOT NULL,
                churn_elasticity REAL NOT NULL,
                estimated_revenue_leakage TEXT NOT NULL,
                feasibility_score REAL DEFAULT 3.0,
                impact_score REAL DEFAULT 4.0,
                rice_score REAL DEFAULT 0.0,
                causal_chains TEXT NOT NULL,       -- JSON list of dicts
                verbatim_evidence_ids TEXT NOT NULL, -- JSON list of IDs
                suggested_action TEXT NOT NULL,
                projected_metric_uplift TEXT NOT NULL
            );
            """)

            # 3. Investor Claims Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS investor_claims (
                id TEXT PRIMARY KEY,
                document_title TEXT NOT NULL,
                claim_quote TEXT NOT NULL,
                category TEXT NOT NULL,
                target_metric TEXT NOT NULL,
                ground_truth_rating REAL NOT NULL,
                ground_truth_verdict TEXT NOT NULL,
                evidence_summary TEXT NOT NULL
            );
            """)

            # 4. Simulation Logs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT NOT NULL,
                friction_reduction REAL NOT NULL,
                projected_nps_delta TEXT NOT NULL,
                projected_repeat_rate_uplift TEXT NOT NULL,
                recovered_revenue TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # Indices for rapid querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_vertical ON feedback_items(service_vertical);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_source ON feedback_items(source);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_city ON feedback_items(city);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback_items(rating);")
            conn.commit()

    def insert_feedback_batch(self, items: List[FeedbackItem]) -> int:
        if not items:
            return 0
        inserted = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in items:
                try:
                    cursor.execute("""
                    INSERT OR IGNORE INTO feedback_items (
                        id, source, external_url, author_masked, rating,
                        text_raw, text_normalized, city, service_vertical,
                        aspects, sentiment_score, churn_intent_flag,
                        is_hinglish, upvotes, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.id,
                        item.source.value,
                        item.external_url,
                        item.author_masked,
                        item.rating,
                        item.text_raw,
                        item.text_normalized,
                        item.city,
                        item.service_vertical.value,
                        json.dumps(item.aspects),
                        item.sentiment_score,
                        1 if item.churn_intent_flag else 0,
                        1 if item.is_hinglish else 0,
                        item.upvotes,
                        item.ingested_at.isoformat()
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    print(f"Error inserting feedback item {item.id}: {e}")
            conn.commit()
        return inserted

    def get_feedback_items(
        self,
        vertical: Optional[str] = None,
        source: Optional[str] = None,
        city: Optional[str] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FeedbackItem]:
        query = "SELECT * FROM feedback_items WHERE 1=1"
        params: List[Any] = []

        if vertical:
            query += " AND service_vertical = ?"
            params.append(vertical)
        if source:
            query += " AND source = ?"
            params.append(source)
        if city:
            query += " AND city = ?"
            params.append(city)
        if min_rating is not None:
            query += " AND rating >= ?"
            params.append(min_rating)
        if max_rating is not None:
            query += " AND rating <= ?"
            params.append(max_rating)

        query += " ORDER BY ingested_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            items = []
            for r in rows:
                items.append(FeedbackItem(
                    id=r["id"],
                    source=FeedbackSource(r["source"]),
                    external_url=r["external_url"],
                    author_masked=r["author_masked"],
                    rating=r["rating"],
                    text_raw=r["text_raw"],
                    text_normalized=r["text_normalized"],
                    city=r["city"],
                    service_vertical=ServiceVertical(r["service_vertical"]),
                    aspects=json.loads(r["aspects"]),
                    sentiment_score=r["sentiment_score"],
                    churn_intent_flag=bool(r["churn_intent_flag"]),
                    is_hinglish=bool(r["is_hinglish"]),
                    upvotes=r["upvotes"],
                    ingested_at=datetime.fromisoformat(r["ingested_at"])
                ))
            return items

    def insert_opportunity(self, opp: OpportunityArea):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO opportunity_areas (
                id, title, vertical, affected_business_metric,
                reach_percentage, nps_drag, churn_elasticity,
                estimated_revenue_leakage, feasibility_score,
                impact_score, rice_score, causal_chains,
                verbatim_evidence_ids, suggested_action,
                projected_metric_uplift
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp.id,
                opp.title,
                opp.vertical.value,
                opp.affected_business_metric,
                opp.reach_percentage,
                opp.nps_drag,
                opp.churn_elasticity,
                opp.estimated_revenue_leakage,
                opp.feasibility_score,
                opp.impact_score,
                opp.rice_score,
                json.dumps([c.model_dump() for c in opp.causal_chains]),
                json.dumps(opp.verbatim_evidence_ids),
                opp.suggested_action,
                opp.projected_metric_uplift
            ))
            conn.commit()

    def get_opportunities(self) -> List[OpportunityArea]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM opportunity_areas ORDER BY rice_score DESC")
            rows = cursor.fetchall()
            opps = []
            for r in rows:
                causal_data = json.loads(r["causal_chains"])
                causal_chains = [CausalChain(**c) for c in causal_data]
                opps.append(OpportunityArea(
                    id=r["id"],
                    title=r["title"],
                    vertical=ServiceVertical(r["vertical"]),
                    affected_business_metric=r["affected_business_metric"],
                    reach_percentage=r["reach_percentage"],
                    nps_drag=r["nps_drag"],
                    churn_elasticity=r["churn_elasticity"],
                    estimated_revenue_leakage=r["estimated_revenue_leakage"],
                    feasibility_score=r["feasibility_score"],
                    impact_score=r["impact_score"],
                    rice_score=r["rice_score"],
                    causal_chains=causal_chains,
                    verbatim_evidence_ids=json.loads(r["verbatim_evidence_ids"]),
                    suggested_action=r["suggested_action"],
                    projected_metric_uplift=r["projected_metric_uplift"]
                ))
            return opps

    def get_executive_metrics(self) -> ExecutiveMetrics:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total feedback count
            cursor.execute("SELECT COUNT(*) as total FROM feedback_items")
            total = cursor.fetchone()["total"] or 0
            
            # NPS Proxy (scale 1-5 mapped to -100 to +100 proxy)
            # Promoters (rating >= 4.5): +100, Passives (3.5-4.4): 0, Detractors (< 3.5): -100
            cursor.execute("""
            SELECT 
                SUM(CASE WHEN rating >= 4.5 THEN 1 ELSE 0 END) as promoters,
                SUM(CASE WHEN rating < 3.5 THEN 1 ELSE 0 END) as detractors,
                COUNT(*) as total_rated
            FROM feedback_items WHERE rating IS NOT NULL
            """)
            nps_row = cursor.fetchone()
            promoters = nps_row["promoters"] or 0
            detractors = nps_row["detractors"] or 0
            total_rated = nps_row["total_rated"] or 1
            nps_proxy = round(((promoters - detractors) / total_rated) * 100, 1)

            # High risk churn count
            cursor.execute("SELECT COUNT(*) as churn_count FROM feedback_items WHERE churn_intent_flag = 1")
            churn_count = cursor.fetchone()["churn_count"] or 0
            churn_rate = round((churn_count / max(total, 1)) * 100, 1)

            # Source distribution
            cursor.execute("SELECT source, COUNT(*) as cnt FROM feedback_items GROUP BY source")
            source_dist = {r["source"]: r["cnt"] for r in cursor.fetchall()}

            # Vertical distribution
            cursor.execute("SELECT service_vertical, COUNT(*) as cnt FROM feedback_items GROUP BY service_vertical")
            vertical_dist = {r["service_vertical"]: r["cnt"] for r in cursor.fetchall()}

            # Opportunities count
            cursor.execute("SELECT COUNT(*) as opp_count FROM opportunity_areas")
            opp_count = cursor.fetchone()["opp_count"] or 0

            return ExecutiveMetrics(
                total_feedback_items=total,
                nps_proxy=nps_proxy,
                high_risk_churn_rate=churn_rate,
                total_revenue_at_risk="₹14.8M / year",
                active_opportunity_count=opp_count,
                source_distribution=source_dist,
                vertical_distribution=vertical_dist
            )

db = Database()
