import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import CV
from ..schemas import CVSummary, CVDetail, ExtractRequest, ClassifyRequest, RankRequest
from ..services import ocr as ocr_service
from ..services import ner as ner_service
from ..services import ranking as ranking_service

router = APIRouter(prefix="/cvs", tags=["CVs"])

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf", "docx"}
IMAGE_EXTENSIONS   = {"png", "jpg", "jpeg", "webp"}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _extract_text(file_bytes: bytes, filename: str, method: str, ollama_url: Optional[str]) -> str:
    """Route to the right extractor based on file extension."""
    ext = _ext(filename)
    if ext == "docx":
        return ocr_service.extract_docx(file_bytes)
    if ext == "pdf":
        return ocr_service.extract_pdf(file_bytes)
    # Image — use selected OCR method
    if method == "minicpm-v":
        return ocr_service.extract_minicpm(file_bytes, ollama_url)
    return ocr_service.extract_easyocr(file_bytes, filename)


# ── Upload ────────────────────────────────────────────────────────────────────
@router.post("/upload", response_model=CVDetail, status_code=201)
async def upload_cv(
    file: UploadFile = File(...),
    extraction_method: str = Form(...),        # "easyocr" or "minicpm-v"
    ollama_url: Optional[str] = Form(None),    # required when minicpm-v
    db: Session = Depends(get_db),
):
    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")
    if extraction_method == "minicpm-v" and not ollama_url and ext in IMAGE_EXTENSIONS:
        raise HTTPException(400, "ollama_url is required when using minicpm-v")

    file_bytes = await file.read()

    # Extract text
    raw_text = _extract_text(file_bytes, file.filename, extraction_method, ollama_url)

    # Run NER on all three approaches
    nlp1 = ner_service.get_model1()
    nlp2 = ner_service.get_model2()
    ner1 = ner_service.run_ner(raw_text, nlp1)
    ner2 = ner_service.run_ner(raw_text, nlp2)
    merged = ner_service.merge_ner(ner1, ner2)
    skills_ner = ner_service.run_skills_ner(raw_text)

    cv = CV(
        filename=file.filename,
        file_type=ext,
        file_data=file_bytes,
        extraction_method=extraction_method,
        raw_text=raw_text,
        ner_model1=ner1,
        ner_model2=ner2,
        ner_merged=merged,
        ner_skills=skills_ner,
        status="classified",
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


# ── List all ──────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[CVSummary])
def list_cvs(db: Session = Depends(get_db)):
    return db.query(CV).order_by(CV.uploaded_at.desc()).all()


# ── JD ranking (before /{cv_id} to avoid route conflict) ─────────────────────
@router.post("/rank")
def rank_by_jd(body: RankRequest, db: Session = Depends(get_db)):
    cvs = db.query(CV).filter(CV.raw_text.isnot(None)).all()
    if not cvs:
        return []

    cv_dicts = []
    for cv in cvs:
        skills_data = cv.ner_skills or {}
        cv_dicts.append({
            "id": cv.id,
            "filename": cv.filename,
            "raw_text": cv.raw_text,
            "name": (skills_data.get("NAME") or ["Unknown"])[0],
            "email": (skills_data.get("EMAIL") or ["Unknown"])[0],
            "skills": skills_data.get("SKILLS") or [],
        })

    ranked = ranking_service.rank_cvs(body.jd_text, cv_dicts)
    return ranked[:body.top_n]


# ── Get single ────────────────────────────────────────────────────────────────
@router.get("/{cv_id}", response_model=CVDetail)
def get_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    return cv


# ── Download original file ────────────────────────────────────────────────────
@router.get("/{cv_id}/file")
def download_cv_file(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    media_type = f"image/{cv.file_type}" if cv.file_type != "pdf" else "application/pdf"
    return Response(content=cv.file_data, media_type=media_type,
                    headers={"Content-Disposition": f'inline; filename="{cv.filename}"'})


# ── Extract text from a JD file (no DB storage) ──────────────────────────────
@router.post("/jd-extract")
async def extract_jd(file: UploadFile = File(...)):
    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")
    file_bytes = await file.read()
    text = _extract_text(file_bytes, file.filename, "easyocr", None)
    return {"text": text}


# ── Re-extract text ───────────────────────────────────────────────────────────
@router.post("/{cv_id}/extract", response_model=CVDetail)
def re_extract(cv_id: int, body: ExtractRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    if body.method == "minicpm-v" and not body.ollama_url and _ext(cv.filename) in IMAGE_EXTENSIONS:
        raise HTTPException(400, "ollama_url required for minicpm-v")

    cv.raw_text = _extract_text(cv.file_data, cv.filename, body.method, body.ollama_url)
    cv.extraction_method = body.method
    cv.status = "extracted"
    db.commit()
    db.refresh(cv)
    return cv


# ── Re-classify ───────────────────────────────────────────────────────────────
@router.post("/{cv_id}/classify", response_model=CVDetail)
def classify(cv_id: int, body: ClassifyRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    if not cv.raw_text:
        raise HTTPException(400, "Extract text first before classifying")

    if body.model in ("model1", "both"):
        cv.ner_model1 = ner_service.run_ner(cv.raw_text, ner_service.get_model1())
    if body.model in ("model2", "both"):
        cv.ner_model2 = ner_service.run_ner(cv.raw_text, ner_service.get_model2())
    if body.model in ("skills", "both"):
        cv.ner_skills = ner_service.run_skills_ner(cv.raw_text)
    if cv.ner_model1 and cv.ner_model2:
        cv.ner_merged = ner_service.merge_ner(cv.ner_model1, cv.ner_model2)

    cv.status = "classified"
    db.commit()
    db.refresh(cv)
    return cv


# ── Delete ────────────────────────────────────────────────────────────────────
@router.delete("/{cv_id}", status_code=204)
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    db.delete(cv)
    db.commit()
