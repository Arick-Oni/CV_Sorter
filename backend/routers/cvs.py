import threading

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import CV, Project
from ..schemas import CVSummary, CVDetail, ExtractRequest, ClassifyRequest, RankRequest, AssignProjectRequest
from ..services import ocr as ocr_service
from ..services import ner as ner_service
from ..services import ranking as ranking_service
from ..services import llm_ranking as llm_ranking_service
from ..services import rank_jobs

router = APIRouter(prefix="/cvs", tags=["CVs"])

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf", "docx"}
IMAGE_EXTENSIONS   = {"png", "jpg", "jpeg", "webp"}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _resolve_project(db: Session, project_id: Optional[int], new_project_name: Optional[str]) -> Optional[int]:
    """Assign to an existing project, create-and-assign a new one, or leave unassigned (None)."""
    if new_project_name and new_project_name.strip():
        name = new_project_name.strip()
        project = db.query(Project).filter(Project.name == name).first()
        if not project:
            project = Project(name=name)
            db.add(project)
            db.commit()
            db.refresh(project)
        return project.id
    if project_id:
        if not db.get(Project, project_id):
            raise HTTPException(400, f"Project {project_id} not found")
        return project_id
    return None


def _extract_text(file_bytes: bytes, ext: str, filename: str, method: str, ollama_url: Optional[str]) -> tuple[str, str]:
    """Route to the right extractor. Returns (raw_text, method_label)."""
    if ext == "docx":
        return ocr_service.extract_docx(file_bytes), "python-docx"
    if ext == "pdf":
        return ocr_service.extract_pdf(file_bytes), "pymupdf"
    if method == "minicpm-v":
        return ocr_service.extract_minicpm(file_bytes, ollama_url), "minicpm-v"
    return ocr_service.extract_easyocr(file_bytes, filename), "easyocr"


# ── Upload ────────────────────────────────────────────────────────────────────
@router.post("/upload", response_model=CVDetail, status_code=201)
async def upload_cv(
    file: UploadFile = File(...),
    extraction_method: str = Form(...),        # "easyocr" or "minicpm-v"
    ollama_url: Optional[str] = Form(None),    # required when minicpm-v
    project_id: Optional[int] = Form(None),         # assign to an existing project
    new_project_name: Optional[str] = Form(None),    # or create-and-assign a new one
    db: Session = Depends(get_db),
):
    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")
    if extraction_method == "minicpm-v" and not ollama_url and ext in IMAGE_EXTENSIONS:
        raise HTTPException(400, "ollama_url is required when using minicpm-v")

    resolved_project_id = _resolve_project(db, project_id, new_project_name)
    original_bytes = await file.read()

    # Text extraction always uses the original bytes/format
    raw_text, used_method = _extract_text(original_bytes, ext, file.filename, extraction_method, ollama_url)

    # For DOCX: try converting to PDF so the browser can preview it
    stored_bytes = original_bytes
    stored_ext   = ext
    if ext == "docx":
        pdf_bytes = ocr_service.convert_docx_to_pdf(original_bytes)
        if pdf_bytes:
            stored_bytes = pdf_bytes
            stored_ext   = "pdf"

    # Run NER on all three approaches
    nlp1 = ner_service.get_model1()
    nlp2 = ner_service.get_model2()
    ner1 = ner_service.run_ner(raw_text, nlp1)
    ner2 = ner_service.run_ner(raw_text, nlp2)
    merged = ner_service.merge_ner(ner1, ner2)
    skills_ner = ner_service.run_skills_ner(raw_text)

    cv = CV(
        filename=file.filename,
        file_type=stored_ext,
        file_data=stored_bytes,
        extraction_method=used_method,
        raw_text=raw_text,
        ner_model1=ner1,
        ner_model2=ner2,
        ner_merged=merged,
        ner_skills=skills_ner,
        status="classified",
        project_id=resolved_project_id,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


# ── List all ──────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[CVSummary])
def list_cvs(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(CV)
    if project_id is not None:
        query = query.filter(CV.project_id == project_id)
    return query.order_by(CV.uploaded_at.desc()).all()


# ── JD ranking (before /{cv_id} to avoid route conflict) ─────────────────────
def _jd_ner_for_method(jd_text: str, method: str) -> dict:
    """Compute the JD's NER using whichever model backs the given rank method
    (model1/model2 for their [_hybrid] variants; merged model1+model2 for tfidf)."""
    if method in ("model1", "model1_hybrid"):
        return ner_service.run_ner(jd_text, ner_service.get_model1())
    if method in ("model2", "model2_hybrid"):
        return ner_service.run_ner(jd_text, ner_service.get_model2())
    ner1 = ner_service.run_ner(jd_text, ner_service.get_model1())
    ner2 = ner_service.run_ner(jd_text, ner_service.get_model2())
    return ner_service.merge_ner(ner1, ner2)


@router.post("/rank")
def rank_by_jd(body: RankRequest, db: Session = Depends(get_db)):
    if body.method == "llm":
        raise HTTPException(400, "method=llm runs as a background job — use POST /cvs/rank/llm/start instead")

    query = db.query(CV).filter(CV.raw_text.isnot(None))
    if body.project_id is not None:
        query = query.filter(CV.project_id == body.project_id)
    cvs = query.all()
    if not cvs:
        return {"method": body.method, "jd_ner": {}, "results": []}

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
            "ner_model1": cv.ner_model1 or {},
            "ner_model2": cv.ner_model2 or {},
            "ner_merged": cv.ner_merged or {},
        })

    ranked = ranking_service.rank_cvs(body.jd_text, cv_dicts, method=body.method)
    jd_ner = _jd_ner_for_method(body.jd_text, body.method)
    return {"method": body.method, "jd_ner": jd_ner, "results": ranked[:body.top_n]}


# ── LLM Judge ranking (background job, polled for live progress) ────────────
def _run_llm_ranking_job(job_id: str, cv_dicts: list[dict], jd_text: str,
                          ollama_url: str, llm_model: str, top_n: int) -> None:
    try:
        rank_jobs.update_job(job_id, phase="rubric")
        rubric = llm_ranking_service.build_rubric(jd_text, ollama_url, llm_model)
        rank_jobs.update_job(job_id, phase="scoring", rubric=rubric)

        for cv in cv_dicts:
            rank_jobs.update_job(job_id, current_filename=cv["filename"])
            # One bad CV (tunnel blip, slow model, malformed response) shouldn't lose
            # every other CV's score in this batch — record it as a failed 0 and move on.
            try:
                outcome = llm_ranking_service.score_cv(rubric, cv["raw_text"], ollama_url, llm_model)
            except Exception as e:
                outcome = {"score": 0.0, "justification": f"LLM call failed: {e}"}
            rank_jobs.append_result(job_id, {
                "id": cv["id"],
                "filename": cv["filename"],
                "name": cv["name"],
                "email": cv["email"],
                "skills": cv["skills"],
                "match_score": round(outcome["score"], 2),
                "llm_justification": outcome["justification"],
            })

        rank_jobs.finish_job(job_id, top_n)
    except Exception as e:
        rank_jobs.fail_job(job_id, str(e))


@router.post("/rank/llm/start")
def start_llm_rank(body: RankRequest, db: Session = Depends(get_db)):
    if not body.ollama_url:
        raise HTTPException(400, "ollama_url is required for method=llm")
    if not body.llm_model:
        raise HTTPException(400, "llm_model is required for method=llm")

    query = db.query(CV).filter(CV.raw_text.isnot(None))
    if body.project_id is not None:
        query = query.filter(CV.project_id == body.project_id)
    cvs = query.all()

    # Pull everything the background thread needs out of the ORM objects now,
    # while the request's DB session is still open — the thread outlives this
    # request/session, so touching lazy-loaded CV attributes from it would
    # otherwise risk a DetachedInstanceError.
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

    job_id = rank_jobs.create_job(total=len(cv_dicts))
    threading.Thread(
        target=_run_llm_ranking_job,
        args=(job_id, cv_dicts, body.jd_text, body.ollama_url, body.llm_model, body.top_n),
        daemon=True,
    ).start()
    return {"job_id": job_id}


@router.get("/rank/llm/{job_id}")
def get_llm_rank_status(job_id: str):
    job = rank_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


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
    mime_map = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    media_type = mime_map.get(cv.file_type, "application/octet-stream")
    return Response(content=cv.file_data, media_type=media_type,
                    headers={"Content-Disposition": f'inline; filename="{cv.filename}"'})


# ── Extract text from a JD file (no DB storage) ──────────────────────────────
@router.post("/jd-extract")
async def extract_jd(file: UploadFile = File(...)):
    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")
    file_bytes = await file.read()
    text, _ = _extract_text(file_bytes, ext, file.filename, "easyocr", None)
    return {"text": text}


# ── Re-extract text ───────────────────────────────────────────────────────────
@router.post("/{cv_id}/extract", response_model=CVDetail)
def re_extract(cv_id: int, body: ExtractRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    if body.method == "minicpm-v" and not body.ollama_url and cv.file_type in IMAGE_EXTENSIONS:
        raise HTTPException(400, "ollama_url required for minicpm-v")

    cv.raw_text, cv.extraction_method = _extract_text(cv.file_data, cv.file_type, cv.filename, body.method, body.ollama_url)
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


# ── Assign / move to a project ────────────────────────────────────────────────
@router.post("/{cv_id}/project", response_model=CVDetail)
def assign_project(cv_id: int, body: AssignProjectRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    cv.project_id = _resolve_project(db, body.project_id, body.new_project_name)
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
