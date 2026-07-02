from sqlalchemy import Column, Integer, String, Text, LargeBinary, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base

class CV(Base):
    __tablename__ = "cvs"

    id               = Column(Integer, primary_key=True, index=True)
    filename         = Column(String, nullable=False)
    file_type        = Column(String, nullable=False)          # png / jpg / pdf
    file_data        = Column(LargeBinary, nullable=False)     # original file bytes
    uploaded_at      = Column(DateTime(timezone=True), server_default=func.now())
    status           = Column(String, default="uploaded")      # uploaded | extracted | classified

    extraction_method = Column(String)                         # easyocr | minicpm-v
    raw_text          = Column(Text)

    ner_model1  = Column(JSON)   # model-best results
    ner_model2  = Column(JSON)   # model-best-2 results
    ner_merged  = Column(JSON)   # per-label best merged result
    ner_skills  = Column(JSON)   # en_core_web_sm + EntityRuler (skills.jsonl)
