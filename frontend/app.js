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

function seniorityBadge(level) {
  if (!level) return '--';
  const map = {
    'Junior': 'badge-gray',
    'Mid-level': 'badge-blue',
    'Senior': 'badge-green',
    'Lead / Principal': 'badge-yellow',
    'Executive': 'badge-red'
  };
  const cls = map[level] || 'badge-gray';
  return `<span class="badge ${cls}">${level}</span>`;
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

// ── Match Ranking Pagination & State ──────────────────────────────────────────
let currentRankResults = [];
let currentRankPage = 1;
const ROWS_PER_PAGE = 10;
let currentRankResultsOptions = {};

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
// Initial history load
loadRankHistory();

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
  if (targetTab === 'rank') loadRankHistory();
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

// ── Compare Modal Tabs & Chart.js Integration ───────────────────────────────
let skillsChart = null;
let techChart = null;

function switchCtab(targetCtab) {
  document.querySelectorAll('.ctab').forEach(b => {
    b.classList.toggle('active', b.dataset.ctab === targetCtab);
  });
  document.querySelectorAll('.ctab-panel').forEach(p => {
    p.style.display = p.id === `ctab-${targetCtab}` ? 'block' : 'none';
  });
}

// Bind ctab event listeners
function bindCtabs() {
  document.querySelectorAll('.ctab').forEach(btn => {
    btn.addEventListener('click', () => switchCtab(btn.dataset.ctab));
  });
}
bindCtabs();

function renderRadarChart(canvasId, placeholderId, dataList, label) {
  const canvas = document.getElementById(canvasId);
  const placeholder = document.getElementById(placeholderId);
  
  if (!canvas || !placeholder) return;
  
  if (!dataList || dataList.length === 0) {
    canvas.style.display = 'none';
    placeholder.style.display = 'block';
    return;
  }
  
  canvas.style.display = 'block';
  placeholder.style.display = 'none';
  
  const labels = dataList.map(item => item.jd_item);
  const cvScores = dataList.map(item => item.similarity);
  const jdScores = dataList.map(() => 100);
  
  // Destroy existing chart instance to avoid overlaps
  if (canvasId === 'skillsRadarChart' && skillsChart) {
    skillsChart.destroy();
    skillsChart = null;
  }
  if (canvasId === 'techRadarChart' && techChart) {
    techChart.destroy();
    techChart = null;
  }
  
  const ctx = canvas.getContext('2d');
  const chartInstance = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'JD Requirement',
          data: jdScores,
          fill: true,
          backgroundColor: 'rgba(79, 70, 229, 0.05)',
          borderColor: 'rgba(79, 70, 229, 0.3)',
          pointBackgroundColor: 'rgba(79, 70, 229, 0.8)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgba(79, 70, 229, 1)'
        },
        {
          label: 'Candidate Match',
          data: cvScores,
          fill: true,
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          borderColor: 'rgba(16, 185, 129, 0.85)',
          pointBackgroundColor: 'rgba(16, 185, 129, 1)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgba(16, 185, 129, 1)'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: {
            display: true,
            color: '#e2e8f0'
          },
          grid: {
            color: '#f1f5f9'
          },
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: {
            stepSize: 20,
            backdropColor: 'transparent',
            color: '#94a3b8',
            font: {
              size: 9
            }
          },
          pointLabels: {
            color: '#475569',
            font: {
              size: 10,
              weight: '600'
            }
          }
        }
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 10,
            font: {
              size: 10,
              weight: '500'
            },
            color: '#475569'
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const datasetLabel = context.dataset.label || '';
              const value = context.raw;
              const index = context.dataIndex;
              if (context.datasetIndex === 1) {
                const matchItem = dataList[index].cv_item || 'N/A';
                return `${datasetLabel}: ${value}% (Best match: ${matchItem})`;
              }
              return `${datasetLabel}: ${value}%`;
            }
          }
        }
      }
    }
  });
  
  if (canvasId === 'skillsRadarChart') {
    skillsChart = chartInstance;
  } else {
    techChart = chartInstance;
  }
}

// ── Ranking Bar Chart (Score Distribution) ──────────────────────────────────
let rankingBarChartInstance = null;
let rankingChartCollapsed = false;

function setRankingChartCollapsed(collapsed) {
  rankingChartCollapsed = collapsed;
  const body = document.getElementById('ranking-chart-body');
  const btn = document.getElementById('toggle-ranking-chart-btn');
  if (!body || !btn) return;
  if (rankingChartCollapsed) {
    body.style.display = 'none';
    btn.textContent = 'Expand Graph';
  } else {
    body.style.display = 'block';
    btn.textContent = 'Collapse Graph';
  }
}

// Bind ranking chart toggle button listener immediately
const toggleRankingChartBtn = document.getElementById('toggle-ranking-chart-btn');
if (toggleRankingChartBtn) {
  toggleRankingChartBtn.addEventListener('click', () => {
    setRankingChartCollapsed(!rankingChartCollapsed);
  });
}

function renderRankingBarChart(results) {
  const wrapper = document.getElementById('ranking-chart-wrapper');
  const canvas = document.getElementById('rankingBarChart');
  if (!wrapper || !canvas) return;
  
  if (!results || results.length === 0) {
    wrapper.style.display = 'none';
    return;
  }
  
  wrapper.style.display = 'block';
  setRankingChartCollapsed(false);
  
  const sorted = [...results].sort((a, b) => b.match_score - a.match_score);
  const labels = sorted.map(r => r.filename);
  const data = sorted.map(r => r.match_score);
  const seniorityLevels = sorted.map(r => r.seniority_level || 'N/A');
  
  if (rankingBarChartInstance) {
    rankingBarChartInstance.destroy();
    rankingBarChartInstance = null;
  }
  
  const ctx = canvas.getContext('2d');
  rankingBarChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Match Score (%)',
        data: data,
        backgroundColor: sorted.map((_, idx) => {
          if (idx === 0) return 'rgba(79, 70, 229, 0.85)';
          if (idx < 3) return 'rgba(79, 70, 229, 0.65)';
          return 'rgba(79, 70, 229, 0.4)';
        }),
        borderColor: 'rgba(79, 70, 229, 1)',
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: '#f1f5f9' },
          ticks: {
            color: '#64748b',
            font: { size: 10 }
          }
        },
        x: {
          grid: { display: false },
          ticks: {
            color: '#64748b',
            font: { size: 9 },
            maxRotation: 45,
            minRotation: 0,
            callback: function(value, index) {
              const label = labels[index] || '';
              return label.length > 15 ? label.slice(0, 12) + '...' : label;
            }
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: function(context) {
              const index = context[0].dataIndex;
              return labels[index];
            },
            label: function(context) {
              const value = context.raw;
              const index = context.dataIndex;
              const seniority = seniorityLevels[index];
              return [
                `Score: ${value.toFixed(1)}%`,
                `Seniority: ${seniority}`
              ];
            }
          }
        }
      }
    }
  });
}

async function openCompare(cvId) {
  const cv = lastRankResults.find(r => r.id === cvId);
  if (!cv) return;
  const nerField = RANK_METHOD_CV_NER_FIELD[lastRankMethod] || 'ner_merged';
  const cvNer = cv[nerField] || {};

  document.getElementById('compare-modal-title').textContent = `JD vs. ${cv.filename} — NER Match`;
  document.getElementById('compare-body').innerHTML = renderCompareNer(lastJdNer, cvNer);
  
  // Default to table tab
  switchCtab('table');
  document.getElementById('compare-modal').style.display = 'flex';

  // Destroy previous charts before loading new ones
  if (skillsChart) { skillsChart.destroy(); skillsChart = null; }
  if (techChart) { techChart.destroy(); techChart = null; }

  // Fetch semantic similarity scores for radar graphs
  const jdText = document.getElementById('jd-text').value.trim();
  try {
    const res = await fetch(`${API}/cvs/${cvId}/compare-semantic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jd_text: jdText, method: lastRankMethod })
    });
    if (res.ok) {
      const data = await res.json();
      renderRadarChart('skillsRadarChart', 'skillsChartPlaceholder', data.skills, 'Skills');
      renderRadarChart('techRadarChart', 'techChartPlaceholder', data.technologies, 'Technologies');
    }
  } catch (err) {
    console.error('Error fetching semantic comparison:', err);
  }
}

document.getElementById('compare-modal-close').addEventListener('click', () => {
  document.getElementById('compare-modal').style.display = 'none';
  if (skillsChart) { skillsChart.destroy(); skillsChart = null; }
  if (techChart) { techChart.destroy(); techChart = null; }
});

// ── JD Match ──────────────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function renderRankResultsTable(resultsEl, results, options) {
  currentRankResults = results || [];
  currentRankPage = 1;
  currentRankResultsOptions = options || {};
  renderCurrentRankPage();
}

function renderCurrentRankPage() {
  const resultsEl = document.getElementById('rank-results');
  const pagControlsEl = document.getElementById('pagination-controls');
  
  if (!currentRankResults.length) {
    resultsEl.innerHTML = '<p style="color:#6b7280;padding:1rem 0">No CVs with extracted text found. Upload and extract CVs first.</p>';
    if (pagControlsEl) pagControlsEl.style.display = 'none';
    return;
  }
  
  const maxPage = Math.ceil(currentRankResults.length / ROWS_PER_PAGE) || 1;
  if (currentRankPage > maxPage) currentRankPage = maxPage;
  if (currentRankPage < 1) currentRankPage = 1;
  
  const startIdx = (currentRankPage - 1) * ROWS_PER_PAGE;
  const endIdx = startIdx + ROWS_PER_PAGE;
  const pageResults = currentRankResults.slice(startIdx, endIdx);
  
  const { isHybrid, isLlm, rubric, llmModel, method } = currentRankResultsOptions;
  
  let rubricHtml = '';
  if (isLlm && rubric && currentRankPage === 1) {
    const summaryText = method === 'llm_no_rubric'
      ? `View job description sent for evaluation (${escapeHtml(llmModel)})`
      : `View generated scoring rubric (${escapeHtml(llmModel)})`;
    rubricHtml = `<details class="rubric-box">
        <summary>${summaryText}</summary>
        <pre>${escapeHtml(rubric)}</pre>
      </details>`;
  }
  
  const rows = pageResults.map((cv, i) => {
    const globalIdx = startIdx + i + 1;
    const score = typeof cv.match_score === 'number' ? cv.match_score : 0;
    const scoreClass = score >= 75 ? 'score-high' : score >= 40 ? 'score-medium' : 'score-low';
    const skillChips = (cv.skills || []).slice(0, 4)
      .map(s => `<span class="ner-chip">${s}</span>`).join('');
    const breakdownCols = isHybrid
      ? `<td style="color:#6b7280">${(cv.embedding_score ?? 0).toFixed(1)}%</td><td style="color:#6b7280">${(cv.keyword_score ?? 0).toFixed(1)}%</td>`
      : '';
    const extraCol = isLlm
      ? `<td>
          ${cv.llm_justification ? `
            <details class="justification-details">
              <summary>View details</summary>
              <div class="justification-content">${escapeHtml(cv.llm_justification)}</div>
            </details>
          ` : '-'}
         </td>`
      : `<td><button class="btn-secondary" style="padding:.2rem .5rem;font-size:.8rem" onclick="openCompare(${cv.id})">Compare NER</button></td>`;
    
    return `<tr>
      <td style="font-weight:600;width:2.5rem">${globalIdx}</td>
      <td><a href="#" class="cv-link" onclick="event.preventDefault(); openDetail(${cv.id})">${cv.filename}</a></td>
      <td>${cv.name || '-'}</td>
      <td>${cv.email || '-'}</td>
      <td><span class="score-badge ${scoreClass}">${score.toFixed(1)}%</span></td>
      ${breakdownCols}
      <td><div class="ner-vals">${skillChips || '<span style="color:#9ca3af">none</span>'}</div></td>
      ${extraCol}
    </tr>`;
  }).join('');
  
  const breakdownHeaders = isHybrid ? '<th>Embedding</th><th>NER Keyword</th>' : '';
  const extraHeader = isLlm ? '<th>LLM Justification</th>' : '<th>Compare</th>';
  
  resultsEl.innerHTML = `
    ${rubricHtml}
    <div class="table-responsive">
      <table class="ner-table">
        <thead><tr><th>#</th><th>File</th><th>Name</th><th>Email</th><th>Score</th>${breakdownHeaders}<th>Top Skills</th>${extraHeader}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
    
  if (pagControlsEl) {
    pagControlsEl.style.display = currentRankResults.length > ROWS_PER_PAGE ? 'flex' : 'none';
    document.getElementById('page-indicator').textContent = `Page ${currentRankPage} of ${maxPage}`;
    document.getElementById('btn-prev-page').disabled = currentRankPage === 1;
    document.getElementById('btn-next-page').disabled = currentRankPage === maxPage;
  }
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
        loadRankHistory();
        renderRankingBarChart(lastRankResults);
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
  
  const banner = document.getElementById('loaded-history-banner');
  if (banner) banner.style.display = 'none';
  document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));

  const statusEl  = document.getElementById('rank-status');
  const resultsEl = document.getElementById('rank-results');
  const btn       = document.getElementById('rank-btn');
  const jdText    = document.getElementById('jd-text').value.trim();
  const method    = document.getElementById('rank-method').value;
  if (!jdText) return;

  setJdFormCollapsed(true);

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
          jd_text: jdText, top_n: 1000, project_id: currentProjectId,
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
      body: JSON.stringify({ jd_text: jdText, top_n: 1000, method, project_id: currentProjectId }),
    });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`);

    hideEl(statusEl);

    const results = data.results || [];
    lastJdNer       = data.jd_ner || {};
    lastRankMethod  = data.method || method;
    lastRankResults = results;

    renderRankResultsTable(resultsEl, results, { isHybrid, isLlm: false, method });
    renderRankingBarChart(lastRankResults);
    loadRankHistory();
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Find Matches';
  }
});

// ── Match History & Pagination Helpers ─────────────────────────────────────────
document.getElementById('btn-prev-page').addEventListener('click', () => {
  if (currentRankPage > 1) {
    currentRankPage--;
    renderCurrentRankPage();
  }
});

document.getElementById('btn-next-page').addEventListener('click', () => {
  const maxPage = Math.ceil(currentRankResults.length / ROWS_PER_PAGE) || 1;
  if (currentRankPage < maxPage) {
    currentRankPage++;
    renderCurrentRankPage();
  }
});

async function loadRankHistory() {
  const historyListEl = document.getElementById('history-list');
  if (!historyListEl) return;
  historyListEl.innerHTML = '<p style="color:#6b7280; font-size:.85rem; text-align:center; padding:1rem 0">Loading matches...</p>';
  
  try {
    const qs = currentProjectId ? `?project_id=${currentProjectId}` : '';
    const res = await fetch(`${API}/cvs/rank/history${qs}`);
    const historyItems = await res.json();
    
    if (!historyItems.length) {
      historyListEl.innerHTML = '<p style="color:#6b7280; font-size:.85rem; text-align:center; padding:1rem 0">No recent matches.</p>';
      return;
    }
    
    historyListEl.innerHTML = historyItems.map(item => {
      const dt = new Date(item.created_at).toLocaleString();
      const methodLabel = {
        tfidf: 'TF-IDF',
        model1: 'Embed M1',
        model2: 'Embed M2',
        model1_hybrid: 'Hybrid M1',
        model2_hybrid: 'Hybrid M2',
        llm: 'LLM Rubric',
        llm_no_rubric: 'LLM Direct',
        llm_multilayer: 'LLM Multi'
      }[item.method] || item.method;
      
      const badgeClass = item.method.startsWith('llm') ? 'badge-yellow' : 'badge-blue';
      const projBadge = item.project_name
        ? `<span class="badge badge-gray" style="padding:.1rem .4rem; font-size:.65rem; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="${escapeHtml(item.project_name)}">${escapeHtml(item.project_name)}</span>`
        : `<span class="badge badge-gray" style="padding:.1rem .4rem; font-size:.65rem; color:#6b7280; font-style:italic">Global</span>`;
      
      return `
        <div class="history-item" data-history-id="${item.id}" onclick="loadHistoryDetail(${item.id})">
          <button class="history-delete-btn" onclick="event.stopPropagation(); deleteHistoryItem(${item.id})">&times;</button>
          <div class="history-item-header">
            <span class="badge ${badgeClass}" style="padding:.1rem .4rem; font-size:.65rem">${methodLabel}</span>
            <span class="history-item-meta">${dt}</span>
          </div>
          <div class="history-item-summary">${escapeHtml(item.jd_summary)}</div>
          <div class="history-item-footer" style="display:flex; justify-content:space-between; align-items:center; margin-top:.4rem">
            ${projBadge}
            ${item.llm_model ? `<span class="history-item-meta" style="font-size:.65rem; color:#64748b" title="Model: ${escapeHtml(item.llm_model)}">${escapeHtml(item.llm_model)}</span>` : ''}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    historyListEl.innerHTML = '<p style="color:#b91c1c; font-size:.85rem; text-align:center; padding:1rem 0">Error loading history.</p>';
  }
}

async function loadHistoryDetail(id) {
  document.querySelectorAll('.history-item').forEach(el => {
    el.classList.toggle('active', Number(el.dataset.historyId) === id);
  });
  
  const statusEl = document.getElementById('rank-status');
  const resultsEl = document.getElementById('rank-results');
  setStatus(statusEl, 'Loading previous match run...', 'info');
  resultsEl.innerHTML = '';
  
  try {
    const res = await fetch(`${API}/cvs/rank/history/${id}`);
    if (!res.ok) throw new Error('Failed to fetch history details');
    const data = await res.json();
    
    document.getElementById('jd-text').value = data.jd_text;
    document.getElementById('rank-method').value = data.method;
    
    const isLlm = data.method.startsWith('llm');
    const optionsGroup = document.getElementById('llm-options-group');
    if (optionsGroup) {
      optionsGroup.style.display = isLlm ? 'flex' : 'none';
      if (isLlm && data.llm_model) {
        const select = document.getElementById('llm-model-select');
        if ([...select.options].some(o => o.value === data.llm_model)) {
          select.value = data.llm_model;
          document.getElementById('llm-model-custom').style.display = 'none';
        } else {
          select.value = '__custom__';
          const customInput = document.getElementById('llm-model-custom');
          customInput.value = data.llm_model;
          customInput.style.display = 'inline-block';
        }
      }
    }
    
    hideEl(statusEl);
    
    lastJdNer = data.jd_ner || {};
    lastRankMethod = data.method;
    lastRankResults = data.results || [];
    
    const banner = document.getElementById('loaded-history-banner');
    if (banner) {
      document.getElementById('loaded-history-project-name').textContent = data.project_name || 'Global / Unassigned';
      const dt = new Date(data.created_at).toLocaleString();
      const methodLabel = {
        tfidf: 'TF-IDF',
        model1: 'Embed M1',
        model2: 'Embed M2',
        model1_hybrid: 'Hybrid M1',
        model2_hybrid: 'Hybrid M2',
        llm: 'LLM Rubric',
        llm_no_rubric: 'LLM Direct',
        llm_multilayer: 'LLM Multi'
      }[data.method] || data.method;
      document.getElementById('loaded-history-meta').textContent = `(${dt} — ${methodLabel})`;
      banner.style.display = 'flex';
    }
    
    setJdFormCollapsed(true);
    
    renderRankResultsTable(resultsEl, data.results || [], {
      isHybrid: data.method.endsWith('_hybrid'),
      isLlm: isLlm,
      rubric: isLlm ? (data.rubric || data.jd_text) : null,
      llmModel: data.llm_model,
      method: data.method
    });
    renderRankingBarChart(lastRankResults);
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  }
}

async function deleteHistoryItem(id) {
  if (!confirm('Are you sure you want to delete this match run from history?')) return;
  try {
    const res = await fetch(`${API}/cvs/rank/history/${id}`, { method: 'DELETE' });
    if (res.ok) {
      loadRankHistory();
      const activeItem = document.querySelector('.history-item.active');
      if (activeItem && Number(activeItem.dataset.historyId) === id) {
        document.getElementById('rank-results').innerHTML = '';
        document.getElementById('pagination-controls').style.display = 'none';
        const chartWrapper = document.getElementById('ranking-chart-wrapper');
        if (chartWrapper) chartWrapper.style.display = 'none';
        if (rankingBarChartInstance) {
          rankingBarChartInstance.destroy();
          rankingBarChartInstance = null;
        }
      }
    } else {
      alert('Failed to delete history item');
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

function clearHistoryView() {
  const banner = document.getElementById('loaded-history-banner');
  if (banner) banner.style.display = 'none';
  document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
  document.getElementById('jd-text').value = '';
  document.getElementById('rank-method').value = 'tfidf';
  const optionsGroup = document.getElementById('llm-options-group');
  if (optionsGroup) optionsGroup.style.display = 'none';
  
  document.getElementById('rank-results').innerHTML = '';
  const paginationControls = document.getElementById('pagination-controls');
  if (paginationControls) paginationControls.style.display = 'none';
  
  const chartWrapper = document.getElementById('ranking-chart-wrapper');
  if (chartWrapper) chartWrapper.style.display = 'none';
  if (rankingBarChartInstance) {
    rankingBarChartInstance.destroy();
    rankingBarChartInstance = null;
  }
  
  const statusEl = document.getElementById('rank-status');
  if (statusEl) hideEl(statusEl);
  const jdFileStatus = document.getElementById('jd-file-status');
  if (jdFileStatus) hideEl(jdFileStatus);
  const jdFile = document.getElementById('jd-file');
  if (jdFile) jdFile.value = '';
  
  lastJdNer = {};
  lastRankMethod = 'tfidf';
  lastRankResults = [];
  
  setJdFormCollapsed(false);
}

const clearBtn = document.getElementById('clear-history-view-btn');
if (clearBtn) {
  clearBtn.addEventListener('click', clearHistoryView);
}

function setJdFormCollapsed(collapsed) {
  const body = document.getElementById('rank-form-body');
  const btn = document.getElementById('toggle-jd-form-btn');
  if (!body || !btn) return;
  if (collapsed) {
    body.style.display = 'none';
    btn.textContent = 'Expand Input';
  } else {
    body.style.display = 'block';
    btn.textContent = 'Collapse Input';
  }
}

const toggleJdBtn = document.getElementById('toggle-jd-form-btn');
if (toggleJdBtn) {
  toggleJdBtn.addEventListener('click', () => {
    const body = document.getElementById('rank-form-body');
    const isCollapsed = body && body.style.display === 'none';
    setJdFormCollapsed(!isCollapsed);
  });
}
