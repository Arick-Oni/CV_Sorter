from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CVSummary(BaseModel):
    id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    status: str
    extraction_method: Optional[str]

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

class RankRequest(BaseModel):
    jd_text: str
    top_n: int = 20
