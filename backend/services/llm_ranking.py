"""
LLM-as-judge JD ranking: build a scoring rubric from the JD with an LLM, then
score each CV's already-extracted raw text against that rubric — one CV per
call, temperature 0 throughout so scoring is deterministic and literal rather
than creative. Mirrors the two-stage rubric/score approach used in
CV_LLM_Full_Pipeline.ipynb, but scores full raw CV text directly (no
re-parsing) and one candidate per call instead of batching.
"""
import json
import time
import requests
import urllib3

# Cloudflare/ngrok tunnels use certs Python's bundled CA bundle may not verify —
# these are user-controlled dev tunnels, so skip SSL verification (same as ocr.py).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RUBRIC_SYSTEM_PROMPT = (
    "You are an expert technical recruiter. Given a job description, produce a detailed, "
    "objective scoring rubric to judge candidate CVs against this specific role. Break it into "
    "concrete, checkable criteria (required skills, experience level, domain knowledge, key "
    "responsibilities, nice-to-haves) with a clear relative weight/importance for each. Be "
    "precise and literal — do not invent requirements the job description doesn't state, and do "
    "not add creative flourishes. Respond with plain text only, no markdown headers."
)

SCORE_SYSTEM_PROMPT = (
    "You are an expert technical recruiter scoring one candidate CV against a fixed rubric "
    "derived from a job description. Judge strictly and literally against the rubric's stated "
    "criteria only — do not reward creativity, embellishment, or impressive-sounding but "
    "unrelated experience. Score from 0-100. Respond with valid JSON only, matching the "
    "requested schema."
)

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "justification": {"type": "string"},
    },
    "required": ["score", "justification"],
}


# temperature 0 (+ no top_p/top_k sampling noise) — deterministic, literal scoring, not creative
_DETERMINISTIC_OPTIONS = {"num_ctx": 16384, "num_predict": -1, "temperature": 0, "top_p": 1, "top_k": 1}


def _poll_job(base_url: str, job_id: str, interval: int = 5, max_wait: int = 600) -> str:
    """Poll /result/{job_id} until done or error. Tolerates transient tunnel blips (same as ocr.py)."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/result/{job_id}", verify=False, timeout=10)
            r.raise_for_status()
            data = r.json()
        except (requests.exceptions.RequestException, ValueError):
            time.sleep(interval)
            continue
        if data["status"] == "done":
            return data["result"]
        if data["status"] == "error":
            raise RuntimeError(f"LLM inference failed: {data['result']}")
        time.sleep(interval)
    raise TimeoutError(f"LLM inference did not complete within {max_wait}s")


def _ollama_chat(base_url: str, model: str, system_prompt: str, user_text: str,
                  json_schema: dict | None = None, timeout: int = 180) -> str:
    base_url = base_url.rstrip("/")

    # Try the async job-queue wrapper first (Colab FastAPI server, same pattern as
    # ocr.py's extract_minicpm) — avoids Cloudflare tunnels timing out on long-running
    # streamed calls. Falls back to direct Ollama /api/chat if that's not available.
    try:
        submit_res = requests.post(
            f"{base_url}/submit",
            json={
                "model": model,
                "prompt": user_text,
                "system": system_prompt,
                "json_schema": json_schema,
                "options": _DETERMINISTIC_OPTIONS,
            },
            verify=False, timeout=30,
        )
        if submit_res.status_code == 200:
            job_id = submit_res.json()["job_id"]
            return _poll_job(base_url, job_id, max_wait=timeout).strip()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, KeyError):
        pass  # fall back to direct Ollama streaming

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": True,
        "options": _DETERMINISTIC_OPTIONS,
    }
    if json_schema is not None:
        payload["format"] = json_schema

    response = requests.post(f"{base_url}/api/chat", json=payload,
                              stream=True, timeout=timeout, verify=False)
    response.raise_for_status()
    content = ""
    for line in response.iter_lines(decode_unicode=True):
        if line:
            chunk = json.loads(line)
            content += chunk.get("message", {}).get("content", "")
    return content.strip()


def build_rubric(jd_text: str, ollama_url: str, model: str) -> str:
    """Turn a job description into a detailed, literal scoring rubric."""
    user_text = f"Job Description:\n{jd_text}\n\nProduce the scoring rubric for this job description."
    return _ollama_chat(ollama_url, model, RUBRIC_SYSTEM_PROMPT, user_text)


def score_cv(rubric: str, cv_text: str, ollama_url: str, model: str) -> dict:
    """Score one CV's raw text against a rubric. Returns {"score": float, "justification": str}."""
    user_text = (
        f"Scoring Rubric:\n{rubric}\n\n"
        f"Candidate CV:\n{cv_text}\n\n"
        "Score this candidate strictly against the rubric above."
    )
    content = _ollama_chat(ollama_url, model, SCORE_SYSTEM_PROMPT, user_text, json_schema=SCORE_SCHEMA)
    try:
        parsed = json.loads(content)
        return {
            "score": float(parsed.get("score", 0)),
            "justification": str(parsed.get("justification", "")),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"score": 0.0, "justification": "Could not parse LLM response."}
