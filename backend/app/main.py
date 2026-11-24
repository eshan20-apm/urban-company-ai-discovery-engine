from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade AI Opportunity Discovery & Metric Quantification Engine for Urban Company.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Vercel Serverless Path Rewrite Middleware
@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    # When deployed on Vercel, requests rewritten to /api/index.py carry the real path in x-matched-path or path query param
    matched_path = (
        request.headers.get("x-matched-path")
        or request.headers.get("x-vercel-matched-path")
        or request.query_params.get("path")
    )
    current_path = request.scope.get("path", "")
    if matched_path and current_path in ["/api/index.py", "/api"]:
        clean_path = matched_path.split("?")[0]
        request.scope["path"] = clean_path
    elif current_path in ["/api/index.py", "/api"]:
        request.scope["path"] = "/"

    return await call_next(request)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Static file serving for the clean white minimalist dashboard
STATIC_DIR = settings.BASE_DIR.parent / "frontend" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.api_route("/", methods=["GET", "HEAD"])
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return {
        "message": "Urban Company AI Opportunity & Discovery Engine API",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }

@app.api_route("/dashboard", methods=["GET", "HEAD"])
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return {"error": "Dashboard index.html not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
