# CV Platform — API Usage & Integration Guide

This guide describes how to interact with the CV Platform API endpoints. It covers managing projects, uploading/processing CVs, running local matching algorithms, and executing asynchronous parallel-tunnel LLM ranking jobs.

## Base URL
By default, the backend server runs at:
```
http://localhost:8000
```
*Note: All requests should contain the header `Content-Type: application/json` unless uploading files (which use `multipart/form-data`).*

---

## Table of Contents
1. [Managing Projects](#1-managing-projects)
2. [CV Upload and Ingestion](#2-cv-upload-and-ingestion)
3. [Managing CVs & Reprocessing](#3-managing-cvs--reprocessing)
4. [Synchronous Ranking (Local Methods)](#4-synchronous-ranking-local-methods)
5. [Asynchronous LLM Ranking (Ollama)](#5-asynchronous-llm-ranking-ollama)
6. [Match History](#6-match-history)
7. [Semantic Compare & Highlighting](#7-semantic-compare--highlighting)
8. [Python Code Examples](#8-python-code-examples)

---

## 1. Managing Projects

Projects serve as buckets to group CVs.

### 1.1 List All Projects
Get a list of all active projects in alphabetical order.
* **Method**: `GET`
* **Path**: `/projects/`
* **cURL example**:
  ```bash
  curl -X GET http://localhost:8000/projects/
  ```
* **Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Backend Software Developer Hiring",
      "created_at": "2026-07-19T04:10:00.123456Z"
    }
  ]
  ```

### 1.2 Create a Project
Creates a new project. If a project with the same name already exists, the server returns the existing record instead of throwing an error.
* **Method**: `POST`
* **Path**: `/projects/`
* **Payload**:
  ```json
  {
    "name": "Senior Data Scientist"
  }
  ```
* **cURL example**:
  ```bash
  curl -X POST http://localhost:8000/projects/ \
    -H "Content-Type: application/json" \
    -d '{"name": "Senior Data Scientist"}'
  ```

### 1.3 Delete a Project
Deletes the project. By default, the CVs associated with this project are not deleted; they are unassigned (`project_id` is set to `null`). To delete the project and all its CVs, pass `cascade=true` as a query parameter.
* **Method**: `DELETE`
* **Path**: `/projects/{project_id}`
* **Query Parameters**:
  - `cascade` (boolean, optional, default = `false`)
* **cURL example**:
  ```bash
  curl -X DELETE "http://localhost:8000/projects/1?cascade=false"
  ```

---

## 2. CV Upload and Ingestion

Allows uploading resume documents in PDF, DOCX, PNG, JPG, JPEG, and WebP formats. Ingestion extracts raw text, executes NER entity parsing, and computes experience metrics in a single operation.

* **Method**: `POST`
* **Path**: `/cvs/upload`
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  - `file`: The resume file binary.
  - `extraction_method` (string): `"easyocr"` (CPU-based layout OCR) or `"minicpm-v"` (Ollama vision model). *Note: PDF and DOCX files always bypass this and use internal extractors (`pymupdf` and `python-docx` respectively).*
  - `ollama_url` (string, optional): Required if `extraction_method` is `"minicpm-v"` and file is an image.
  - `project_id` (int, optional): ID of an existing project to assign the CV to.
  - `new_project_name` (string, optional): Names a new project to create-and-assign. Takes precedence over `project_id`.
* **cURL example**:
  ```bash
  curl -X POST http://localhost:8000/cvs/upload \
    -F "file=@/path/to/resume.pdf" \
    -F "extraction_method=easyocr" \
    -F "project_id=1"
  ```
* **Response (210 Created)**:
  ```json
  {
    "id": 12,
    "filename": "resume.pdf",
    "file_type": "pdf",
    "uploaded_at": "2026-07-19T04:12:00Z",
    "status": "classified",
    "extraction_method": "pymupdf",
    "project_id": 1,
    "years_of_experience": 4.5,
    "seniority_level": "Mid-level",
    "raw_text": "extracted text of resume here...",
    "ner_model1": { "SKILLS": ["Python", "Docker"] },
    "ner_model2": { "TECHNOLOGY": ["Python", "Flask"] },
    "ner_merged": { "SKILLS": ["Python", "Docker"], "TECHNOLOGY": ["Python", "Flask"] },
    "ner_skills": { "EMAIL": ["user@example.com"], "SKILLS": ["Python", "Docker"] }
  }
  ```

---

## 3. Managing CVs & Reprocessing

### 3.1 List CVs
Retrieve a summary list of all uploaded CVs.
* **Method**: `GET`
* **Path**: `/cvs/`
* **Query Parameters**:
  - `project_id` (int, optional): Restricts output to one project.
* **cURL example**:
  ```bash
  curl -X GET "http://localhost:8000/cvs/?project_id=1"
  ```

### 3.2 Get Single CV Detail
Get raw texts, computed seniority, and complete NER dictionaries for one CV.
* **Method**: `GET`
* **Path**: `/cvs/{cv_id}`
* **cURL example**:
  ```bash
  curl -X GET http://localhost:8000/cvs/12
  ```

### 3.3 Download Original CV File
Retrieve the raw binary file for rendering or downloading. If the file was uploaded as a DOCX, this returns a PDF convert (if available) for inline rendering.
* **Method**: `GET`
* **Path**: `/cvs/{cv_id}/file`
* **cURL example**:
  ```bash
  curl -X GET http://localhost:8000/cvs/12/file -o resume_preview.pdf
  ```

### 3.4 Re-extract CV Text
Reprocess raw text extraction on an already uploaded CV (e.g. changing OCR method).
* **Method**: `POST`
* **Path**: `/cvs/{cv_id}/extract`
* **Payload**:
  ```json
  {
    "method": "minicpm-v",
    "ollama_url": "https://my-ollama-tunnel.ngrok-free.app"
  }
  ```

### 3.5 Re-classify NER Models
Runs Named Entity Recognition on pre-extracted text.
* **Method**: `POST`
* **Path**: `/cvs/{cv_id}/classify`
* **Payload**:
  ```json
  {
    "model": "both" 
  }
  ```
  *(Options for `model`: `"model1"`, `"model2"`, `"skills"`, or `"both"`)*

### 3.6 Re-assign Project Bucket
Assign the CV to a different project, unassign it, or create a project to place it in.
* **Method**: `POST`
* **Path**: `/cvs/{cv_id}/project`
* **Payload**:
  ```json
  {
    "project_id": 2,
    "new_project_name": null
  }
  ```
  *To unassign a CV and place it in the global global space, pass null or empty keys:*
  ```json
  {}
  ```

### 3.7 Delete a CV
Permanently deletes a CV and its binary data.
* **Method**: `DELETE`
* **Path**: `/cvs/{cv_id}`
* **cURL example**:
  ```bash
  curl -X DELETE http://localhost:8000/cvs/12
  ```

---

## 4. Synchronous Ranking (Local Methods)

Used to instantly rank CVs against a job description using local models (TF-IDF, SpaCy vector embedding models, SentenceTransformers, LDA, or Doc2Vec).

* **Method**: `POST`
* **Path**: `/cvs/rank`
* **Payload**:
  ```json
  {
    "jd_text": "Looking for a Python Developer with Docker and AWS experience.",
    "top_n": 5,
    "method": "sentence_transformer_hybrid",
    "project_id": 1
  }
  ```
  *Available methods: `"tfidf"`, `"lda"`, `"doc2vec"`, `"model1"`, `"model2"`, `"model1_hybrid"`, `"model2_hybrid"`, `"sentence_transformer"`, `"sentence_transformer_hybrid"`*
* **Response (200 OK)**:
  ```json
  {
    "id": 45,
    "method": "sentence_transformer_hybrid",
    "jd_ner": {
      "SKILLS": ["Python", "Docker", "AWS"]
    },
    "results": [
      {
        "id": 12,
        "filename": "resume.pdf",
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "skills": ["Python", "Docker", "Git"],
        "match_score": 78.4,
        "embedding_score": 82.6,
        "keyword_score": 70.0,
        "years_of_experience": 4.5,
        "seniority_level": "Mid-level"
      }
    ]
  }
  ```

---

## 5. Asynchronous LLM Ranking (Ollama)

Large Language Model scoring can take significant time depending on local model speeds. The platform implements an asynchronous progress pattern.

### Step 5.1: Start the Background Ranking Job
Kick off the evaluation job in a background daemon thread. Returns a `job_id` immediately.
* **Method**: `POST`
* **Path**: `/cvs/rank/llm/start`
* **Payload**:
  ```json
  {
    "jd_text": "Looking for a Python Developer with Docker and AWS experience.",
    "top_n": 10,
    "method": "llm_multilayer",
    "project_id": 1,
    "llm_model": "qwen2.5-coder:14b",
    "ollama_url": "https://tunnel1.ngrok-free.app,https://tunnel2.trycloudflare.com"
  }
  ```
  *Allowed LLM methods: `"llm"` (standard rubric), `"llm_no_rubric"`, `"llm_split_rubric"`, `"llm_multilayer"`, `"hybrid"`*
  *Note: Multiple endpoints can be passed as a comma-separated list to enable parallel load balancing.*
* **Response (200 OK)**:
  ```json
  {
    "job_id": "8bfa2e9a-cd3e-46db-9086-4e55490bc894"
  }
  ```

### Step 5.2: Poll Job Status & Progress
Client polls this endpoint periodically to display progress bars, active tunnels, or job completion states.
* **Method**: `GET`
* **Path**: `/cvs/rank/llm/{job_id}`
* **cURL example**:
  ```bash
  curl -X GET http://localhost:8000/cvs/rank/llm/8bfa2e9a-cd3e-46db-9086-4e55490bc894
  ```
* **Response (200 OK - While Running)**:
  ```json
  {
    "status": "running",
    "phase": "scoring",
    "total": 35,
    "completed": 12,
    "current_filename": "candidate_resume_14.docx",
    "tunnel_activity": {
      "https://tunnel1.ngrok-free.app": "Scoring: candidate_resume_14.docx"
    },
    "rubric": "Detailed criteria generated from Job Description...",
    "results": [],
    "error": null,
    "disabled_tunnels": []
  }
  ```
* **Response (200 OK - On Completion)**:
  ```json
  {
    "status": "done",
    "phase": "done",
    "total": 35,
    "completed": 35,
    "current_filename": null,
    "tunnel_activity": {},
    "rubric": "...",
    "results": [
      {
        "id": 12,
        "filename": "resume.pdf",
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "skills": ["Python", "Docker"],
        "match_score": 85.0,
        "llm_justification": "Candidate has 4+ years of Python experience and direct containerization exposure.",
        "years_of_experience": 4.5,
        "seniority_level": "Mid-level"
      }
    ],
    "history_id": 98,
    "error": null,
    "disabled_tunnels": []
  }
  ```

### Step 5.3: Cancel a Job
Terminates a running job immediately.
* **Method**: `POST`
* **Path**: `/cvs/rank/llm/cancel/{job_id}`
* **cURL example**:
  ```bash
  curl -X POST http://localhost:8000/cvs/rank/llm/cancel/8bfa2e9a-cd3e-46db-9086-4e55490bc894
  ```

### Step 5.4: Disable a Failed Tunnel
If one of your ngrok/cloudflare tunnels is timing out or failing during a run, disable it on the fly to prevent the engine from routing further tasks to it.
* **Method**: `POST`
* **Path**: `/cvs/rank/llm/disable-tunnel/{job_id}`
* **Query Parameters**:
  - `url`: The URL of the tunnel to disable.
* **cURL example**:
  ```bash
  curl -X POST "http://localhost:8000/cvs/rank/llm/disable-tunnel/8bfa2e9a-cd3e-46db-9086-4e55490bc894?url=https://tunnel1.ngrok-free.app"
  ```

---

## 6. Match History

Recalls previous search runs from the database.

### 6.1 List History
Retrieves previous matching runs. Scopes summary items by project if filtered.
* **Method**: `GET`
* **Path**: `/cvs/rank/history`
* **Query Parameters**:
  - `project_id` (int, optional)
* **Response (200 OK)**:
  ```json
  [
    {
      "id": 98,
      "project_id": 1,
      "project_name": "Backend Software Developer Hiring",
      "method": "llm_multilayer",
      "llm_model": "qwen2.5-coder:14b",
      "created_at": "2026-07-19T04:22:00Z",
      "jd_summary": "Looking for a Python Developer..."
    }
  ]
  ```

### 6.2 Get Detailed Match Run
Gets full logs, scores, and evaluations of a previous run.
* **Method**: `GET`
* **Path**: `/cvs/rank/history/{history_id}`
* **cURL example**:
  ```bash
  curl -X GET http://localhost:8000/cvs/rank/history/98
  ```

### 6.3 Delete a Match Run
Removes a history record from the database.
* **Method**: `DELETE`
* **Path**: `/cvs/rank/history/{history_id}`
* **cURL example**:
  ```bash
  curl -X DELETE http://localhost:8000/cvs/rank/history/98
  ```

---

## 7. Semantic Compare & Highlighting

Used for drawing the visual side-by-side keyword overlap mapping and radar chart comparison layout.

* **Method**: `POST`
* **Path**: `/cvs/{cv_id}/compare-semantic`
* **Payload**:
  ```json
  {
    "jd_text": "Looking for Python, Django, AWS, and a Bachelor's Degree in London.",
    "method": "sentence_transformer_hybrid"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "jd_skills": ["python", "django"],
    "cv_skills": ["python", "flask", "django"],
    "jd_techs": ["aws"],
    "cv_techs": ["aws", "gcp"],
    "jd_tools": [],
    "cv_tools": ["git", "docker"],
    "jd_degrees": ["bachelor"],
    "cv_degrees": ["bachelor of science"],
    "jd_locations": ["london"],
    "cv_locations": ["london"],
    "jd_designations": ["developer"],
    "cv_designations": ["software engineer", "developer"],
    "matched_skills": ["python", "django"],
    "matched_techs": ["aws"],
    "matched_tools": [],
    "matched_degrees": ["bachelor"],
    "matched_locations": ["london"],
    "matched_designations": ["developer"],
    "scores": {
      "skills": 100.0,
      "technologies": 100.0,
      "tools": 0.0,
      "degrees": 100.0,
      "locations": 100.0,
      "designations": 100.0
    }
  }
  ```

---

## 8. Python Code Examples

This Python script demonstrates how to upload a folder of CVs and trigger an asynchronous LLM job to score them.

```python
import time
import requests

BASE_URL = "http://localhost:8000"

def create_project(name):
    url = f"{BASE_URL}/projects/"
    r = requests.post(url, json={"name": name})
    r.raise_for_status()
    project = r.json()
    print(f"Created project: {project['name']} (ID: {project['id']})")
    return project["id"]

def upload_cv(file_path, project_id):
    url = f"{BASE_URL}/cvs/upload"
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        data = {
            "extraction_method": "easyocr",
            "project_id": project_id
        }
        r = requests.post(url, files=files, data=data)
        r.raise_for_status()
        cv = r.json()
        print(f"Uploaded CV: {cv['filename']} (ID: {cv['id']})")
        return cv

def trigger_llm_ranking(project_id, jd_text, ollama_url, model):
    url = f"{BASE_URL}/cvs/rank/llm/start"
    payload = {
        "jd_text": jd_text,
        "top_n": 5,
        "method": "llm_multilayer",
        "project_id": project_id,
        "llm_model": model,
        "ollama_url": ollama_url
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    job_id = r.json()["job_id"]
    print(f"Triggered LLM ranker job: {job_id}")
    return job_id

def poll_llm_job(job_id):
    url = f"{BASE_URL}/cvs/rank/llm/{job_id}"
    while True:
        r = requests.get(url)
        r.raise_for_status()
        status_info = r.json()
        status = status_info.get("status")
        
        if status == "done":
            print("\nJob completed successfully!")
            return status_info.get("results")
        elif status == "error":
            raise RuntimeError(f"Job failed: {status_info.get('error')}")
        else:
            completed = status_info.get("completed", 0)
            total = status_info.get("total", 0)
            phase = status_info.get("phase", "running")
            print(f"Progress: [{completed}/{total}] - Phase: {phase} ...")
            time.sleep(5)

if __name__ == "__main__":
    # 1. Setup a Project
    project_id = create_project("Python Developer Role")

    # 2. Upload candidate resumes
    # upload_cv("candidate1.pdf", project_id)
    # upload_cv("candidate2.pdf", project_id)

    # 3. Define Job Description and LLM properties
    job_requirements = """
    We are seeking a Backend Software Developer.
    Must have 3+ years experience with Python, FastAPI, and Docker.
    """
    ollama_endpoint = "https://your-ngrok-tunnel.ngrok-free.app"
    model_tag = "qwen2.5-coder:14b"

    # 4. Trigger Ranking Job
    try:
        job_id = trigger_llm_ranking(project_id, job_requirements, ollama_endpoint, model_tag)
        
        # 5. Monitor and print final rankings
        results = poll_llm_job(job_id)
        print("\n--- Final Rankings ---")
        for idx, item in enumerate(results):
            print(f"{idx+1}. {item['filename']} | Score: {item['match_score']}")
            print(f"   Reason: {item['llm_justification']}\n")
    except Exception as e:
        print(f"Error executing ranking flow: {e}")
```
