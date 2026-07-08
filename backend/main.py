from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from sqlalchemy import text
from .database import engine
from .models import Base
from .routers import cvs, projects

Base.metadata.create_all(bind=engine)

# Add columns that didn't exist in DBs created before this feature was added
with engine.connect() as _conn:
    _conn.execute(text("ALTER TABLE cvs ADD COLUMN IF NOT EXISTS ner_skills JSON"))
    _conn.execute(text("ALTER TABLE cvs ADD COLUMN IF NOT EXISTS project_id INTEGER"))
    _conn.execute(text("ALTER TABLE cvs ADD COLUMN IF NOT EXISTS years_of_experience REAL"))
    _conn.execute(text("ALTER TABLE cvs ADD COLUMN IF NOT EXISTS seniority_level VARCHAR"))
    _conn.execute(text("ALTER TABLE match_history ADD COLUMN IF NOT EXISTS rubric TEXT"))
    _conn.commit()

app = FastAPI(title="CV Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cvs.router)
app.include_router(projects.router)

# Serve frontend
FRONTEND = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

@app.middleware("http")
async def no_cache_static(request, call_next):
    """Dev app, frontend files change often — never let the browser cache them stale."""
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND / "index.html"), media_type="text/html; charset=utf-8")

@app.get("/health")
def health():
    return {"status": "ok"}
