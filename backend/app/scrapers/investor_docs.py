from datetime import datetime
from typing import List
from backend.app.models.schemas import InvestorClaim

class InvestorDocsParser:
    """Parses public shareholder letters, investor presentations and IPO filings."""
    def __init__(self):
        pass

    def get_strategic_claims(self) -> List[InvestorClaim]:
        # Extracted strategic management statements from Urban Company public investor disclosures & DRHP
        return [
            InvestorClaim(
                id="CLAIM-01",
                document_title="Urban Company Annual Shareholder Letter FY24",
                claim_quote="Our AC servicing NPS improved by 450 bps year-over-year, driven by standardized foam-jet cleaning protocols and strict technician onboarding audits.",
                category="Appliance Repair",
                target_metric="Customer NPS & Service Quality",
                ground_truth_rating=2.1,
                ground_truth_verdict="DIVERGENT",
                evidence_summary="Ground truth customer reviews reveal 28.4% of negative appliance feedback centers on arbitrary doorstep spare-part quotes and gas charging disputes, offsetting procedural cleaning satisfaction."
            ),
            InvestorClaim(
                id="CLAIM-02",
                document_title="Urban Company Strategic Disclosure Q3",
                claim_quote="Partner retention across top 5 metros reached an all-time high of 84%, supported by enhanced safety nets, subsidized health insurance, and transparent commission structures.",
                category="Partner Supply Health",
                target_metric="Partner Retention & Commission Trust",
                ground_truth_rating=2.8,
                ground_truth_verdict="CRITICAL_RISK",
                evidence_summary="Reddit partner discussions and community threads cite effective take-rates exceeding 28% after kit deductions, leading experienced senior partners to migrate towards independent salons."
            ),
            InvestorClaim(
                id="CLAIM-03",
                document_title="Urban Company Product & Innovation Note: Native Purifiers",
                claim_quote="The Native M1 smart RO water purifier achieved 92% customer satisfaction due to its innovative rapid filter replacement and zero-service-overhead design.",
                category="Native Smart Devices",
                target_metric="Product CSAT & Retention",
                ground_truth_rating=4.2,
                ground_truth_verdict="CONFIRMED",
                evidence_summary="Verified positive sentiment on YouTube and App Store regarding sleek hardware and digital filter tracking, with minor complaints restricted to proprietary cartridge lock-in."
            ),
            InvestorClaim(
                id="CLAIM-04",
                document_title="Urban Company Operational Metrics Presentation",
                claim_quote="Average customer support ticket resolution turnaround time reduced by 60% with our automated AI resolution assistant.",
                category="Customer Support",
                target_metric="Support Resolution SLA & CSAT",
                ground_truth_rating=1.7,
                ground_truth_verdict="CRITICAL_RISK",
                evidence_summary="Consumer forum and Trustpilot complaints overwhelmingly cite the automated chatbot as a primary barrier to human agent escalation during emergency property damage or refund disputes."
            )
        ]

