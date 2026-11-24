from typing import List, Optional
from backend.app.models.schemas import CausalChain, ServiceVertical

class CausalChainExtractor:
    """Extracts causal event triples: [Friction Trigger] -> [Customer Reaction] -> [Business Metric Drag]."""

    def extract_causal_chain(self, text: str, vertical: ServiceVertical, aspects: List[str]) -> Optional[CausalChain]:
        t = text.lower()

        # 1. Appliance Repair & Pricing Disputes
        if "pricing & transparency" in [a.lower() for a in aspects] and vertical == ServiceVertical.APPLIANCE_REPAIR:
            if any(w in t for w in ["gas", "extra", "3000", "2500", "motherboard", "pcb", "cash"]):
                return CausalChain(
                    friction_trigger="Technician verbally quoted arbitrary add-on pricing (gas recharge / motherboard replacement) without standard app rate card",
                    customer_reaction="Refused doorstep repair, disputed charges with customer care, uninstalled app",
                    metric_impact="Severe 90-day repeat booking churn and local vendor defection"
                )

        # 2. Punctuality & Scheduling in Metros
        if "punctuality & reliability" in [a.lower() for a in aspects]:
            if any(w in t for w in ["late", "delay", "waiting", "cancel", "rain"]):
                return CausalChain(
                    friction_trigger="Partner delayed >45 minutes during peak evening hours or sudden weather disruption with no real-time notification",
                    customer_reaction="Cancelled doorstep appointment, hired offline local technician, left 1-star rage rating",
                    metric_impact="Same-day booking GMV leakage and negative word-of-mouth drag on NPS"
                )

        # 3. Customer Support & Warranty Re-work Disputes
        if "customer support & refunds" in [a.lower() for a in aspects]:
            if any(w in t for w in ["refund", "warranty", "consumer court", "bot", "ticket"]):
                return CausalChain(
                    friction_trigger="Warranty re-work failure or property damage claim stalled by automated chatbot loops without human escalation",
                    customer_reaction="Escalated complaint to National Consumer Helpline (NCH) or public grievance forums",
                    metric_impact="High legal escalation cost and lasting brand equity erosion"
                )

        # 4. UC Plus & Subscription Transparency
        if "app ux & uc plus" in [a.lower() for a in aspects]:
            if any(w in t for w in ["plus", "auto-debit", "renew", "discount cap"]):
                return CausalChain(
                    friction_trigger="Surprise annual membership renewal auto-debit or disillusionment with discount caps below expectation",
                    customer_reaction="Disputed transaction with bank, cancelled membership, vented on Reddit",
                    metric_impact="Voluntary churn in highest-spending premium iOS customer tier"
                )

        # 5. Salon & Hygiene Standards
        if vertical == ServiceVertical.SALON_SPA and any(w in t for w in ["wax", "cleanup", "hair", "carpet", "dirty"]):
            return CausalChain(
                friction_trigger="Beautician left wax or hair residue on floors/furniture following in-home service",
                customer_reaction="Downgraded rating from 5 to 3 stars, refused to rebook home salon for subsequent cycle",
                metric_impact="15% drop in 60-day repeat booking retention for women's salon"
            )

        # Default fallback causal chain
        if any(w in t for w in ["bad", "worst", "cheat", "scam", "waste"]):
            return CausalChain(
                friction_trigger="Mismatch between expected service standard and physical doorstep execution",
                customer_reaction="Expressed acute dissatisfaction and reluctance to re-engage platform",
                metric_impact="NPS drag and lowered lifetime booking frequency"
            )

        return None

causal_extractor = CausalChainExtractor()

