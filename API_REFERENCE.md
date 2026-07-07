# CV Platform — API Reference

Base URL (local dev): `http://localhost:8000`
The frontend (`frontend/index.html` + `app.js`) calls these same-origin, so no auth/CORS config is needed beyond the wildcard CORS already enabled in `backend/main.py`.

All request/response bodies are JSON unless noted (file uploads use `multipart/form-data`).

---

## Contents
- [App / Health](#app--health)
- [Projects](#projects-projects)
- [CVs](#cvs-cvs)

---

## App / Health

### `GET /`
Serves the frontend `index.html`.

### `GET /health`
Liveness check.
- **Response** `200`: `{"status": "ok"}`

```bash
curl http://localhost:8000/health
```

---

## Projects (`/projects`)

Projects are simple named buckets used to group CVs. Defined in `backend/routers/projects.py`.

### `GET /projects/`
List all projects, alphabetical by name.
- **Response** `200`: array of `ProjectOut` — `{id, name, created_at}`

```bash
curl http://localhost:8000/projects/
```

### `POST /projects/`
Create a project. If a project with the same name already exists, returns that existing project instead of erroring (idempotent create).
- **Body**: `ProjectCreate` — `{"name": "Q3 Data Analyst Hiring"}`
- **Response** `201`: `ProjectOut`
- **Errors**: `400` if `name` is blank/whitespace-only

```bash
curl -X POST http://localhost:8000/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Q3 Data Analyst Hiring"}'
```

### `DELETE /projects/{project_id}`
Delete a project. CVs assigned to it are **not** deleted — they're unassigned (`project_id` set to `null`) so they remain visible in the global view.
- **Path param**: `project_id` (int)
- **Response** `204`: no body
- **Errors**: `404` if project not found

```bash
curl -X DELETE http://localhost:8000/projects/3
```

---

## CVs (`/cvs`)

Defined in `backend/routers/cvs.py`. A CV record stores the original file, extracted raw text, and NER output from three approaches: `ner_model1` / `ner_model2` (two trained spaCy models), `ner_merged` (per-label best-of-both, see `_LABEL_WINNER` in `backend/services/ner.py`), and `ner_skills` (lightweight `en_core_web_sm` + `skills.jsonl` EntityRuler extracting NAME/EMAIL/PHONE/SKILLS/COMPANIES/LOCATIONS).

### `POST /cvs/upload`
Upload a CV file, extract its text, and run all NER models against it in one call.
- **Body** (`multipart/form-data`):
  | field | type | required | notes |
  |---|---|---|---|
  | `file` | file | yes | `.png .jpg .jpeg .webp .pdf .docx` |
  | `extraction_method` | string | yes | `"easyocr"` or `"minicpm-v"` (only applies to image files — PDF/DOCX always use their own extractor regardless of this value) |
  | `ollama_url` | string | only if `minicpm-v` + image | Ollama/ngrok/cloudflare URL for the vision LLM |
  | `project_id` | int | no | assign to an existing project |
  | `new_project_name` | string | no | create-and-assign a new project (takes precedence over `project_id`) |
- **Response** `201`: `CVDetail` (full record, including all NER fields)
- **Errors**: `400` unsupported extension, or `minicpm-v` selected for an image without `ollama_url`

```bash
curl -X POST http://localhost:8000/cvs/upload \
  -F "file=@resume.pdf" \
  -F "extraction_method=easyocr" \
  -F "project_id=3"
```

### `GET /cvs/`
List CVs (summary — no raw text or NER payloads), most recently uploaded first.
- **Query param**: `project_id` (int, optional) — filter to one project; omit for all projects
- **Response** `200`: array of `CVSummary` — `{id, filename, file_type, uploaded_at, status, extraction_method, project_id}`

```bash
curl "http://localhost:8000/cvs/?project_id=3"
```

### `POST /cvs/rank`
Rank all CVs (optionally scoped to a project) against a job description.
- **Body**: `RankRequest`
  | field | type | default | notes |
  |---|---|---|---|
  | `jd_text` | string | — | full job description text |
  | `top_n` | int | `20` | max rows returned |
  | `method` | string | `"tfidf"` | one of `tfidf`, `model1`, `model2`, `model1_hybrid`, `model2_hybrid` (see below) |
  | `project_id` | int/null | `null` | restrict to one project; `null` = all projects |
- **Ranking methods**:
  - `tfidf` — TF-IDF cosine similarity on lemmatized text (no NER involved).
  - `model1` / `model2` — cosine similarity of spaCy `doc.vector` embeddings from that model.
  - `model1_hybrid` / `model2_hybrid` — `2/3 × embedding similarity + 1/3 × NER-keyword overlap` (% of the JD's NER values found anywhere in the CV's NER output for that model).
- **Response** `200`:
  ```json
  {
    "method": "model1_hybrid",
    "jd_ner": { "TECHNOLOGY": ["AWS", "Python"], "...": ["..."] },
    "results": [
      {
        "id": 12, "filename": "resume.pdf",
        "raw_text": "...", "name": "...", "email": "...",
        "skills": ["Python", "AWS"],
        "ner_model1": {"...": ["..."]},
        "ner_model2": {"...": ["..."]},
        "ner_merged": {"...": ["..."]},
        "match_score": 42.1,
        "embedding_score": 38.0,
        "keyword_score": 50.0
      }
    ]
  }
  ```
  `jd_ner` is computed from whichever model backs the chosen `method` (model1 for `model1`/`model1_hybrid`, model2 for `model2`/`model2_hybrid`, merged model1+model2 for `tfidf`). `embedding_score` / `keyword_score` are only present for `_hybrid` methods. `results` is sorted by `match_score` descending and capped at `top_n`.

```bash
curl -X POST http://localhost:8000/cvs/rank \
  -H "Content-Type: application/json" \
  -d '{"jd_text": "Looking for a Python developer with AWS experience.", "top_n": 10, "method": "model1_hybrid"}'
```

### `GET /cvs/{cv_id}`
Fetch one CV's full detail, including raw text and all NER outputs.
- **Path param**: `cv_id` (int)
- **Response** `200`: `CVDetail`
- **Errors**: `404` if not found

```bash
curl http://localhost:8000/cvs/12
```

### `GET /cvs/{cv_id}/file`
Stream the original uploaded file (or the DOCX→PDF conversion, if one was made at upload time) for inline preview/download.
- **Path param**: `cv_id` (int)
- **Response** `200`: raw file bytes with the appropriate `Content-Type` (`application/pdf`, `image/png`, etc.) and `Content-Disposition: inline`
- **Errors**: `404` if not found

```bash
curl http://localhost:8000/cvs/12/file -o resume.pdf
```

### `POST /cvs/jd-extract`
Extract text from a job-description file (PDF/image/DOCX) without storing anything — used to populate the JD textarea in the UI.
- **Body** (`multipart/form-data`): `file`
- **Response** `200`: `{"text": "extracted job description text..."}`
- **Errors**: `400` unsupported extension

```bash
curl -X POST http://localhost:8000/cvs/jd-extract -F "file=@jd.pdf"
```

### `POST /cvs/{cv_id}/extract`
Re-run text extraction on an already-uploaded CV (e.g. to try a different OCR method). Does **not** re-run NER — call `/classify` afterward for that.
- **Path param**: `cv_id` (int)
- **Body**: `ExtractRequest` — `{"method": "easyocr" | "minicpm-v", "ollama_url": "..." }` (`ollama_url` required for `minicpm-v` on image files)
- **Response** `200`: `CVDetail` (status becomes `"extracted"`)
- **Errors**: `404` not found, `400` missing `ollama_url` for `minicpm-v`

```bash
curl -X POST http://localhost:8000/cvs/12/extract \
  -H "Content-Type: application/json" \
  -d '{"method": "easyocr"}'
```

### `POST /cvs/{cv_id}/classify`
Re-run NER on a CV's existing raw text.
- **Path param**: `cv_id` (int)
- **Body**: `ClassifyRequest` — `{"model": "model1" | "model2" | "skills" | "both"}` (`"both"` runs model1 + model2 + re-merges; it does **not** re-run the skills extractor — pass `"skills"` explicitly for that)
- **Response** `200`: `CVDetail` (status becomes `"classified"`)
- **Errors**: `404` not found, `400` if no raw text has been extracted yet

```bash
curl -X POST http://localhost:8000/cvs/12/classify \
  -H "Content-Type: application/json" \
  -d '{"model": "both"}'
```

### `POST /cvs/{cv_id}/project`
Move a CV to a different project, unassign it, or create-and-assign a new project.
- **Path param**: `cv_id` (int)
- **Body**: `AssignProjectRequest` — `{"project_id": 3}` or `{"new_project_name": "New Project"}` or `{}` to unassign
- **Response** `200`: `CVDetail`
- **Errors**: `404` CV not found, `400` if `project_id` doesn't exist

```bash
curl -X POST http://localhost:8000/cvs/12/project \
  -H "Content-Type: application/json" \
  -d '{"project_id": 3}'
```

### `DELETE /cvs/{cv_id}`
Permanently delete a CV (including its stored file bytes).
- **Path param**: `cv_id` (int)
- **Response** `204`: no body
- **Errors**: `404` if not found

```bash
curl -X DELETE http://localhost:8000/cvs/12
```

---

## Schemas quick reference (`backend/schemas.py`)

| Schema | Fields |
|---|---|
| `ProjectOut` | `id, name, created_at` |
| `ProjectCreate` | `name` |
| `CVSummary` | `id, filename, file_type, uploaded_at, status, extraction_method, project_id` |
| `CVDetail` | `CVSummary` + `raw_text, ner_model1, ner_model2, ner_merged, ner_skills` |
| `ExtractRequest` | `method, ollama_url?` |
| `ClassifyRequest` | `model` |
| `AssignProjectRequest` | `project_id?, new_project_name?` |
| `RankRequest` | `jd_text, top_n=20, method="tfidf", project_id?` |

`status` values: `uploaded` → `extracted` → `classified`.
