import threading
import queue
import concurrent.futures

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, SessionLocal
from ..models import CV, Project, MatchHistory
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

    # Estimate experience and seniority
    years, seniority = ner_service.estimate_experience_and_seniority(raw_text)
    exp_val = [f"{years} yrs" if years > 0 else "0 yrs"]
    sen_val = [seniority]

    if "YEARS_OF_EXPERIENCE" not in ner1:
        ner1["YEARS_OF_EXPERIENCE"] = exp_val
    if "SENIORITY_LEVEL" not in ner1:
        ner1["SENIORITY_LEVEL"] = sen_val

    if "YEARS_OF_EXPERIENCE" not in ner2:
        ner2["YEARS_OF_EXPERIENCE"] = exp_val
    if "SENIORITY_LEVEL" not in ner2:
        ner2["SENIORITY_LEVEL"] = sen_val

    if "YEARS_OF_EXPERIENCE" not in merged:
        merged["YEARS_OF_EXPERIENCE"] = exp_val
    if "SENIORITY_LEVEL" not in merged:
        merged["SENIORITY_LEVEL"] = sen_val

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
        years_of_experience=years,
        seniority_level=seniority,
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
    if body.method.startswith("llm"):
        raise HTTPException(400, f"method={body.method} runs as a background job — use POST /cvs/rank/llm/start instead")

    query = db.query(CV).filter(CV.raw_text.isnot(None))
    if body.project_id is not None:
        query = query.filter(CV.project_id == body.project_id)
    cvs = query.all()
    if not cvs:
        # Save empty history run to maintain log
        history = MatchHistory(
            project_id=body.project_id,
            jd_text=body.jd_text,
            method=body.method,
            results=[]
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return {"id": history.id, "method": body.method, "jd_ner": {}, "results": []}

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
            "years_of_experience": cv.years_of_experience,
            "seniority_level": cv.seniority_level,
        })

    ranked = ranking_service.rank_cvs(body.jd_text, cv_dicts, method=body.method)
    jd_ner = _jd_ner_for_method(body.jd_text, body.method)

    # Save to search history
    # Keep result records lightweight by omitting raw texts or details
    saved_results = []
    for r in ranked:
        saved_results.append({
            "id": r["id"],
            "filename": r["filename"],
            "name": r.get("name"),
            "email": r.get("email"),
            "skills": r.get("skills"),
            "match_score": r["match_score"],
            "embedding_score": r.get("embedding_score"),
            "keyword_score": r.get("keyword_score"),
            "years_of_experience": r.get("years_of_experience"),
            "seniority_level": r.get("seniority_level"),
        })

    history = MatchHistory(
        project_id=body.project_id,
        jd_text=body.jd_text,
        method=body.method,
        results=saved_results
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {"id": history.id, "method": body.method, "jd_ner": jd_ner, "results": ranked}


# ── LLM Judge ranking (background job, polled for live progress) ────────────
def _run_llm_ranking_job(job_id: str, cv_dicts: list[dict], jd_text: str,
                          ollama_url: str, llm_model: str, top_n: int, method: str, project_id: Optional[int] = None) -> None:
    try:
        # Split ollama_url on commas to support multiple concurrent tunnels
        urls = [u.strip() for u in ollama_url.split(",") if u.strip()]
        if not urls:
            urls = [ollama_url]
            
        tunnel_queue = queue.Queue()
        for url in urls:
            tunnel_queue.put(url)
            
        if method == "llm_multilayer":
            # --- STAGE 1: SOFT FILTERING (Parallel) ---
            if rank_jobs.get_job(job_id).get("status") == "cancelled":
                return
            rank_jobs.update_job(job_id, phase="filtering", completed=0, total=len(cv_dicts))
            relevant_candidates = []
            filtered_out_results = []
            completed_count = 0
            
            def filter_worker(cv):
                nonlocal completed_count
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return cv, False
                url = tunnel_queue.get()
                rank_jobs.update_tunnel_activity(job_id, url, f"Filtering: {cv['filename']}")
                rank_jobs.update_job(job_id, current_filename=cv["filename"])
                try:
                    is_rel = llm_ranking_service.filter_candidate(
                        jd_text, cv["raw_text"], url, llm_model
                    )
                except Exception:
                    is_rel = True  # Fallback to True on error
                finally:
                    rank_jobs.update_tunnel_activity(job_id, url, None)
                    tunnel_queue.put(url)
                    tunnel_queue.task_done()
                return cv, is_rel
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as executor:
                futures = {executor.submit(filter_worker, cv): cv for cv in cv_dicts}
                for fut in concurrent.futures.as_completed(futures):
                    if rank_jobs.get_job(job_id).get("status") == "cancelled":
                        return
                    cv, is_rel = fut.result()
                    completed_count += 1
                    if is_rel:
                        relevant_candidates.append(cv)
                    else:
                        filtered_out_results.append({
                            "id": cv["id"],
                            "filename": cv["filename"],
                            "name": cv["name"],
                            "email": cv["email"],
                            "skills": cv["skills"],
                            "match_score": 0.0,
                            "llm_justification": "Filtered out in Stage 1: Marked as not relevant to the Job Description.",
                            "years_of_experience": cv.get("years_of_experience"),
                            "seniority_level": cv.get("seniority_level"),
                        })
                    rank_jobs.update_job(job_id, completed=completed_count)

            # --- STAGE 2: BATCH SCORING (groups of 3) (Parallel) ---
            if rank_jobs.get_job(job_id).get("status") == "cancelled":
                return
            stage2_scored_candidates = []
            batches = [relevant_candidates[i:i+3] for i in range(0, len(relevant_candidates), 3)]
            rank_jobs.update_job(job_id, phase="batch_scoring", completed=0, total=len(relevant_candidates))
            processed_relevant = 0
            
            def batch_scoring_worker(batch):
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return batch, []
                url = tunnel_queue.get()
                filenames_str = ", ".join([c["filename"] for c in batch])
                rank_jobs.update_tunnel_activity(job_id, url, f"Scoring batch: {filenames_str}")
                rank_jobs.update_job(job_id, current_filename=filenames_str)
                try:
                    scores_list = llm_ranking_service.score_batch(jd_text, batch, url, llm_model)
                except Exception:
                    scores_list = []
                finally:
                    rank_jobs.update_tunnel_activity(job_id, url, None)
                    tunnel_queue.put(url)
                    tunnel_queue.task_done()
                return batch, scores_list
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as executor:
                futures = {executor.submit(batch_scoring_worker, b): b for b in batches}
                for fut in concurrent.futures.as_completed(futures):
                    if rank_jobs.get_job(job_id).get("status") == "cancelled":
                        return
                    batch, scores_list = fut.result()
                    processed_relevant += len(batch)
                    
                    for cv in batch:
                        match = next((s for s in scores_list if s.get("filename") == cv["filename"]), None)
                        if match:
                            score_val = float(match.get("score", 0.0))
                            just_val = str(match.get("justification", ""))
                        else:
                            score_val = 0.0
                            just_val = "Could not parse batch score for this candidate."
                        
                        stage2_scored_candidates.append({
                            "id": cv["id"],
                            "filename": cv["filename"],
                            "name": cv["name"],
                            "email": cv["email"],
                            "skills": cv["skills"],
                            "raw_text": cv["raw_text"],
                            "previous_score": score_val,
                            "previous_justification": just_val,
                            "match_score": score_val,
                            "llm_justification": just_val,
                            "years_of_experience": cv.get("years_of_experience"),
                            "seniority_level": cv.get("seniority_level"),
                        })
                    rank_jobs.update_job(job_id, completed=processed_relevant)

            # --- STAGE 3: RE-RANKING TOP 10 ---
            if rank_jobs.get_job(job_id).get("status") == "cancelled":
                return
            rank_jobs.update_job(job_id, phase="re_ranking", completed=0, total=1)
            
            stage2_scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
            top_10 = stage2_scored_candidates[:10]
            remaining = stage2_scored_candidates[10:]
            
            if top_10:
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return
                rank_jobs.update_job(job_id, current_filename="Re-ranking top candidates...")
                try:
                    rerank_results = llm_ranking_service.rerank_top_candidates(jd_text, top_10, urls[0], llm_model)
                except Exception:
                    rerank_results = []
                
                for cand in top_10:
                    match = next((r for r in rerank_results if r.get("filename") == cand["filename"]), None)
                    if match:
                        cand["match_score"] = float(match.get("score", cand["match_score"]))
                        cand["llm_justification"] = f"Rank {match.get('rank', '-')}: {match.get('justification', cand['llm_justification'])}"
            
            rank_jobs.update_job(job_id, completed=1)

            # Put all results together
            final_results = top_10 + remaining + filtered_out_results
            final_results.sort(key=lambda x: x["match_score"], reverse=True)
            
            for r in final_results:
                r.pop("raw_text", None)
                r.pop("previous_score", None)
                r.pop("previous_justification", None)

            if rank_jobs.get_job(job_id).get("status") == "cancelled":
                return
                
            rank_jobs.update_job(
                job_id,
                results=final_results,
                completed=len(cv_dicts),
                total=len(cv_dicts)
            )
            rank_jobs.finish_job(job_id, top_n)

            # Save LLM Multilayer results to DB
            db = SessionLocal()
            try:
                history = MatchHistory(
                    project_id=project_id,
                    jd_text=jd_text,
                    method=method,
                    llm_model=llm_model,
                    results=final_results
                )
                db.add(history)
                db.commit()
                db.refresh(history)
                rank_jobs.update_job(job_id, history_id=history.id)
            except Exception as db_err:
                print(f"Error saving match history to DB: {db_err}")
            finally:
                db.close()
        else:
            is_jd = (method == "llm_no_rubric")
            if is_jd:
                rubric_or_jd = jd_text
                rank_jobs.update_job(job_id, phase="scoring", rubric=jd_text)
            else:
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return
                rank_jobs.update_job(job_id, phase="rubric")
                rubric_or_jd = llm_ranking_service.build_rubric(jd_text, urls[0], llm_model)
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return
                rank_jobs.update_job(job_id, phase="scoring", rubric=rubric_or_jd)

            # Precompute TF-IDF and embedding scores if hybrid
            precomputed = {}
            if method == "hybrid":
                # Compute TF-IDF
                tfidf_results = ranking_service.rank_cvs(jd_text, cv_dicts, method="tfidf")
                tfidf_map = {r["id"]: r["match_score"] for r in tfidf_results}
                
                # Compute model-best (model1) embeddings
                model1_results = ranking_service.rank_cvs(jd_text, cv_dicts, method="model1")
                model1_map = {r["id"]: r["match_score"] for r in model1_results}
                
                # Compute model-best2 (model2) embeddings
                model2_results = ranking_service.rank_cvs(jd_text, cv_dicts, method="model2")
                model2_map = {r["id"]: r["match_score"] for r in model2_results}
                
                for cv in cv_dicts:
                    cv_id = cv["id"]
                    precomputed[cv_id] = {
                        "tfidf": tfidf_map.get(cv_id, 0.0),
                        "model1": model1_map.get(cv_id, 0.0),
                        "model2": model2_map.get(cv_id, 0.0),
                    }

            # --- STANDARD LLM EVALUATION (Parallel) ---
            completed_count = 0
            
            def standard_scoring_worker(cv):
                nonlocal completed_count
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return
                url = tunnel_queue.get()
                rank_jobs.update_tunnel_activity(job_id, url, f"Scoring: {cv['filename']}")
                rank_jobs.update_job(job_id, current_filename=cv["filename"])
                try:
                    outcome = llm_ranking_service.score_cv(rubric_or_jd, cv["raw_text"], url, llm_model, is_jd=is_jd)
                except Exception as e:
                    outcome = {"score": 0.0, "justification": f"LLM call failed: {e}"}
                finally:
                    rank_jobs.update_tunnel_activity(job_id, url, None)
                    tunnel_queue.put(url)
                    tunnel_queue.task_done()
                    
                if rank_jobs.get_job(job_id).get("status") == "cancelled":
                    return
                
                llm_score = float(outcome.get("score", 0.0))
                if method == "hybrid":
                    scores = precomputed.get(cv["id"], {"tfidf": 0.0, "model1": 0.0, "model2": 0.0})
                    final_score = (
                        0.50 * llm_score +
                        0.20 * scores["model2"] +
                        0.20 * scores["model1"] +
                        0.10 * scores["tfidf"]
                    )
                    justification = (
                        f"Hybrid Score: LLM Rubric ({llm_score} * 50%) + "
                        f"model-best2 ({scores['model2']} * 20%) + "
                        f"model-best ({scores['model1']} * 20%) + "
                        f"TF-IDF ({scores['tfidf']} * 10%). "
                        f"Details: {outcome.get('justification', '')}"
                    )
                    score_to_append = round(final_score, 2)
                else:
                    score_to_append = round(llm_score, 2)
                    justification = outcome.get("justification", "")

                rank_jobs.append_result(job_id, {
                    "id": cv["id"],
                    "filename": cv["filename"],
                    "name": cv["name"],
                    "email": cv["email"],
                    "skills": cv["skills"],
                    "match_score": score_to_append,
                    "llm_justification": justification,
                    "years_of_experience": cv.get("years_of_experience"),
                    "seniority_level": cv.get("seniority_level"),
                })
                completed_count += 1
                rank_jobs.update_job(job_id, completed=completed_count)
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as executor:
                futures = [executor.submit(standard_scoring_worker, cv) for cv in cv_dicts]
                for fut in concurrent.futures.as_completed(futures):
                    if rank_jobs.get_job(job_id).get("status") == "cancelled":
                        return
                    fut.result()

            if rank_jobs.get_job(job_id).get("status") == "cancelled":
                return
            rank_jobs.finish_job(job_id, top_n)

            # Get sorted results
            job_info = rank_jobs.get_job(job_id)
            sorted_results = job_info.get("results", [])

            # Save LLM standard/no-rubric results to DB
            db = SessionLocal()
            try:
                history = MatchHistory(
                    project_id=project_id,
                    jd_text=jd_text,
                    rubric=rubric_or_jd if method == "llm" else None,
                    method=method,
                    llm_model=llm_model,
                    results=sorted_results
                )
                db.add(history)
                db.commit()
                db.refresh(history)
                rank_jobs.update_job(job_id, history_id=history.id)
            except Exception as db_err:
                print(f"Error saving match history to DB: {db_err}")
            finally:
                db.close()
    except Exception as e:
        rank_jobs.fail_job(job_id, str(e))


@router.post("/rank/llm/start")
def start_llm_rank(body: RankRequest, db: Session = Depends(get_db)):
    if body.method not in ("llm", "llm_no_rubric", "llm_multilayer", "hybrid"):
        raise HTTPException(400, f"Unsupported method for LLM ranker: {body.method}")
    if not body.ollama_url:
        raise HTTPException(400, f"ollama_url is required for method={body.method}")
    if not body.llm_model:
        raise HTTPException(400, f"llm_model is required for method={body.method}")

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
            "years_of_experience": cv.years_of_experience,
            "seniority_level": cv.seniority_level,
        })

    job_id = rank_jobs.create_job(total=len(cv_dicts))
    threading.Thread(
        target=_run_llm_ranking_job,
        args=(job_id, cv_dicts, body.jd_text, body.ollama_url, body.llm_model, body.top_n, body.method, body.project_id),
        daemon=True,
    ).start()
    return {"job_id": job_id}


@router.get("/rank/llm/{job_id}")
def get_llm_rank_status(job_id: str):
    job = rank_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/rank/llm/cancel/{job_id}")
def cancel_llm_rank(job_id: str):
    job = rank_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    rank_jobs.cancel_job(job_id)
    return {"status": "ok"}


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

    # Estimate experience and seniority
    years, seniority = ner_service.estimate_experience_and_seniority(cv.raw_text)
    cv.years_of_experience = years
    cv.seniority_level = seniority

    # Inject into ner_model1, ner_model2, ner_merged if present
    exp_val = [f"{years} yrs" if years > 0 else "0 yrs"]
    sen_val = [seniority]
    if cv.ner_model1:
        m1 = dict(cv.ner_model1)
        m1["YEARS_OF_EXPERIENCE"] = exp_val
        m1["SENIORITY_LEVEL"] = sen_val
        cv.ner_model1 = m1
    if cv.ner_model2:
        m2 = dict(cv.ner_model2)
        m2["YEARS_OF_EXPERIENCE"] = exp_val
        m2["SENIORITY_LEVEL"] = sen_val
        cv.ner_model2 = m2
    if cv.ner_merged:
        merged = dict(cv.ner_merged)
        merged["YEARS_OF_EXPERIENCE"] = exp_val
        merged["SENIORITY_LEVEL"] = sen_val
        cv.ner_merged = merged

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


# ── Match History ─────────────────────────────────────────────────────────────
@router.get("/rank/history")
def get_rank_history(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(MatchHistory)
    if project_id is not None:
        query = query.filter(MatchHistory.project_id == project_id)
    history_items = query.order_by(MatchHistory.created_at.desc()).all()
    
    out = []
    for item in history_items:
        proj_name = item.project.name if item.project else None
        out.append({
            "id": item.id,
            "project_id": item.project_id,
            "project_name": proj_name,
            "method": item.method,
            "llm_model": item.llm_model,
            "created_at": item.created_at,
            "jd_summary": item.jd_text[:100] + ("..." if len(item.jd_text) > 100 else "")
        })
    return out


@router.get("/rank/history/{history_id}")
def get_rank_history_detail(history_id: int, db: Session = Depends(get_db)):
    item = db.query(MatchHistory).filter(MatchHistory.id == history_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="History not found")
    
    # Compute jd_ner on the fly for non-LLM runs to support Compare NER in re-loaded history
    jd_ner = {}
    if not item.method.startswith("llm"):
        try:
            jd_ner = _jd_ner_for_method(item.jd_text, item.method)
        except Exception:
            pass

    results = []
    if item.results:
        cv_ids = [r["id"] for r in item.results if isinstance(r, dict) and "id" in r]
        cv_map = {}
        if cv_ids:
            cvs = db.query(CV).filter(CV.id.in_(cv_ids)).all()
            cv_map = {
                cv.id: {
                    "ner_model1": cv.ner_model1 or {},
                    "ner_model2": cv.ner_model2 or {},
                    "ner_merged": cv.ner_merged or {}
                }
                for cv in cvs
            }
        for r in item.results:
            if isinstance(r, dict):
                enriched_r = dict(r)
                cv_ner = cv_map.get(r.get("id"), {})
                enriched_r.update(cv_ner)
                results.append(enriched_r)
            else:
                results.append(r)
    else:
        results = item.results

    return {
        "id": item.id,
        "project_id": item.project_id,
        "project_name": item.project.name if item.project else None,
        "jd_text": item.jd_text,
        "rubric": item.rubric,
        "method": item.method,
        "llm_model": item.llm_model,
        "created_at": item.created_at,
        "results": results,
        "jd_ner": jd_ner
    }


@router.delete("/rank/history/{history_id}")
def delete_rank_history(history_id: int, db: Session = Depends(get_db)):
    item = db.query(MatchHistory).filter(MatchHistory.id == history_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="History not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


from pydantic import BaseModel

class SemanticCompareRequest(BaseModel):
    jd_text: str
    method: str = "tfidf"

@router.post("/{cv_id}/compare-semantic")
def compare_semantic(cv_id: int, body: SemanticCompareRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
        
    is_tfidf = (body.method == "tfidf")
    cv_text_lower = (cv.raw_text or "").lower()
    jd_text_lower = body.jd_text.lower()
    
    if body.method in ("model1", "model1_hybrid"):
        nlp = ner_service.get_model1()
        cv_ner = cv.ner_model1 or {}
    elif body.method in ("model2", "model2_hybrid"):
        nlp = ner_service.get_model2()
        cv_ner = cv.ner_model2 or {}
    else:
        nlp = ner_service.get_model2()
        cv_ner = cv.ner_merged or {}
        
    jd_ner = _jd_ner_for_method(body.jd_text, body.method)
    
    jd_skills = list(set((jd_ner.get("SKILLS") or []) + (jd_ner.get("SKILL") or [])))
    cv_skills = list(set((cv_ner.get("SKILLS") or []) + (cv_ner.get("SKILL") or [])))
    
    jd_techs = list(set(jd_ner.get("TECHNOLOGY") or []))
    cv_techs = list(set(cv_ner.get("TECHNOLOGY") or []))
    
    def get_best_matches(jd_items, cv_items):
        results = []
        for jd_item in jd_items:
            jd_item_clean = jd_item.strip()
            jd_item_lower = jd_item_clean.lower()
            
            if is_tfidf:
                import re
                escaped = re.escape(jd_item_lower)
                pattern = rf"\b{escaped}\b"
                
                count_jd = len(re.findall(pattern, jd_text_lower))
                count_cv = len(re.findall(pattern, cv_text_lower))
                
                if count_jd == 0:
                    count_jd = 1
                
                score = min(1.0, count_cv / count_jd)
                best_match = f"{count_cv} mentions" if count_cv > 0 else "0 mentions"
                
                results.append({
                    "jd_item": jd_item_clean,
                    "cv_item": best_match,
                    "similarity": round(score * 100, 1)
                })
            else:
                best_score = 0.0
                best_match = None
                
                jd_clean = jd_item_lower
                for cv_item in cv_items:
                    cv_clean = cv_item.strip().lower()
                    if jd_clean == cv_clean:
                        best_score = 1.0
                        best_match = cv_item
                        break
                
                if best_score < 1.0 and cv_items:
                    if body.method in ("sentence_transformer", "sentence_transformer_hybrid"):
                        try:
                            from sklearn.metrics.pairwise import cosine_similarity
                            from ..services.ranking import _get_transformer_model
                            st_model = _get_transformer_model()
                            
                            jd_emb = st_model.encode(jd_item_clean).reshape(1, -1)
                            cv_embs = st_model.encode(cv_items)
                            sims = cosine_similarity(jd_emb, cv_embs)[0]
                            for cv_item, sim in zip(cv_items, sims):
                                if sim > best_score:
                                    best_score = float(sim)
                                    best_match = cv_item
                        except Exception:
                            for cv_item in cv_items:
                                import difflib
                                sim = difflib.SequenceMatcher(None, jd_clean, cv_item.strip().lower()).ratio()
                                if sim > best_score:
                                    best_score = sim
                                    best_match = cv_item
                    else:
                        token_jd = nlp(jd_item_clean)
                        for cv_item in cv_items:
                            token_cv = nlp(cv_item)
                            if token_jd.vector_norm and token_cv.vector_norm:
                                sim = float(token_jd.similarity(token_cv))
                            else:
                                import difflib
                                sim = difflib.SequenceMatcher(None, jd_clean, cv_item.strip().lower()).ratio()
                                
                            if sim > best_score:
                                best_score = sim
                                align_item = cv_item
                                best_match = cv_item
                            
                results.append({
                    "jd_item": jd_item_clean,
                    "cv_item": best_match or "N/A",
                    "similarity": round(best_score * 100, 1)
                })
        return results
        
    return {
        "skills": get_best_matches(jd_skills, cv_skills),
        "technologies": get_best_matches(jd_techs, cv_techs)
    }

