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
            "tunnel_activity": {},
            "rubric": None,
            "results": [],
            "error": None,
            "disabled_tunnels": [],
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


def cancel_job(job_id: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["status"] = "cancelled"
        job["phase"] = "cancelled"
        job["error"] = "Job was cancelled by the user."


def update_tunnel_activity(job_id: str, url: str, filename: str | None) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        if "tunnel_activity" not in job:
            job["tunnel_activity"] = {}
        if filename:
            job["tunnel_activity"][url] = filename
        else:
            job["tunnel_activity"].pop(url, None)


def disable_tunnel(job_id: str, url: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job:
            if "disabled_tunnels" not in job:
                job["disabled_tunnels"] = []
            if url not in job["disabled_tunnels"]:
                job["disabled_tunnels"].append(url)


def get_disabled_tunnels(job_id: str) -> list[str]:
    with _LOCK:
        job = _JOBS.get(job_id)
        return job.get("disabled_tunnels", []) if job else []

