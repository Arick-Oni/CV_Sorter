# CV Platform — Architecture, Pipeline, and Developer Documentation

This is a comprehensive technical documentation for the **CV Platform**. This system is an end-to-end recruitment tool designed to ingest, process, parse, analyze, and rank candidate resumes (CVs) against job descriptions using a variety of machine learning, NLP, and Large Language Model (LLM) techniques.

For interactive integration details, cURL examples, request-response payloads, and Python scripts, please see the [API Usage & Integration Guide](API_USAGE_GUIDE.md).


---

## 1. System Architecture

The CV Platform uses a decoupled **FastAPI** backend and a **Vanilla JS/CSS/HTML5** frontend, using SQLite/PostgreSQL database storage.

```mermaid
graph TD
    A[Frontend: index.html / app.js] -->|Upload CV File| B(FastAPI Backend: routers/cvs.py)
    A -->|Request Match / Rank| B
    B -->|OCR / Text Extraction| C[services/ocr.py]
    B -->|NER / Classification| D[services/ner.py]
    B -->|Ranking Algorithms| E[services/ranking.py]
    B -->|LLM Judge & Rubric Jobs| F[services/llm_ranking.py]
    
    C -->|EasyOCR / PyMuPDF / docx| G[(SQLite/PostgreSQL DB)]
    C -->|MiniCPM-V via Ollama| H[External Ollama API]
    D -->|spaCy / Regex / skills.jsonl| G
    E -->|TF-IDF / SentenceTransformers / LDA / Doc2Vec| G
    F -->|Parallel / API Tunnels| H
    
    B -->|Manage States & History| G
```

### 1.1 Key Modules
- **`backend/main.py`**: Application entry point, configures CORS, serves static frontend files, and ensures schema migrations are run on startup.
- **`backend/database.py`**: Configures the database engine (PostgreSQL or SQLite) and provides session lifecycle management.
- **`backend/models.py`**: Defines database tables and schema using SQLAlchemy.
- **`backend/schemas.py`**: Holds Pydantic validation schemas for API inputs and outputs.
- **`backend/routers/`**:
  - `projects.py`: Handles project bucket creation, listing, and deletion.
  - `cvs.py`: Core logic for uploading, re-extracting, re-classifying, assigning projects, semantic comparison, and ranking.
- **`backend/services/`**:
  - `ocr.py`: Document ingestion and OCR routing.
  - `ner.py`: Extraction of skills, personal info, work experience estimation, and seniority classification.
  - `ranking.py`: Classical and embedding-based ranking algorithms.
  - `llm_ranking.py`: Advanced LLM-as-a-judge prompts, rubric-building, and batch scoring.
  - `rank_jobs.py`: In-memory multi-threaded background progress tracker for long-running LLM tasks.

---

## 2. Database Schema (`backend/models.py`)

The platform structures data into three primary tables:

### 2.1 `Project`
Acts as a workspace bucket to group CVs.
- `id` (Integer, Primary Key): Unique identifier.
- `name` (String, Unique): Project name.
- `created_at` (DateTime): Creation timestamp.
- *Relationships*: Has a one-to-many relationship with `CV` records.

### 2.2 `CV`
Contains original document assets, extracted texts, and parsed metadata.
- `id` (Integer, Primary Key): Unique identifier.
- `filename` (String): Original file name.
- `file_type` (String): Extension (`pdf`, `docx`, `png`, `jpg`, etc.).
- `file_data` (LargeBinary): Stored raw file bytes.
- `status` (String): Pipeline state (`uploaded` → `extracted` → `classified`).
- `extraction_method` (String): Method used (`pymupdf`, `python-docx`, `easyocr`, or `minicpm-v`).
- `raw_text` (Text): The full extracted text.
- `ner_model1` (JSON): Entity groups extracted using custom Spacy `model-best`.
- `ner_model2` (JSON): Entity groups extracted using custom Spacy `model-best-2`.
- `ner_merged` (JSON): Intelligent blend of best entities from both models.
- `ner_skills` (JSON): Skill taxonomy entities extracted via Rule-based EntityRuler and Regexes (Name, Email, Phone, Skills, Companies, Locations).
- `years_of_experience` (Float): Computed work duration in years.
- `seniority_level` (String): Heuristically assigned seniority ("Junior", "Mid-level", "Senior", "Lead / Principal", "Executive").
- `project_id` (Integer, Foreign Key): Assigned project. Set to `ON DELETE SET NULL` so CVs are not lost when a project is deleted.

### 2.3 `MatchHistory`
Logs queries and results of ranking operations.
- `id` (Integer, Primary Key): Unique identifier.
- `project_id` (Integer, Foreign Key, Nullable): Scopes history item to a project.
- `jd_text` (Text): The job description text.
- `rubric` (Text, Nullable): The built LLM rubric (if applicable).
- `method` (String): The ranking strategy used.
- `llm_model` (String, Nullable): The model name used for LLM runs.
- `created_at` (DateTime): Timestamp of the search run.
- `results` (JSON): Lightweight array of scored items (contains scores, IDs, and filenames).

---

## 3. Data Processing & NER Pipeline

```
  [ Upload Document ]
          │
          ▼
┌──────────────────┐
│  Text Extractor  │◄── PDF (Pymupdf) / DOCX (Python-docx) / Images (EasyOCR / MiniCPM-V)
└──────────────────┘
          │
          ▼
┌──────────────────┐
│   NER Engines    │◄── Custom spaCy, skills.jsonl ruler, Phone/Email Regexes
└──────────────────┘
          │
          ▼
┌──────────────────┐
│ Experience/Level │◄── Parse Date Ranges (Ignore Education) & Classify Seniority
└──────────────────┘
```

### 3.1 Text Extraction (`backend/services/ocr.py`)
Depending on the file format, the system routes processing accordingly:
1. **PDF**: Attempts digital text extraction using PyMuPDF (`fitz`). If extracted text is less than 100 characters, it falls back to rendering page images and OCRing them via EasyOCR.
2. **DOCX**: Extracts text paragraph by paragraph and cell by cell from tables using `python-docx`. It also performs an optional conversion to PDF using `docx2pdf` (on Windows systems with Word installed) to allow in-browser previewing.
3. **Images (PNG, JPG, WebP)**: 
   - **EasyOCR**: Local execution. Extracts bounding boxes and applies a custom `_layout_text` algorithm to reconstruct the layout. It groups detections by visual lines (Y coordinate) and sorts them left-to-right (X coordinate) to accurately preserve multi-column formats.
   - **MiniCPM-V**: Visual LLM run via Ollama (configured via external tunnel URL). Encodes the image to Base64 and transcribes layout text deterministically at `temperature = 1`.

### 3.2 Named Entity Recognition (NER) (`backend/services/ner.py`)
The pipeline runs four concurrent parser configurations:
- **`model-best` & `model-best-2`**: Custom-trained Spacy pipelines designed to identify resume entities.
- **Winner-Take-All Merge (`ner_merged`)**: Evaluates labels across both custom models and routes to the model with the higher F1-score for that specific category. The default winner map is defined in `_LABEL_WINNER`.
- **Skills Entity Ruler (`ner_skills`)**: Utilizes Spacy's `EntityRuler` seeded with a custom taxonomy file ([skills.jsonl](file:///c:/Users/arick.sarkar/Desktop/Save%20The%20Children%20Techhub/Fourth%20Week/CV%20sorting/cv-platform/resources/skills.jsonl)) to match technical keywords.
- **Regex Detectors**: Extracts emails and phone numbers safely from raw strings.

### 3.3 Experience and Seniority Classifier
A heuristic module calculates experience:
1. **Education Filtering**: Strips headers resembling educational sections (University, degree, school, college, etc.) so that graduation years are not incorrectly flagged as professional career dates.
2. **Explicit Mentions**: Matches numeric phrases like `(\d+)\+ years of experience` or `Experience: (\d+) years`.
3. **Timeline Accumulation**: Parses dates and intervals (e.g., `Jan 2018 - Aug 2021` or `2019 - Present`), merges overlapping intervals to avoid double-counting, and sums the total duration.
4. **Seniority Allocation**: Determines seniority dynamically based on the final year score and keyword matching:
   - **>= 10 years**: Executive (if "director/VP/CEO" found), Lead/Principal (if "lead/manager" found), else Senior.
   - **>= 5 years**: Executive, Lead/Principal, or Senior.
   - **>= 2 years**: Lead/Principal, Mid-level, or Junior (if explicitly tagged).
   - **< 2 years**: Senior (only if explicitly flagged), else Junior.

---

## 4. Ranking & Matching Strategies (`backend/services/ranking.py` & `llm_ranking.py`)

The platform implements 14 different matching strategies, divided into three tiers:

| Tier | Method Key | Algorithm Description |
| :--- | :--- | :--- |
| **Statistical & Contextual** | `tfidf` | Cosine similarity on TF-IDF vectors of lemmatized text (stop words removed). |
| | `lda` | Latent Dirichlet Allocation (5 topics) to find conceptual document alignment. |
| | `doc2vec` | Trains a mini Doc2Vec neural model (50 dimensions) on fly to match document context vectors. |
| **Embeddings & Local ML** | `model1` / `model2` | Direct cosine similarity of SpaCy `doc.vector` embeddings. |
| | `model1_hybrid` / `model2_hybrid` | Blends `2/3` embedding similarity and `1/3` NER keyword matching overlap between the JD and CV. |
| | `sentence_transformer` | Generates semantic vectors using local Hugging Face `all-MiniLM-L6-v2`. |
| | `sentence_transformer_hybrid` | Blends SentenceTransformer embeddings (`2/3`) and merged custom NER keywords (`1/3`). |
| **LLM-as-a-Judge (Ollama)** | `llm` | Builds a text scoring rubric from the JD, then scores CVs (0-100) one by one. |
| | `llm_no_rubric` | Scores candidates directly against the raw JD, skipping rubric construction. |
| | `llm_split_rubric` | Generates 5 distinct criteria and weights, scores candidates on each individually, and aggregates. |
| | `llm_multilayer` | Runs a **3-stage pipeline**: <br>1. **Filter**: Removes template/empty files.<br>2. **Batch Score**: Scores candidates in parallel batches of 3.<br>3. **Re-rank**: Side-by-side relative comparisons of the top 10 profiles. |
| | `hybrid` | Blends multiple approaches: `50% LLM Rubric + 20% model-best-2 + 20% model-best + 10% TF-IDF`. |

---

## 5. Parallel LLM Inference & Tunnel Support

To speed up heavy LLM operations (such as scoring 50+ resumes one-by-one, which can take several minutes), the platform supports:
- **Asynchronous Background Workers**: When `/cvs/rank/llm/start` is triggered, the server spawns a daemon thread `_run_llm_ranking_job` and returns a `job_id` immediately, allowing the UI to poll status asynchronously.
- **Parallel Tunnel Load-Balancing**: In `llm-ollama-url`, users can supply a comma-separated list of multiple URLs (e.g. cloudflare tunnels, ngrok instances, or secondary Colab runtimes). The backend distributes scoring tasks across a queue of these tunnels using thread pools, achieving significant linear speedups.
- **Fail-safe Tunnels**: Active connections are tracked in `tunnel_activity`. If a tunnel times out or goes offline, developers can call the `/disable-tunnel` endpoint to exclude it from rotation.

---

## 6. Frontend Interface Features

The user interface is structured into three main views:

1. **Upload Tab**:
   - File drag-and-drop or select.
   - Assignment to existing projects or instant creation of new ones.
   - Configurable text extraction methods (EasyOCR vs MiniCPM-V).
2. **Library Tab**:
   - Tabular overview of CVs with metadata (ID, status, extraction method, date).
   - **CV Action Modal**:
     - View original rendering (embedded PDF, image, or DOCX download).
     - Inspect raw parsed text or tabbed NER outputs (Model-Best, Model-Best-2, Merged, and Skills).
     - Run re-extraction or re-classification on the fly.
     - Re-assign project tags or delete records.
3. **JD Match Tab**:
   - Match history side panel allowing recruiters to reload previous searches.
   - Expandable / collapsible JD input panels with file upload capabilities to extract requirements from PDF/DOCX job postings.
   - Multi-tier matching selector (TF-IDF, Embeddings, LLM-as-a-judge options).
   - Dynamic parameter fields for Ollama URL, customized models (e.g. Qwen, Llama), and parallel tunnels.
   - Live job progress logs detailing rubric construction, current file execution, and active tunnel activity.
   - **Match Analytics (Chart.js)**: Automatically renders a vertical bar chart displaying score distributions to visually separate high-tier candidates.
   - **Consensus Matcher**: Compares model rankings against human-annotator rankings. Accepts comma-separated values (e.g., `24, 25, 21, 23`) and reports top-N overlap metrics alongside a list of matched and missing items.
   - **Semantic Compare Modal**: Shows a side-by-side keyword match table mapping requirements to resume details. Displays a Spider (Radar) chart mapping category coverages (e.g., matching skills, designations, degree requirements).

---

## 7. Developer & Operations Guide

### 7.1 Requirements
Make sure Python 3.10+ is installed. Install package dependencies:
```bash
pip install -r requirements.txt
```

Verify that spaCy model paths are loaded. If you are using pre-trained pipelines, download them:
```bash
python -m spacy download en_core_web_sm
```

### 7.2 Configuration (`.env`)
Create a `.env` file in the project root:
```env
DATABASE_URL=sqlite:///./cv_platform.db
# DATABASE_URL=postgresql://postgres:password@localhost:5432/cv_platform

# Paths to trained spaCy models (absolute or relative)
MODEL1_PATH=C:/Users/arick.sarkar/Desktop/Save The Children Techhub/Fourth Week/CV sorting/Collaborative/model-best
MODEL2_PATH=C:/Users/arick.sarkar/Desktop/Save The Children Techhub/Fourth Week/CV sorting/Collaborative/model-best 2/model-best

# Vision LLM configuration
OLLAMA_NGROK_URL=https://your-ngrok-url.ngrok-free.app
MINICPM_MODEL=minicpm-v
```

### 7.3 Running the Application
To run the server locally:
```bash
python run.py
```
This spawns a **FastAPI** application via Uvicorn on `http://localhost:8000`. Open this URL in any browser to launch the frontend.
