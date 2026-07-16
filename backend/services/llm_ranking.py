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
    "You are an expert technical recruiter. You score candidate CVs against a scoring rubric "
    "from 0-100 based on real relevance (skills, experience, context), not keyword overlap. "
    "CRITICAL GUARDRAIL: Some CVs are blank templates containing placeholder text, formatting guides, "
    "or writing instructions (e.g., 'Write a short brief introduction explaining who you are...', "
    "'In a short statement of no more than just a few sentences describe your role...', 'A sentence describing your duties', "
    "'More text here', 'Company name', 'JOB TITLE'). You MUST ignore these placeholder instructions. "
    "Any candidate CV that is a blank template containing no actual personal background or work history "
    "MUST be scored as 0. Respond with valid JSON only, matching the requested schema."
)

SCORE_JD_SYSTEM_PROMPT = (
    "You are an expert technical recruiter. You score candidate CVs against a job description "
    "from 0-100 based on real relevance (skills, experience, context), not keyword overlap. "
    "CRITICAL GUARDRAIL: Some CVs are blank templates containing placeholder text, formatting guides, "
    "or writing instructions (e.g., 'Write a short brief introduction explaining who you are...', "
    "'In a short statement of no more than just a few sentences describe your role...', 'A sentence describing your duties', "
    "'More text here', 'Company name', 'JOB TITLE'). You MUST ignore these placeholder instructions. "
    "Any candidate CV that is a blank template containing no actual personal background or work history "
    "MUST be scored as 0. Respond with valid JSON only, matching the requested schema."
)

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "justification": {"type": "string"},
    },
    "required": ["score", "justification"],
}

FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "explanation": {"type": "string"},
    },
    "required": ["relevant"],
}

FILTER_SYSTEM_PROMPT = (
    "You are an expert recruiter performing a quick, initial pass over candidate CVs. "
    "Determine whether the candidate has any potential relevance, skills, or background "
    "that could align with the job description. Do not be overly strict—if they have transferrable "
    "skills or basic qualifications, mark them as relevant so they can be scored in the next round. "
    "CRITICAL GUARDRAIL: If the CV is a blank template containing only placeholder instructions, formatting guides, "
    "or boilerplate text with no actual candidate career history, mark it as NOT relevant (relevant: false). "
    "Respond with valid JSON only matching the schema."
)

BATCH_SCORING_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "score": {"type": "number"},
                    "justification": {"type": "string"},
                },
                "required": ["filename", "score", "justification"],
            },
        }
    },
    "required": ["scores"],
}

BATCH_SCORE_SYSTEM_PROMPT = (
    "You are an expert technical recruiter scoring candidate CVs against a job description. "
    "Compare and score each candidate CV from 0-100 based on their relevance and fit. "
    "CRITICAL GUARDRAIL: Some CVs are blank templates containing placeholder text, formatting guides, "
    "or writing instructions (e.g., 'Write a short brief introduction explaining who you are...', "
    "'In a short statement of no more than just a few sentences describe your role...', 'A sentence describing your duties', "
    "'More text here', 'Company name', 'JOB TITLE'). You MUST ignore these placeholder instructions. "
    "Any candidate CV that is a blank template containing no actual personal background or work history "
    "MUST be scored as 0. Respond with valid JSON only matching the requested schema, returning exactly "
    "one score entry per candidate filename provided."
)

RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "rank": {"type": "integer"},
                    "score": {"type": "number"},
                    "justification": {"type": "string"}
                },
                "required": ["filename", "rank", "score", "justification"]
            }
        }
    },
    "required": ["ranks"]
}

RERANK_SYSTEM_PROMPT = (
    "You are an expert executive recruiter comparative-ranking candidate CVs side-by-side. "
    "Given a job description and a list of top candidates, compare them against each other "
    "and rank them in order of best fit (Rank 1 being the best) down to the last candidate. "
    "Assign them relative, final matching scores (0-100) reflecting their hierarchy, and provide a "
    "clear, comparative justification explaining why they placed in that specific rank relative "
    "to the other candidates. Respond with valid JSON only matching the schema."
)


# temperature 1 (+ no top_p/top_k sampling noise) — deterministic, literal scoring, not creative
_DETERMINISTIC_OPTIONS = {"num_ctx": 16384, "num_predict": -1, "temperature": 1, "top_p": 1, "top_k": 1}


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
                  json_schema: dict | None = None, timeout: int = 500) -> str:
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


def score_cv(rubric_or_jd: str, cv_text: str, ollama_url: str, model: str, is_jd: bool = False) -> dict:
    """Score one CV's raw text against a rubric or JD. Returns {"score": float, "justification": str}."""
    if is_jd:
        user_text = (
            f"Job Description:\n{rubric_or_jd}\n\n"
            f"Candidate CV:\n{cv_text}\n\n"
            "Score this candidate from 0-100 against this job description, with a one-sentence justification."
        )
        system_prompt = SCORE_JD_SYSTEM_PROMPT
    else:
        user_text = (
            f"Scoring Rubric:\n{rubric_or_jd}\n\n"
            f"Candidate CV:\n{cv_text}\n\n"
            "Score this candidate from 0-100 against this scoring rubric, with a one-sentence justification."
        )
        system_prompt = SCORE_SYSTEM_PROMPT

    content = _ollama_chat(ollama_url, model, system_prompt, user_text, json_schema=SCORE_SCHEMA)
    try:
        parsed = json.loads(content)
        return {
            "score": float(parsed.get("score", 0)),
            "justification": str(parsed.get("justification", "")),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"score": 0.0, "justification": "Could not parse LLM response."}


def filter_candidate(jd_text: str, cv_text: str, ollama_url: str, model: str) -> bool:
    """Soft-filter a CV to check if it has potential relevance to the JD."""
    user_text = (
        f"Job Description:\n{jd_text}\n\n"
        f"Candidate CV:\n{cv_text}\n\n"
        "Is this candidate potentially relevant to the job? Answer with a JSON object containing the boolean 'relevant'."
    )
    try:
        content = _ollama_chat(ollama_url, model, FILTER_SYSTEM_PROMPT, user_text, json_schema=FILTER_SCHEMA)
        parsed = json.loads(content)
        return bool(parsed.get("relevant", True))
    except Exception:
        # Fallback to True if parsing fails to avoid dropping relevant candidates
        return True


def score_batch(jd_text: str, batch_candidates: list[dict], ollama_url: str, model: str) -> list[dict]:
    """Score a batch of candidate CVs (up to 3) against the Job Description."""
    # batch_candidates is a list of dicts: {"filename": str, "raw_text": str}
    blocks = []
    for idx, cand in enumerate(batch_candidates):
        blocks.append(f"Candidate {idx+1} [Filename: {cand['filename']}]:\n{cand['raw_text']}")
    candidates_text = "\n---\n".join(blocks)
    
    user_text = (
        f"Job Description:\n{jd_text}\n\n"
        f"Score EACH of the following {len(batch_candidates)} candidates from 0-100 against the job description above. "
        f"Provide a brief, one-sentence justification for each. "
        f"Return exactly one entry per candidate, identified by filename.\n\n"
        f"Candidates:\n{candidates_text}"
    )
    
    try:
        content = _ollama_chat(ollama_url, model, BATCH_SCORE_SYSTEM_PROMPT, user_text, json_schema=BATCH_SCORING_SCHEMA)
        parsed = json.loads(content)
        return parsed.get("scores", [])
    except Exception:
        return []


def rerank_top_candidates(jd_text: str, top_candidates: list[dict], ollama_url: str, model: str) -> list[dict]:
    """Re-rank the top candidates relative to each other by presenting them side-by-side."""
    # top_candidates is a list of dicts: {"filename": str, "raw_text": str, "previous_score": float, "previous_justification": str}
    blocks = []
    for cand in top_candidates:
        # Use first 1500 chars of CV to fit context limit
        snippet = cand["raw_text"][:1500]
        blocks.append(
            f"Candidate Filename: {cand['filename']}\n"
            f"Stage 2 Score: {cand['previous_score']}\n"
            f"Stage 2 Justification: {cand['previous_justification']}\n"
            f"CV Snippet (First 1500 chars):\n{snippet}"
        )
    candidates_text = "\n---\n".join(blocks)
    
    user_text = (
        f"Job Description:\n{jd_text}\n\n"
        "Here are the top candidates. Compare their profiles relative to one another and "
        "output a definitive final ranking and comparative scores from 0-100.\n\n"
        f"Candidates:\n{candidates_text}"
    )
    
    try:
        content = _ollama_chat(ollama_url, model, RERANK_SYSTEM_PROMPT, user_text, json_schema=RERANK_SCHEMA)
        parsed = json.loads(content)
        return parsed.get("ranks", [])
    except Exception:
        return []


CRITERIA_EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert technical recruiter. Analyze the given job description and divide it into "
    "exactly 5 major, non-overlapping criteria for screening candidates. Each criterion must represent "
    "a distinct category (e.g., Core programming stack, Frameworks, Architecture/Databases, Process/Soft skills, Domain experience). "
    "Allocate a weight percentage (integer) to each of the 5 criteria such that they sum to exactly 100%. "
    "Respond with valid JSON only matching the schema."
)

CRITERIA_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "weight": {"type": "integer"},
                    "description": {"type": "string"},
                    "sub_criteria": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["name", "weight", "description", "sub_criteria"]
            }
        }
    },
    "required": ["criteria"]
}

SCORE_CRITERION_SYSTEM_PROMPT = (
    "You are an expert technical recruiter. You score candidate CVs against one specific rubric criterion "
    "from 0-100 based on candidate fit. "
    "CRITICAL GUARDRAIL: If the CV is a blank template containing placeholder text, formatting guides, "
    "or writing instructions, score it as 0. Respond with valid JSON only matching the schema."
)

SCORE_CRITERION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "justification": {"type": "string"},
    },
    "required": ["score", "justification"],
}

def extract_rubric_criteria(jd_text: str, ollama_url: str, model: str) -> list[dict]:
    """Split the job description into exactly 5 weighted criteria."""
    user_text = f"Job Description:\n{jd_text}\n\nExtract exactly 5 criteria and their weights."
    content = _ollama_chat(ollama_url, model, CRITERIA_EXTRACTION_SYSTEM_PROMPT, user_text, json_schema=CRITERIA_EXTRACTION_SCHEMA)
    try:
        parsed = json.loads(content)
        criteria = parsed.get("criteria", [])
        if len(criteria) != 5:
            raise ValueError("Expected exactly 5 criteria")
        return criteria
    except Exception as e:
        print(f"Failed to parse criteria JSON: {e}. Using fallback criteria.")
        return [
            {"name": "Core Technical Skills", "weight": 20, "description": "Required languages, frameworks, and tools", "sub_criteria": []},
            {"name": "Experience & Seniority", "weight": 20, "description": "Years of experience and role seniority", "sub_criteria": []},
            {"name": "Architecture & Design", "weight": 20, "description": "System design, OOP, and patterns", "sub_criteria": []},
            {"name": "Database & Cloud", "weight": 20, "description": "Databases, cloud platforms, and DevOps", "sub_criteria": []},
            {"name": "Methodology & Soft Skills", "weight": 20, "description": "Agile, team-work, and communication", "sub_criteria": []}
        ]

def score_cv_criterion(criterion: dict, cv_text: str, ollama_url: str, model: str) -> dict:
    """Score one candidate CV raw text against a single criterion. Returns {"score": float, "justification": str}."""
    user_text = (
        f"Criterion: {criterion['name']}\n"
        f"Weight: {criterion['weight']}%\n"
        f"Description: {criterion['description']}\n"
        f"Sub-criteria: {', '.join(criterion.get('sub_criteria', []))}\n\n"
        f"Candidate CV:\n{cv_text}\n\n"
        f"Score this candidate's fit for this specific criterion on a scale from 0 to 100, and provide a one-sentence justification."
    )
    content = _ollama_chat(ollama_url, model, SCORE_CRITERION_SYSTEM_PROMPT, user_text, json_schema=SCORE_CRITERION_SCHEMA)
    try:
        parsed = json.loads(content)
        return {
            "score": float(parsed.get("score", 0.0)),
            "justification": str(parsed.get("justification", "")),
        }
    except Exception as e:
        return {"score": 0.0, "justification": f"Parsing failed for this criterion: {e}."}

