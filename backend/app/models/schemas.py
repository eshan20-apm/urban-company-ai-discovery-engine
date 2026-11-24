from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class FeedbackSource(str, Enum):
    PLAY_STORE = "play_store"
    APP_STORE = "app_store"
    REDDIT = "reddit"
    CONSUMER_FORUM = "consumer_forum"
    YOUTUBE = "youtube"
    INVESTOR_REPORT = "investor_report"

class ServiceVertical(str, Enum):
    APPLIANCE_REPAIR = "Appliance Repair"
    CLEANING = "Home Cleaning"
    SALON_SPA = "Salon & Spa"
    PLUMBING_CARPENTRY = "Plumber & Electrician"
    PAINTING = "Painting & Waterproofing"
    NATIVE_DEVICES = "Native Smart Devices"
    GENERAL = "General / Platform"

class FeedbackItem(BaseModel):
    id: str = Field(..., description="Unique deterministic hash (SHA256)")
    source: FeedbackSource
    external_url: Optional[str] = None
    author_masked: str = "[REDACTED_USER]"
    rating: Optional[float] = None  # 1.0 to 5.0
    text_raw: str
    text_normalized: str
    city: Optional[str] = "All India"
    service_vertical: ServiceVertical = ServiceVertical.GENERAL
    aspects: List[str] = Field(default_factory=list)
    sentiment_score: float = 0.0    # -1.0 to 1.0
    churn_intent_flag: bool = False
    is_hinglish: bool = False
    upvotes: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

class CausalChain(BaseModel):
    friction_trigger: str
    customer_reaction: str
    metric_impact: str

class OpportunityArea(BaseModel):
    id: str  # e.g., 'OPP-01'
    title: str
    vertical: ServiceVertical
    affected_business_metric: str
    reach_percentage: float  # e.g., 28.4%
    nps_drag: float          # e.g., -1.8
    churn_elasticity: float  # e.g., 0.41 (41%)
    estimated_revenue_leakage: str  # e.g., "₹3.2M / cohort"
    feasibility_score: float = 3.0  # 1 to 5
    impact_score: float = 4.0       # 1 to 5
    rice_score: float = 0.0
    causal_chains: List[CausalChain] = Field(default_factory=list)
    verbatim_evidence_ids: List[str] = Field(default_factory=list)
    suggested_action: str
    projected_metric_uplift: str

class SimulationRequest(BaseModel):
    opportunity_id: str
    friction_reduction_percentage: float = Field(..., ge=0.0, le=100.0)

class SimulationResponse(BaseModel):
    opportunity_id: str
    opportunity_title: str
    friction_reduction_percentage: float
    projected_nps_delta: str
    projected_repeat_rate_uplift: str
    recovered_annual_revenue: str
    confidence_interval: str

class InvestorClaim(BaseModel):
    id: str
    document_title: str
    claim_quote: str
    category: str
    target_metric: str
    ground_truth_rating: float
    ground_truth_verdict: str  # 'CONFIRMED', 'DIVERGENT', 'CRITICAL_RISK'
    evidence_summary: str

class ExecutiveMetrics(BaseModel):
    total_feedback_items: int
    nps_proxy: float
    high_risk_churn_rate: float
    total_revenue_at_risk: str
    active_opportunity_count: int
    source_distribution: Dict[str, int]
    vertical_distribution: Dict[str, int]

