# Urban Company AI Opportunity & Discovery Engine
> An enterprise-grade customer intelligence and business metric quantification system that analyzes multi-channel public feedback at scale.

---

## 🌟 Overview & Core Philosophy

The **Urban Company AI Opportunity & Discovery Engine** transitions beyond traditional sentiment classification. Instead of outputting generic sentiment labels, it discovers **systemic operational friction points**, quantifies their empirical drag on core business metrics (NPS, Churn Elasticity, Customer LTV, Support Escalations), and enables interactive **"What-If" sensitivity simulations** for leadership.

### Key Differentiators:
- **Zero-Intrusion Compliance**: Ingests exclusively from permitted public endpoints (Google Play Store, Apple App Store, Indian Subreddits, Trustpilot, Consumer Complaints Forums, YouTube comments, and public Shareholder Letters). Zero private app or authenticated session scraping.
- **Hinglish & Vernacular Normalizer**: Translates code-mixed Indian idioms (e.g., *"AC cooling nahi kar raha tha, technician bola gas leak hai"*) into normalized English while preserving emotional intensity.
- **Causal Event Extraction**: Breaks feedback into causal event triples: `[Friction Trigger] -> [Customer Reaction] -> [Business Metric Drag]`.
- **RICE & Empirical Quantification**: Calculates Volume Reach ($R_i$), NPS Drag ($S_i$), Churn Elasticity ($C_i$), and Estimated Annual Revenue Leakage ($L_i$).
- **Dynamic "What-If" Sensitivity Simulator**: Models projected $\Delta\text{NPS}$ and $\Delta\text{Repeat Rate}$ from operational interventions.
- **Pure White Minimalist UI**: High-density, distraction-free executive dashboard with interactive 2x2 matrix, deep-dive dossiers, and conversational AI Copilot.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ (Virtual environment included in `backend/.venv`)

### 2. Launch the Application
Run the unified FastAPI server:
```bash
PYTHONPATH=. backend/.venv/bin/python backend/app/main.py
```

Open your browser to explore:
- **Clean White Executive Dashboard**: [http://localhost:8000/](http://localhost:8000/) or [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc View**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Run Automated Tests
```bash
PYTHONPATH=. backend/.venv/bin/pytest -v backend/tests/
```
*(18 unit and integration tests covering scrapers, PII redaction, Hinglish normalizer, causal extraction, simulation math, and REST endpoints).*

---

## 📊 Discovered Opportunity Areas (Initial Ingestion)

| ID | Opportunity Area | Vertical | Business Metric Impact | RICE Score | Est. Annual Revenue Leakage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OPP-01** | Standardized Pre-service Diagnostics | Appliance Repair | Retention & 90-Day Repeat Rate | **142.5** | ₹3.2M / cohort |
| **OPP-02** | Dynamic Rain & Traffic Arrival Buffer | Cleaning | Punctuality & Same-Day Cancellations | **135.2** | ₹2.4M / cohort |
| **OPP-03** | Transparent Warranty Claim Ownership | Support / General | Support Cost & Escalation Rate | **118.4** | ₹4.8M / cohort |
| **OPP-04** | UC Plus Subscription Transparency | General / iOS | UC Plus Churn & High-AOV LTV | **112.0** | ₹1.9M / cohort |
| **OPP-05** | Post-Salon Sanitation & Cleanup | Salon & Spa | Women's Salon 60-Day Repeat Rate | **98.6** | ₹1.2M / cohort |

---

## 📡 REST API Reference

- `GET /api/v1/metrics/executive`: Returns platform NPS Proxy, Churn Risk %, ARR at risk, and total ingested items.
- `GET /api/v1/opportunities`: Returns filterable list of opportunity areas ranked by RICE score.
- `GET /api/v1/opportunities/{id}/dossier`: Returns full deep-dive dossier (causal flows, verbatim evidence, recommended actions).
- `POST /api/v1/simulate`: Models $\Delta\text{NPS}$ and $\Delta\text{Repeat Rate}$ for a given percentage reduction in operational friction.
- `GET /api/v1/strategy-gap`: Compares official shareholder letter claims against on-the-ground review ratings.
- `GET /api/v1/feed`: Faceted review search with filters for vertical, source, city, rating, and Hinglish flags.
- `GET /api/v1/discovery/search?q=...`: Live query search across public channels with honest data-gap detection.
- `GET /api/v1/export/csv`: Cross-platform CSV download (UTF-8 BOM `\ufeff`) compatible with Google Sheets, Microsoft Excel (Windows & macOS), and Apple Mac Numbers. Supports exporting the entire corpus or query-filtered search results (`?q=...`).
- `POST /api/v1/copilot/chat`: Conversational RAG assistant grounded in the feedback corpus with cited quotes.

---

## 📁 Project Structure

```
AI discovery engine/
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI REST route handlers
│   │   ├── core/               # Configuration & settings
│   │   ├── db/                 # SQLite WAL database & schema
│   │   ├── intelligence/       # PII Redactor, Hinglish engine, Causal & Math core
│   │   ├── models/             # Pydantic v2 schemas
│   │   ├── scrapers/           # Permitted multi-channel public scrapers
│   │   ├── services/           # RAG Copilot service
│   │   └── main.py             # Server entrypoint
│   ├── tests/                  # 18 passing pytest test suites
│   └── requirements.txt
├── frontend/
│   ├── static/
│   │   └── index.html          # Clean white minimalist dashboard
│   ├── package.json            # Next.js 14 configuration
│   └── tailwind.config.js
├── data/
│   ├── raw/                    # Raw ingested snapshots
│   ├── processed/              # Normalized datasets
│   └── investor_reports/       # Shareholder PDF documents
├── SYSTEM_PLAN.md              # High-level strategic blueprint
├── DETAILED_ARCHITECTURE.md    # In-depth architectural & mathematical specification
└── PHASE_WISE_IMPLEMENTATION_PLAN.md
```

