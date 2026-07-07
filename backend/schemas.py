from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

class ProjectCreate(BaseModel):
    name: str

class CVSummary(BaseModel):
    id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    status: str
    extraction_method: Optional[str]
    project_id: Optional[int]

    model_config = {"from_attributes": True}

class CVDetail(CVSummary):
    raw_text: Optional[str]
    ner_model1: Optional[dict]
    ner_model2: Optional[dict]
    ner_merged: Optional[dict]
    ner_skills: Optional[dict]

class ExtractRequest(BaseModel):
    method: str           # "easyocr" or "minicpm-v"
    ollama_url: Optional[str] = None   # required when method=minicpm-v

class ClassifyRequest(BaseModel):
    model: str            # "model1", "model2", "skills", or "both"

class AssignProjectRequest(BaseModel):
    project_id: Optional[int] = None       # None = unassign (global only)
    new_project_name: Optional[str] = None # create-and-assign a new one

class RankRequest(BaseModel):
    jd_text: str
    top_n: int = 20
    method: str = "tfidf"   # "tfidf", "model1", "model2", "model1_hybrid", "model2_hybrid", or "llm"
    project_id: Optional[int] = None   # None = all projects (global)
    llm_model: Optional[str] = None    # required when method="llm" — Ollama model tag
    ollama_url: Optional[str] = None   # required when method="llm" — tunnel URL to the Ollama server
