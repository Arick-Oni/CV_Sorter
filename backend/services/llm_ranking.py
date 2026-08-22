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
    "5 to 8 major, non-overlapping evaluation criteria based on the actual structure of the Job Description. "
    "For each criterion, define its name, description, weight (an integer representing importance), "
    "and a list of structured subcriteria.\n\n"
    "CRITICAL CONSTRAINTS FOR RUBRIC GENERATION:\n"
    "1. Criteria count: Generate between 5 and 8 criteria. Do not force exactly 5.\n"
    "2. Non-overlapping: Ensure criteria and subcriteria are strictly non-overlapping. Every technology, "
    "competency, tool, certification, or qualification must appear in exactly one criterion. A skill (e.g., SQL Server, SSRS) "
    "must NOT be duplicated across multiple categories.\n"
    "3. Separate Required & Preferred: Whenever possible, separate required qualifications from preferred (nice-to-have) "
    "qualifications into distinct criteria or distinct subcriteria.\n"
    "4. Weight Allocation: Allocate weights based on employer emphasis: Required > Preferred; repeated skills receive higher "
    "weight; terms like 'Must', 'Expert', 'Required', 'Essential' increase weight; required years of experience must "
    "influence weighting. The total sum of parent criteria weights must equal exactly 100.\n"
    "5. Subcriteria weights: Each subcriterion has a name, a weight, and a 'required' boolean flag. "
    "The sum of subcriterion weights within a criterion must equal the parent criterion's weight.\n"
    "6. Objective criteria only: Remove subjective resume criteria (e.g., Integrity, Positive attitude, Punctuality, "
    "On-site attendance, or other personality traits) unless they are hard requirements that can realistically "
    "be verified or inferred from a resume.\n\n"
    "Respond with valid JSON only matching the schema."
)

CRITERIA_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "minItems": 5,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "weight": {"type": "integer"},
                    "description": {"type": "string"},
                    "subcriteria": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "weight": {"type": "integer"},
                                "required": {"type": "boolean"}
                            },
                            "required": ["name", "weight", "required"]
                        }
                    }
                },
                "required": ["name", "weight", "description", "subcriteria"]
            }
        }
    },
    "required": ["criteria"]
}

SCORE_CRITERION_SYSTEM_PROMPT = (
    "You are an expert technical recruiter scoring a candidate CV against one specific rubric criterion. "
    "You must evaluate every subcriterion of this criterion independently.\n\n"
    "CRITICAL SCORING CONSTRAINTS:\n"
    "1. Strict Evidence-Based: Only use explicit, literal evidence from the resume. Do NOT infer or assume missing experience. "
    "If the resume does not explicitly mention a technology, tool, competency, or qualification, assign a score of 0.0.\n"
    "2. Granular Scoring: For each subcriterion, assign exactly one of the following scores: "
    "1.0 (Full match with clear/strong evidence), 0.75 (Good match with slightly minor gaps), 0.5 (Partial match / basic exposure), "
    "0.25 (Very weak match or highly ambiguous mention), 0.0 (No explicit mention or evidence at all).\n"
    "3. Quote Evidence: You must extract and quote the exact supporting evidence from the resume for each subcriterion. "
    "If no evidence exists, explain why or state 'No explicit evidence found'.\n"
    "4. Clamped Scores: Use lower scores (e.g. 0.25 or 0.0) whenever the evidence is weak, ambiguous, or self-reported without context.\n"
    "5. Calculate Parent Score: Compute the overall criterion score on a 0 to 100 scale from the weighted subcriteria. "
    "Formula: (Sum of (subcriterion_score * subcriterion_weight) / parent_criterion_weight) * 100.\n\n"
    "Respond with valid JSON only matching the schema."
)

SCORE_CRITERION_SCHEMA = {
    "type": "object",
    "properties": {
        "subcriteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "number"},
                    "evidence": {"type": "string"}
                },
                "required": ["name", "score", "evidence"]
            }
        },
        "score": {"type": "number"},
        "justification": {"type": "string"}
    },
    "required": ["subcriteria", "score", "justification"]
}

def normalize_weights(criteria: list[dict]) -> list[dict]:
    """
    Ensure the parent weights sum to exactly 100, and for each criterion,
    the sum of subcriteria weights equals the parent criterion's weight.
    """
    if not criteria:
        return criteria

    # 1. Normalize parent weights to sum to exactly 100
    total_parent_weight = sum(c.get("weight", 0) for c in criteria)
    if total_parent_weight == 0:
        default_weight = 100 // len(criteria)
        for c in criteria:
            c["weight"] = default_weight
        criteria[-1]["weight"] = 100 - (default_weight * (len(criteria) - 1))
    else:
        running_sum = 0
        for i, c in enumerate(criteria):
            w = c.get("weight", 0)
            if i == len(criteria) - 1:
                c["weight"] = 100 - running_sum
            else:
                normalized = round((w / total_parent_weight) * 100)
                c["weight"] = normalized
                running_sum += normalized

    # 2. Normalize subcriteria weights to sum to the parent weight
    for c in criteria:
        parent_w = c["weight"]
        sub = c.get("subcriteria", [])
        if not sub:
            c["subcriteria"] = [{"name": c["name"], "weight": parent_w, "required": True}]
            continue

        total_sub_weight = sum(s.get("weight", 0) for s in sub)
        if total_sub_weight == 0:
            default_sub_weight = parent_w // len(sub)
            running_sub_sum = 0
            for i, s in enumerate(sub):
                if i == len(sub) - 1:
                    s["weight"] = parent_w - running_sub_sum
                else:
                    s["weight"] = default_sub_weight
                    running_sub_sum += default_sub_weight
        else:
            running_sub_sum = 0
            for i, s in enumerate(sub):
                sw = s.get("weight", 0)
                if i == len(sub) - 1:
                    s["weight"] = parent_w - running_sub_sum
                else:
                    normalized_sub = round((sw / total_sub_weight) * parent_w)
                    s["weight"] = normalized_sub
                    running_sub_sum += normalized_sub

    return criteria

def extract_rubric_criteria(jd_text: str, ollama_url: str, model: str) -> list[dict]:
    """Split the job description into 5 to 8 weighted criteria with nested subcriteria."""
    user_text = f"Job Description:\n{jd_text}\n\nExtract 5 to 8 criteria and their structured subcriteria."
    content = _ollama_chat(ollama_url, model, CRITERIA_EXTRACTION_SYSTEM_PROMPT, user_text, json_schema=CRITERIA_EXTRACTION_SCHEMA)
    try:
        parsed = json.loads(content)
        criteria = parsed.get("criteria", [])
        if not (5 <= len(criteria) <= 8):
            raise ValueError(f"Expected between 5 and 8 criteria, got {len(criteria)}")
        return normalize_weights(criteria)
    except Exception as e:
        print(f"Failed to parse criteria JSON: {e}. Using fallback criteria.")
        fallback = [
            {
                "name": "Core Technical Skills",
                "weight": 25,
                "description": "Required languages, frameworks, and tools stated in the JD.",
                "subcriteria": [{"name": "Core programming stack and frameworks", "weight": 25, "required": True}]
            },
            {
                "name": "Experience & Seniority",
                "weight": 20,
                "description": "Years of experience and role seniority levels.",
                "subcriteria": [{"name": "Required years and depth of professional experience", "weight": 20, "required": True}]
            },
            {
                "name": "Architecture & Design",
                "weight": 15,
                "description": "System design, OOP, design patterns, and architecture principles.",
                "subcriteria": [{"name": "System design and software architecture principles", "weight": 15, "required": False}]
            },
            {
                "name": "Database & Cloud Infrastructure",
                "weight": 20,
                "description": "Databases, cloud platforms, and DevOps / CI/CD tools.",
                "subcriteria": [{"name": "Cloud infrastructure and database systems", "weight": 20, "required": True}]
            },
            {
                "name": "Methodology & Domain",
                "weight": 20,
                "description": "Agile methodologies, communication skills, and specific industry domain experience.",
                "subcriteria": [{"name": "Agile practices and domain expertise", "weight": 20, "required": False}]
            }
        ]
        return normalize_weights(fallback)

def score_cv_criterion(criterion: dict, cv_text: str, ollama_url: str, model: str) -> dict:
    """Score one candidate CV raw text against a single criterion by evaluating its subcriteria independently."""
    sub_lines = []
    for s in criterion.get("subcriteria", []):
        req_str = "Required" if s.get("required", True) else "Preferred"
        sub_lines.append(f"- Name: {s['name']}, Weight: {s['weight']}, Type: {req_str}")
    sub_desc = "\n".join(sub_lines)

    user_text = (
        f"Parent Criterion: {criterion['name']}\n"
        f"Total Weight: {criterion['weight']}\n"
        f"Description: {criterion['description']}\n\n"
        f"Evaluate the following Subcriteria:\n{sub_desc}\n\n"
        f"Candidate CV:\n{cv_text}\n\n"
        f"Evaluate each subcriterion independently and return the JSON response matching the schema."
    )
    
    content = _ollama_chat(ollama_url, model, SCORE_CRITERION_SYSTEM_PROMPT, user_text, json_schema=SCORE_CRITERION_SCHEMA)
    
    try:
        parsed = json.loads(content)
        
        orig_subs = criterion.get("subcriteria", [])
        parsed_subs = parsed.get("subcriteria", [])
        
        weighted_sum = 0.0
        aligned_parsed_subs = []
        
        for idx, orig_sub in enumerate(orig_subs):
            orig_name_clean = orig_sub["name"].strip().lower()
            match_eval = None
            
            for p_sub in parsed_subs:
                if p_sub.get("name", "").strip().lower() == orig_name_clean:
                    match_eval = p_sub
                    break
            
            if not match_eval and idx < len(parsed_subs):
                match_eval = parsed_subs[idx]
                
            if match_eval:
                eval_score = float(match_eval.get("score", 0.0))
                valid_scores = [0.0, 0.25, 0.5, 0.75, 1.0]
                eval_score = min(valid_scores, key=lambda x: abs(x - eval_score))
                
                weighted_sum += eval_score * orig_sub["weight"]
                
                aligned_parsed_subs.append({
                    "name": orig_sub["name"],
                    "weight": orig_sub["weight"],
                    "required": orig_sub.get("required", True),
                    "score": eval_score,
                    "evidence": str(match_eval.get("evidence", ""))
                })
            else:
                aligned_parsed_subs.append({
                    "name": orig_sub["name"],
                    "weight": orig_sub["weight"],
                    "required": orig_sub.get("required", True),
                    "score": 0.0,
                    "evidence": "No explicit evidence found."
                })
        
        parent_weight = float(criterion["weight"])
        computed_score = (weighted_sum / parent_weight) * 100.0 if parent_weight > 0 else 0.0
        
        sub_details = []
        for s in aligned_parsed_subs:
            status = "Required" if s["required"] else "Preferred"
            evidence_str = f"Evidence: \"{s['evidence']}\"" if s["evidence"] and s["evidence"].strip() != "No explicit evidence found." else "No explicit evidence found."
            sub_details.append(f"[{s['name']} (Weight: {s['weight']}/{int(parent_weight)}, {status}) -> Score: {s['score']} ({evidence_str})]")
        
        overall_justification = str(parsed.get("justification", ""))
        full_justification = f"Overall: {overall_justification}\nSubcriteria Breakdown:\n" + "\n".join(sub_details)
        
        return {
            "score": round(computed_score, 2),
            "justification": full_justification,
            "subcriteria_breakdown": aligned_parsed_subs
        }
    except Exception as e:
        print(f"Failed to parse or score criterion: {e}. Using fallback 0.0.")
        fallback_breakdown = []
        for s in criterion.get("subcriteria", []):
            fallback_breakdown.append({
                "name": s["name"],
                "weight": s["weight"],
                "required": s.get("required", True),
                "score": 0.0,
                "evidence": f"Scoring execution encountered an error: {e}"
            })
        return {
            "score": 0.0,
            "justification": f"Failed to score criterion: {e}.",
            "subcriteria_breakdown": fallback_breakdown
        }


