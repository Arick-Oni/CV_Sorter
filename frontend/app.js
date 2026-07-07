const API = '';   // same origin

// ── Utilities ─────────────────────────────────────────────────────────────────
function setStatus(el, msg, type = 'info') {
  el.textContent = msg;
  el.className = `status ${type}`;
  el.style.display = '';
}

function hideEl(el) { el.style.display = 'none'; }
function showEl(el, display = 'block') { el.style.display = display; }

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

function fmtDate(iso) {
  return new Date(iso).toLocaleString();
}

function statusBadge(s) {
  const map = { uploaded: 'gray', extracted: 'yellow', classified: 'green' };
  return `<span class="badge badge-${map[s] || 'gray'}">${s}</span>`;
}

function methodBadge(m) {
  if (!m) return '--';
  const map = {
    'easyocr':     ['badge-blue',   'EasyOCR'],
    'minicpm-v':   ['badge-yellow', 'MiniCPM-V'],
    'pymupdf':     ['badge-green',  'PyMuPDF'],
    'python-docx': ['badge-gray',   'python-docx'],
  };
  const [cls, label] = map[m] || ['badge-gray', m];
  return `<span class="badge ${cls}">${label}</span>`;
}

function renderNer(container, nerData) {
  if (!nerData || !Object.keys(nerData).length) {
    container.innerHTML = '<p style="color:#6b7280;padding:.5rem">No NER data.</p>';
    return;
  }
  const rows = Object.entries(nerData)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([label, vals]) => {
      const chips = (Array.isArray(vals) ? vals : [vals])
        .map(v => `<span class="ner-chip">${v}</span>`).join('');
      return `<tr><td><strong>${label}</strong></td><td><div class="ner-vals">${chips}</div></td></tr>`;
    }).join('');
  container.innerHTML = `<table class="ner-table"><thead><tr><th>Label</th><th>Values</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function safeJson(res) {
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { detail: text || res.statusText }; }
}

// ── Projects ──────────────────────────────────────────────────────────────────
let projects = [];               // [{id, name, created_at}, ...]
let currentProjectId = null;     // null = "All Projects" (global view)

function populateProjectSelect(selectEl, { includeAll = false, includeNew = false, selected = null } = {}) {
  const opts = [];
  opts.push(includeAll
    ? `<option value="">All Projects (Global)</option>`
    : `<option value="">Unassigned (global only)</option>`);
  projects.forEach(p => opts.push(`<option value="${p.id}">${p.name}</option>`));
  if (includeNew) opts.push(`<option value="__new__">+ Create new project...</option>`);
  selectEl.innerHTML = opts.join('');
  // falls back to the blank/default option if `selected` no longer matches any project
  selectEl.value = selected != null ? String(selected) : '';
}

async function loadProjects() {
  const res = await fetch(`${API}/projects/`);
  projects = await res.json();

  populateProjectSelect(document.getElementById('global-project-select'), {
    includeAll: true, selected: currentProjectId,
  });
  populateProjectSelect(document.getElementById('upload-project-select'), {
    includeNew: true, selected: currentProjectId,
  });
}

document.getElementById('global-project-select').addEventListener('change', function () {
  currentProjectId = this.value ? Number(this.value) : null;
  // mirror the active project into the upload form as the default tag for new CVs
  const uploadSelect = document.getElementById('upload-project-select');
  const targetVal = currentProjectId != null ? String(currentProjectId) : '';
  if ([...uploadSelect.options].some(o => o.value === targetVal)) {
    uploadSelect.value = targetVal;
    document.getElementById('upload-new-project-group').style.display = 'none';
  }
  if (document.getElementById('tab-library').style.display !== 'none') loadLibrary();
});

document.getElementById('new-project-btn').addEventListener('click', async () => {
  const name = prompt('New project name:');
  if (!name || !name.trim()) return;
  try {
    const res = await fetch(`${API}/projects/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() }),
    });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || 'Failed to create project');
    currentProjectId = data.id;
    await loadProjects();
    document.getElementById('global-project-select').value = String(data.id);
    document.getElementById('upload-project-select').value = String(data.id);
    if (document.getElementById('tab-library').style.display !== 'none') loadLibrary();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
});

document.getElementById('upload-project-select').addEventListener('change', function () {
  document.getElementById('upload-new-project-group').style.display = this.value === '__new__' ? 'block' : 'none';
});

loadProjects();

// ── Tab switching ─────────────────────────────────────────────────────────────
const TAB_IDS = ['upload', 'library', 'rank'];

function switchTab(targetTab) {
  TAB_IDS.forEach(id => {
    const el = document.getElementById(`tab-${id}`);
    if (el) el.style.display = id === targetTab ? 'block' : 'none';
  });
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === targetTab);
  });
  if (targetTab === 'library') loadLibrary();
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// Init: show only upload
switchTab('upload');

// ── Upload form ───────────────────────────────────────────────────────────────
const extractionMethod = document.getElementById('extraction-method');
const ollamaUrlGroup   = document.getElementById('ollama-url-group');

extractionMethod.addEventListener('change', () => {
  ollamaUrlGroup.style.display = extractionMethod.value === 'minicpm-v' ? 'block' : 'none';
});

document.getElementById('upload-form').addEventListener('submit', async e => {
  e.preventDefault();
  const statusEl = document.getElementById('upload-status');
  const btn = document.getElementById('upload-btn');
  const file = document.getElementById('cv-file').files[0];
  if (!file) return;

  const projectSelectVal = document.getElementById('upload-project-select').value;

  const fd = new FormData();
  fd.append('file', file);
  fd.append('extraction_method', extractionMethod.value);
  if (extractionMethod.value === 'minicpm-v') {
    fd.append('ollama_url', document.getElementById('ollama-url').value);
  }
  if (projectSelectVal === '__new__') {
    const newName = document.getElementById('upload-new-project-name').value.trim();
    if (!newName) { setStatus(document.getElementById('upload-status'), 'Enter a name for the new project', 'error'); return; }
    fd.append('new_project_name', newName);
  } else if (projectSelectVal) {
    fd.append('project_id', projectSelectVal);
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Processing...';
  setStatus(statusEl, 'Uploading and processing CV - this may take a moment...', 'info');

  try {
    const res = await fetch(`${API}/cvs/upload`, { method: 'POST', body: fd });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    setStatus(statusEl, `CV uploaded and classified (ID: ${data.id})`, 'success');
    e.target.reset();
    ollamaUrlGroup.style.display = 'none';
    document.getElementById('upload-new-project-group').style.display = 'none';
    if (data.project_id && !projects.some(p => p.id === data.project_id)) await loadProjects();
    document.getElementById('upload-project-select').value = currentProjectId || '';
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Process';
  }
});

// ── Library ───────────────────────────────────────────────────────────────────
function projectName(projectId) {
  if (!projectId) return '<span style="color:#9ca3af">Unassigned</span>';
  const p = projects.find(p => p.id === projectId);
  return p ? p.name : '<span style="color:#9ca3af">Unknown</span>';
}

async function loadLibrary() {
  const tbody = document.getElementById('cv-tbody');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#6b7280;padding:1.5rem">Loading...</td></tr>';
  try {
    const qs  = currentProjectId ? `?project_id=${currentProjectId}` : '';
    const res  = await fetch(`${API}/cvs/${qs}`);
    const cvs  = await res.json();
    if (!cvs.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#6b7280;padding:1.5rem">No CVs found for this view.</td></tr>';
      return;
    }
    tbody.innerHTML = cvs.map(cv => `
      <tr>
        <td>${cv.id}</td>
        <td>${cv.filename}</td>
        <td>${projectName(cv.project_id)}</td>
        <td>${fmtDate(cv.uploaded_at)}</td>
        <td>${methodBadge(cv.extraction_method)}</td>
        <td>${statusBadge(cv.status)}</td>
        <td class="row-actions">
          <button class="btn-secondary" onclick="openDetail(${cv.id})">View</button>
          <button class="btn-danger" onclick="deleteCv(${cv.id})">Delete</button>
        </td>
      </tr>`).join('');
  } catch {
    tbody.innerHTML = '<tr><td colspan="7" style="color:#b91c1c;padding:1rem">Failed to load CVs.</td></tr>';
  }
}

document.getElementById('refresh-btn').addEventListener('click', loadLibrary);

async function deleteCv(id) {
  if (!confirm(`Delete CV #${id}?`)) return;
  await fetch(`${API}/cvs/${id}`, { method: 'DELETE' });
  loadLibrary();
}

// ── Modal ─────────────────────────────────────────────────────────────────────
let currentCvId = null;

function switchMtab(targetMtab) {
  document.querySelectorAll('.mtab').forEach(b => {
    b.classList.toggle('active', b.dataset.mtab === targetMtab);
  });
  document.querySelectorAll('.mtab-panel').forEach(p => {
    p.style.display = p.id === `mtab-${targetMtab}` ? 'block' : 'none';
  });
}

document.querySelectorAll('.mtab').forEach(btn => {
  btn.addEventListener('click', () => switchMtab(btn.dataset.mtab));
});

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('modal').style.display = 'none';
  currentCvId = null;
});

document.getElementById('re-extract-method').addEventListener('change', function () {
  document.getElementById('re-ollama-url').style.display =
    this.value === 'minicpm-v' ? 'inline-block' : 'none';
});

async function openDetail(id) {
  currentCvId = id;
  const res = await fetch(`${API}/cvs/${id}`);
  const cv  = await res.json();

  document.getElementById('modal-title').textContent = `CV #${cv.id} - ${cv.filename}`;
  document.getElementById('raw-text-pre').textContent = cv.raw_text || '(not extracted yet)';
  populateProjectSelect(document.getElementById('modal-project-select'), {
    includeNew: true, selected: cv.project_id,
  });
  document.getElementById('modal-new-project-name').style.display = 'none';
  renderNer(document.getElementById('ner-m1'),     cv.ner_model1);
  renderNer(document.getElementById('ner-m2'),     cv.ner_model2);
  renderNer(document.getElementById('ner-merged'), cv.ner_merged);
  renderNer(document.getElementById('ner-skills'), cv.ner_skills);

  // Original file preview - show correct element based on file type
  const fileUrl = `${API}/cvs/${id}/file`;
  const imgEl   = document.getElementById('cv-img');
  const pdfEl   = document.getElementById('cv-pdf-embed');
  const docxEl  = document.getElementById('cv-docx-msg');
  const isPdf   = cv.file_type === 'pdf';
  const isDocx  = cv.file_type === 'docx';
  imgEl.style.display  = (!isPdf && !isDocx) ? 'block' : 'none';
  pdfEl.style.display  = isPdf  ? 'block' : 'none';
  docxEl.style.display = isDocx ? 'block' : 'none';
  if (isPdf)       pdfEl.src = fileUrl;
  else if (isDocx) document.getElementById('cv-docx-dl').href = fileUrl;
  else             imgEl.src = fileUrl;

  switchMtab('raw');
  document.getElementById('modal').style.display = 'flex';
}

document.getElementById('re-extract-btn').addEventListener('click', async () => {
  if (!currentCvId) return;
  const btn = document.getElementById('re-extract-btn');
  const method = document.getElementById('re-extract-method').value;
  const ollamaUrl = document.getElementById('re-ollama-url').value;
  if (method === 'minicpm-v' && !ollamaUrl) { alert('Enter ngrok URL for MiniCPM-V'); return; }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Extracting...';
  try {
    const res = await fetch(`${API}/cvs/${currentCvId}/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, ollama_url: ollamaUrl || null }),
    });
    if (res.ok) {
      await openDetail(currentCvId);
    } else {
      const d = await safeJson(res);
      alert(`Error: ${d.detail || 'Failed'}`);
    }
  } catch (err) {
    alert(`Request failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Re-extract';
  }
});

document.getElementById('re-classify-btn').addEventListener('click', async () => {
  if (!currentCvId) return;
  const btn = document.getElementById('re-classify-btn');
  const model = document.getElementById('re-classify-model').value;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Classifying...';
  try {
    const res = await fetch(`${API}/cvs/${currentCvId}/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    if (res.ok) {
      await openDetail(currentCvId);
    } else {
      const d = await safeJson(res);
      alert(`Error: ${d.detail || 'Failed'}`);
    }
  } catch (err) {
    alert(`Request failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Re-classify';
  }
});

document.getElementById('modal-project-select').addEventListener('change', function () {
  document.getElementById('modal-new-project-name').style.display = this.value === '__new__' ? 'inline-block' : 'none';
});

document.getElementById('assign-project-btn').addEventListener('click', async () => {
  if (!currentCvId) return;
  const select = document.getElementById('modal-project-select');
  const btn = document.getElementById('assign-project-btn');
  const body = select.value === '__new__'
    ? { new_project_name: document.getElementById('modal-new-project-name').value.trim() }
    : { project_id: select.value ? Number(select.value) : null };
  if (select.value === '__new__' && !body.new_project_name) { alert('Enter a name for the new project'); return; }

  btn.disabled = true;
  try {
    const res = await fetch(`${API}/cvs/${currentCvId}/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || 'Failed to move CV');
    if (body.new_project_name) await loadProjects();
    await openDetail(currentCvId);
    if (document.getElementById('tab-library').style.display !== 'none') loadLibrary();
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('delete-btn').addEventListener('click', async () => {
  if (!currentCvId) return;
  if (!confirm(`Delete CV #${currentCvId}?`)) return;
  await fetch(`${API}/cvs/${currentCvId}`, { method: 'DELETE' });
  document.getElementById('modal').style.display = 'none';
  currentCvId = null;
  loadLibrary();
});

// ── LLM ranker options (model + tunnel URL) ──────────────────────────────────
const rankMethodSelect = document.getElementById('rank-method');
const llmOptionsGroup  = document.getElementById('llm-options-group');
const llmModelSelect   = document.getElementById('llm-model-select');
const llmModelCustom   = document.getElementById('llm-model-custom');

rankMethodSelect.addEventListener('change', () => {
  llmOptionsGroup.style.display = rankMethodSelect.value.startsWith('llm') ? 'flex' : 'none';
});

llmModelSelect.addEventListener('change', () => {
  llmModelCustom.style.display = llmModelSelect.value === '__custom__' ? 'inline-block' : 'none';
});

function resolveLlmModel() {
  return llmModelSelect.value === '__custom__' ? llmModelCustom.value.trim() : llmModelSelect.value;
}

// ── JD file upload → extract text → populate textarea ────────────────────────
document.getElementById('jd-file').addEventListener('change', async function () {
  const file = this.files[0];
  if (!file) return;
  const statusEl  = document.getElementById('jd-file-status');
  const uploadBtn = document.querySelector('.jd-upload-btn');
  const rankBtn   = document.getElementById('rank-btn');

  setStatus(statusEl, `Extracting text from "${file.name}"…`, 'info');
  uploadBtn.style.opacity      = '0.6';
  uploadBtn.style.pointerEvents = 'none';
  rankBtn.disabled  = true;
  rankBtn.innerHTML = '<span class="spinner"></span>Extracting JD…';

  const fd = new FormData();
  fd.append('file', file);
  try {
    const res  = await fetch(`${API}/cvs/jd-extract`, { method: 'POST', body: fd });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || 'Extraction failed');
    document.getElementById('jd-text').value = data.text;
    setStatus(statusEl, `Text extracted from "${file.name}" - review and submit below.`, 'success');
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    uploadBtn.style.opacity      = '';
    uploadBtn.style.pointerEvents = '';
    rankBtn.disabled  = false;
    rankBtn.textContent = 'Find Matches';
    this.value = '';
  }
});

// ── JD vs CV NER Compare Modal ────────────────────────────────────────────────
let lastJdNer = {};
let lastRankMethod = 'tfidf';
let lastRankResults = [];

// method -> which of the CV's precomputed NER fields lines up with lastJdNer
const RANK_METHOD_CV_NER_FIELD = {
  model1: 'ner_model1',
  model1_hybrid: 'ner_model1',
  model2: 'ner_model2',
  model2_hybrid: 'ner_model2',
  tfidf: 'ner_merged',
};

function normSet(vals) {
  return new Set((Array.isArray(vals) ? vals : [vals]).map(v => String(v).trim().toLowerCase()).filter(Boolean));
}

function compareChips(vals, otherSet) {
  return (Array.isArray(vals) ? vals : [vals]).map(v => {
    const matched = otherSet.has(String(v).trim().toLowerCase());
    return `<span class="ner-chip ${matched ? 'ner-chip-green' : 'ner-chip-red'}">${v}</span>`;
  }).join('');
}

function renderCompareNer(jdNer, cvNer) {
  const labels = Array.from(new Set([...Object.keys(jdNer || {}), ...Object.keys(cvNer || {})])).sort();
  if (!labels.length) return '<p style="color:#6b7280;padding:.5rem">No NER data available to compare.</p>';

  const rows = labels.map(label => {
    const jdVals = (jdNer || {})[label] || [];
    const cvVals = (cvNer || {})[label] || [];
    const jdSet = normSet(jdVals);
    const cvSet = normSet(cvVals);
    const jdChips = jdVals.length ? compareChips(jdVals, cvSet) : '<span style="color:#9ca3af">—</span>';
    const cvChips = cvVals.length ? compareChips(cvVals, jdSet) : '<span style="color:#9ca3af">—</span>';
    return `<tr><td><strong>${label}</strong></td><td><div class="ner-vals">${jdChips}</div></td><td><div class="ner-vals">${cvChips}</div></td></tr>`;
  }).join('');

  return `<table class="ner-table">
    <thead><tr><th>Label</th><th>Job Description</th><th>CV</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function openCompare(cvId) {
  const cv = lastRankResults.find(r => r.id === cvId);
  if (!cv) return;
  const nerField = RANK_METHOD_CV_NER_FIELD[lastRankMethod] || 'ner_merged';
  const cvNer = cv[nerField] || {};

  document.getElementById('compare-modal-title').textContent = `JD vs. ${cv.filename} — NER Match`;
  document.getElementById('compare-body').innerHTML = renderCompareNer(lastJdNer, cvNer);
  document.getElementById('compare-modal').style.display = 'flex';
}

document.getElementById('compare-modal-close').addEventListener('click', () => {
  document.getElementById('compare-modal').style.display = 'none';
});

// ── JD Match ──────────────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function renderRankResultsTable(resultsEl, results, { isHybrid, isLlm, rubric, llmModel, method }) {
  if (!results.length) {
    resultsEl.innerHTML = '<p style="color:#6b7280;padding:1rem 0">No CVs with extracted text found. Upload and extract CVs first.</p>';
    return;
  }

  let rubricHtml = '';
  if (isLlm && rubric) {
    const summaryText = method === 'llm_no_rubric'
      ? `View job description sent for evaluation (${escapeHtml(llmModel)})`
      : `View generated scoring rubric (${escapeHtml(llmModel)})`;
    rubricHtml = `<details class="rubric-box">
        <summary>${summaryText}</summary>
        <pre>${escapeHtml(rubric)}</pre>
      </details>`;
  }

  const rows = results.map((cv, i) => {
    const score = typeof cv.match_score === 'number' ? cv.match_score : 0;
    const scoreColor = score >= 15 ? '#15803d' : score >= 8 ? '#b45309' : '#6b7280';
    const skillChips = (cv.skills || []).slice(0, 8)
      .map(s => `<span class="ner-chip">${s}</span>`).join('');
    const breakdownCols = isHybrid
      ? `<td style="color:#6b7280">${(cv.embedding_score ?? 0).toFixed(1)}%</td><td style="color:#6b7280">${(cv.keyword_score ?? 0).toFixed(1)}%</td>`
      : '';
    const extraCol = isLlm
      ? `<td>${escapeHtml(cv.llm_justification) || '-'}</td>`
      : `<td><button class="btn-secondary" style="padding:.2rem .5rem;font-size:.8rem" onclick="openCompare(${cv.id})">Compare NER</button></td>`;
    return `<tr>
      <td style="font-weight:600;width:2.5rem">${i + 1}</td>
      <td><button class="btn-secondary" style="padding:.2rem .5rem;font-size:.8rem" onclick="openDetail(${cv.id})">${cv.filename}</button></td>
      <td>${cv.name || '-'}</td>
      <td>${cv.email || '-'}</td>
      <td><strong style="color:${scoreColor}">${score.toFixed(1)}%</strong></td>
      ${breakdownCols}
      <td><div class="ner-vals">${skillChips || '<span style="color:#9ca3af">none extracted</span>'}</div></td>
      ${extraCol}
    </tr>`;
  }).join('');

  const breakdownHeaders = isHybrid ? '<th>Embedding</th><th>NER Keyword</th>' : '';
  const extraHeader = isLlm ? '<th>LLM Justification</th>' : '<th>Compare</th>';
  resultsEl.innerHTML = `
    ${rubricHtml}
    <table class="ner-table">
      <thead><tr><th>#</th><th>File</th><th>Name</th><th>Email</th><th>Score</th>${breakdownHeaders}<th>Top Skills</th>${extraHeader}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// Polls /cvs/rank/llm/{job_id} until done/error, updating the progress bar and
// live results table (in completion order) on every tick so the user watches
// CVs get scored one by one instead of staring at a spinner for minutes.
async function pollLlmRankJob(jobId, resultsEl, llmModel, method) {
  const progressEl  = document.getElementById('llm-progress');
  const progressFill = document.getElementById('llm-progress-fill');
  const progressText = document.getElementById('llm-progress-text');
  showEl(progressEl, 'block');

  try {
    while (true) {
      const res = await fetch(`${API}/cvs/rank/llm/${jobId}`);
      const job = await safeJson(res);
      if (!res.ok) throw new Error(job.detail || 'Lost track of the ranking job');

      const pct = job.total ? Math.round((job.completed / job.total) * 100) : 0;
      progressFill.style.width = `${pct}%`;
      if (job.phase === 'starting') {
        progressText.textContent = 'Starting LLM ranking job...';
      } else if (job.phase === 'rubric') {
        progressText.textContent = 'Building scoring rubric from the job description...';
      } else if (job.phase === 'filtering') {
        progressText.textContent = `Soft filtering CVs: scanned ${job.completed}/${job.total} — ${job.current_filename || ''}`;
      } else if (job.phase === 'batch_scoring') {
        progressText.textContent = `Scoring candidates in batches of 3: completed ${job.completed}/${job.total} — ${job.current_filename || ''}`;
      } else if (job.phase === 're_ranking') {
        progressText.textContent = `Re-ranking top candidates relative to each other...`;
      } else if (job.phase === 'scoring') {
        progressText.textContent = `Scoring CV ${job.completed}/${job.total} — ${job.current_filename || ''}`;
      }

      lastJdNer       = {};
      lastRankMethod  = method;
      lastRankResults = job.results || [];
      renderRankResultsTable(resultsEl, job.results || [], { isHybrid: false, isLlm: true, rubric: job.rubric, llmModel, method });

      if (job.status === 'done') {
        progressText.textContent = `Done — scored ${job.total}/${job.total} CVs.`;
        return;
      }
      if (job.status === 'error') {
        throw new Error(job.error || 'LLM ranking failed');
      }
      await sleep(1200);
    }
  } finally {
    hideEl(progressEl);
  }
}

document.getElementById('rank-form').addEventListener('submit', async e => {
  e.preventDefault();
  const statusEl  = document.getElementById('rank-status');
  const resultsEl = document.getElementById('rank-results');
  const btn       = document.getElementById('rank-btn');
  const jdText    = document.getElementById('jd-text').value.trim();
  const topN      = parseInt(document.getElementById('rank-top-n').value, 10) || 10;
  const method    = document.getElementById('rank-method').value;
  if (!jdText) return;

  const isLlm = method.startsWith('llm');
  let llmModel, llmOllamaUrl;
  if (isLlm) {
    llmModel     = resolveLlmModel();
    llmOllamaUrl = document.getElementById('llm-ollama-url').value.trim();
    if (!llmModel)     { setStatus(statusEl, 'Enter a custom LLM model tag', 'error'); return; }
    if (!llmOllamaUrl) { setStatus(statusEl, 'Enter the Ollama/ngrok/cloudflare tunnel URL', 'error'); return; }
  }

  const methodLabel = {
    tfidf: 'TF-IDF',
    model1: 'model-best embedding',
    model2: 'model-best 2 embedding',
    model1_hybrid: 'model-best hybrid (embedding + NER)',
    model2_hybrid: 'model-best 2 hybrid (embedding + NER)',
    llm: `LLM Judge (rubric-based) (${llmModel || ''})`,
    llm_no_rubric: `LLM Judge (no rubric, direct JD) (${llmModel || ''})`,
    llm_multilayer: `LLM Judge (multilayer: filter -> score -> re-rank) (${llmModel || ''})`,
  }[method];
  const isHybrid = method.endsWith('_hybrid');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Ranking...';
  setStatus(statusEl, isLlm
    ? `Starting ${methodLabel} — this calls the LLM once per CV, so it can take a while. Watch progress below.`
    : `Calculating ${methodLabel} similarity against all CVs...`, 'info');
  resultsEl.innerHTML = '';

  try {
    if (isLlm) {
      const startRes = await fetch(`${API}/cvs/rank/llm/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jd_text: jdText, top_n: topN, project_id: currentProjectId,
          llm_model: llmModel, ollama_url: llmOllamaUrl, method: method,
        }),
      });
      const startData = await safeJson(startRes);
      if (!startRes.ok) throw new Error(startData.detail || `Server error ${startRes.status}`);

      hideEl(statusEl);
      await pollLlmRankJob(startData.job_id, resultsEl, llmModel, method);
      return;
    }

    const res = await fetch(`${API}/cvs/rank`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jd_text: jdText, top_n: topN, method, project_id: currentProjectId }),
    });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`);

    hideEl(statusEl);

    const results = data.results || [];
    lastJdNer       = data.jd_ner || {};
    lastRankMethod  = data.method || method;
    lastRankResults = results;

    renderRankResultsTable(resultsEl, results, { isHybrid, isLlm: false, method });
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Find Matches';
  }
});
