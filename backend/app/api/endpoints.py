from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from backend.app.services.export_service import export_service

from backend.app.db.database import db
from backend.app.models.schemas import (
    ExecutiveMetrics,
    OpportunityArea,
    SimulationRequest,
    SimulationResponse,
    InvestorClaim,
    FeedbackItem,
    ServiceVertical,
)
from backend.app.intelligence.quantification import quantification_engine
from backend.app.services.copilot_service import copilot_service

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "Urban Company AI Opportunity & Discovery Engine", "version": "1.0.0"}

@router.get("/metrics/executive", response_model=ExecutiveMetrics)
def get_executive_metrics():
    """Returns top-level KPIs including NPS Proxy, Churn Risk, and Source Breakdown."""
    return db.get_executive_metrics()

@router.get("/opportunities", response_model=List[OpportunityArea])
def get_opportunities(vertical: Optional[str] = Query(None, description="Filter by service vertical")):
    """Returns prioritized list of quantified opportunity areas ranked by RICE score."""
    opps = db.get_opportunities()
    if vertical and vertical.lower() != "all":
        opps = [o for o in opps if o.vertical.value.lower() == vertical.lower()]
    return opps

@router.get("/opportunities/{opp_id}/dossier", response_model=OpportunityArea)
def get_opportunity_dossier(opp_id: str):
    """Returns comprehensive deep-dive dossier for a specific opportunity area."""
    opps = db.get_opportunities()
    for o in opps:
        if o.id.upper() == opp_id.upper():
            return o
    raise HTTPException(status_code=404, detail=f"Opportunity {opp_id} not found")

@router.post("/simulate", response_model=SimulationResponse)
def simulate_scenario(req: SimulationRequest):
    """Models projected NPS and Repeat Rate recovery from operational friction reduction."""
    opps = db.get_opportunities()
    target_opp = next((o for o in opps if o.id.upper() == req.opportunity_id.upper()), None)
    if not target_opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {req.opportunity_id} not found")

    return quantification_engine.simulate_friction_reduction(
        opp=target_opp,
        friction_reduction_pct=req.friction_reduction_percentage
    )

@router.get("/strategy-gap", response_model=List[InvestorClaim])
def get_strategy_gaps():
    """Returns comparison of official Shareholder Claims against live ground-truth review sentiment."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM investor_claims ORDER BY id ASC")
        rows = cursor.fetchall()
        claims = []
        for r in rows:
            claims.append(InvestorClaim(
                id=r["id"],
                document_title=r["document_title"],
                claim_quote=r["claim_quote"],
                category=r["category"],
                target_metric=r["target_metric"],
                ground_truth_rating=r["ground_truth_rating"],
                ground_truth_verdict=r["ground_truth_verdict"],
                evidence_summary=r["evidence_summary"]
            ))
        return claims

@router.get("/feed", response_model=List[FeedbackItem])
def get_feedback_feed(
    vertical: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None),
    max_rating: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Faceted search for raw & normalized customer reviews with source attribution."""
    return db.get_feedback_items(
        vertical=vertical,
        source=source,
        city=city,
        min_rating=min_rating,
        max_rating=max_rating,
        limit=limit,
        offset=offset
    )

@router.post("/copilot/chat")
def chat_with_copilot(req: ChatRequest):
    """Conversational analytics copilot that answers questions with citations."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return copilot_service.answer_query(req.query)

@router.get("/discovery/search")
def discovery_search(q: str = Query(..., description="User feedback discovery query")):
    """Direct search endpoint for user feedback exploration questions."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return copilot_service.answer_query(q)

@router.get("/export/csv")
def export_feedback_csv(q: Optional[str] = Query(None, description="Optional search query to export")):
    """
    Exports data in UTF-8 BOM CSV format compatible with:
    - Microsoft Excel
    - Google Sheets
    - Apple Mac Numbers
    """
    if q and q.strip():
        csv_bytes = export_service.export_search_results_csv(q.strip())
        safe_q = "".join(c for c in q.strip()[:20] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"UrbanCompany_Behavior_{safe_q}.csv"
    else:
        csv_bytes = export_service.export_all_feedback_csv()
        filename = "UrbanCompany_Feedback_Corpus.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )

