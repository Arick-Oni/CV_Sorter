from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from sqlalchemy import text
from .database import engine
from .models import Base
from .routers import cvs

Base.metadata.create_all(bind=engine)

# Add ner_skills column if it doesn't exist yet (for DBs created before this column)
with engine.connect() as _conn:
    _conn.execute(text("ALTER TABLE cvs ADD COLUMN IF NOT EXISTS ner_skills JSON"))
    _conn.commit()

app = FastAPI(title="CV Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cvs.router)

# Serve frontend
FRONTEND = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND / "index.html"), media_type="text/html; charset=utf-8")

@app.get("/health")
def health():
    return {"status": "ok"}
