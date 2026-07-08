"""
In-memory progress tracking for the LLM Judge ranking job. Scoring 50+ CVs
one LLM call at a time can take minutes, so /cvs/rank/llm/start kicks off a
background thread and returns a job_id immediately; the frontend polls
/cvs/rank/llm/{job_id} to render live progress instead of staring at a
spinner for the whole run.

Single dict in process memory — fine for this app's single-user, single-
process dev setup. Not meant to survive a server restart or scale to
multiple workers.
"""
import threading
import uuid

_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def create_job(total: int) -> str:
    job_id = str(uuid.uuid4())
    with _LOCK:
        _JOBS[job_id] = {
            "status": "running",   # running | done | error
            "phase": "starting",   # starting | rubric | scoring | done
            "total": total,
            "completed": 0,
            "current_filename": None,
            "rubric": None,
            "results": [],
            "error": None,
        }
    return job_id


def update_job(job_id: str, **fields) -> None:
    with _LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(fields)


def append_result(job_id: str, result: dict) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["results"].append(result)
        job["completed"] += 1


def finish_job(job_id: str, top_n: int) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["results"] = sorted(job["results"], key=lambda r: r["match_score"], reverse=True)
        job["status"] = "done"
        job["phase"] = "done"
        job["current_filename"] = None


def fail_job(job_id: str, error: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["status"] = "error"
        job["error"] = error


def get_job(job_id: str) -> dict:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else {}
