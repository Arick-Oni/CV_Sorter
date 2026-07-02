const API = '';   // same origin

// ── Utilities ─────────────────────────────────────────────────────────────────
function setStatus(el, msg, type = 'info') {
  el.textContent = msg;
  el.className = `status ${type}`;
  el.style.display = '';
}

function hideEl(el) { el.style.display = 'none'; }
function showEl(el, display = 'block') { el.style.display = display; }

function fmtDate(iso) {
  return new Date(iso).toLocaleString();
}

function statusBadge(s) {
  const map = { uploaded: 'gray', extracted: 'yellow', classified: 'green' };
  return `<span class="badge badge-${map[s] || 'gray'}">${s}</span>`;
}

function methodBadge(m) {
  if (!m) return '--';
  return m === 'easyocr'
    ? '<span class="badge badge-blue">EasyOCR</span>'
    : '<span class="badge badge-yellow">MiniCPM-V</span>';
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

  const fd = new FormData();
  fd.append('file', file);
  fd.append('extraction_method', extractionMethod.value);
  if (extractionMethod.value === 'minicpm-v') {
    fd.append('ollama_url', document.getElementById('ollama-url').value);
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
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Process';
  }
});

// ── Library ───────────────────────────────────────────────────────────────────
async function loadLibrary() {
  const tbody = document.getElementById('cv-tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b7280;padding:1.5rem">Loading...</td></tr>';
  try {
    const res  = await fetch(`${API}/cvs/`);
    const cvs  = await res.json();
    if (!cvs.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b7280;padding:1.5rem">No CVs uploaded yet.</td></tr>';
      return;
    }
    tbody.innerHTML = cvs.map(cv => `
      <tr>
        <td>${cv.id}</td>
        <td>${cv.filename}</td>
        <td>${fmtDate(cv.uploaded_at)}</td>
        <td>${methodBadge(cv.extraction_method)}</td>
        <td>${statusBadge(cv.status)}</td>
        <td class="row-actions">
          <button class="btn-secondary" onclick="openDetail(${cv.id})">View</button>
          <button class="btn-danger" onclick="deleteCv(${cv.id})">Delete</button>
        </td>
      </tr>`).join('');
  } catch {
    tbody.innerHTML = '<tr><td colspan="6" style="color:#b91c1c;padding:1rem">Failed to load CVs.</td></tr>';
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
  renderNer(document.getElementById('ner-m1'),     cv.ner_model1);
  renderNer(document.getElementById('ner-m2'),     cv.ner_model2);
  renderNer(document.getElementById('ner-merged'), cv.ner_merged);
  renderNer(document.getElementById('ner-skills'), cv.ner_skills);

  document.getElementById('cv-img').src = `${API}/cvs/${id}/file`;

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

document.getElementById('delete-btn').addEventListener('click', async () => {
  if (!currentCvId) return;
  if (!confirm(`Delete CV #${currentCvId}?`)) return;
  await fetch(`${API}/cvs/${currentCvId}`, { method: 'DELETE' });
  document.getElementById('modal').style.display = 'none';
  currentCvId = null;
  loadLibrary();
});

// ── JD file upload → extract text → populate textarea ────────────────────────
document.getElementById('jd-file').addEventListener('change', async function () {
  const file = this.files[0];
  if (!file) return;
  const statusEl = document.getElementById('jd-file-status');
  const btn = document.querySelector('.jd-upload-btn');
  setStatus(statusEl, `Extracting text from "${file.name}"…`, 'info');
  btn.style.opacity = '0.6';
  btn.style.pointerEvents = 'none';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch(`${API}/cvs/jd-extract`, { method: 'POST', body: fd });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || 'Extraction failed');
    document.getElementById('jd-text').value = data.text;
    setStatus(statusEl, `Text extracted from "${file.name}" — review and submit below.`, 'success');
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.style.opacity = '';
    btn.style.pointerEvents = '';
    this.value = '';   // allow re-selecting the same file
  }
});

// ── JD Match ──────────────────────────────────────────────────────────────────
document.getElementById('rank-form').addEventListener('submit', async e => {
  e.preventDefault();
  const statusEl  = document.getElementById('rank-status');
  const resultsEl = document.getElementById('rank-results');
  const btn       = document.getElementById('rank-btn');
  const jdText    = document.getElementById('jd-text').value.trim();
  const topN      = parseInt(document.getElementById('rank-top-n').value, 10) || 10;
  if (!jdText) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Ranking...';
  setStatus(statusEl, 'Calculating TF-IDF similarity against all CVs...', 'info');
  resultsEl.innerHTML = '';

  try {
    const res = await fetch(`${API}/cvs/rank`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jd_text: jdText, top_n: topN }),
    });
    const data = await safeJson(res);
    if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`);

    hideEl(statusEl);

    if (!Array.isArray(data) || !data.length) {
      resultsEl.innerHTML = '<p style="color:#6b7280;padding:1rem 0">No CVs with extracted text found. Upload and extract CVs first.</p>';
      return;
    }

    const rows = data.map((cv, i) => {
      const score = typeof cv.match_score === 'number' ? cv.match_score : 0;
      const scoreColor = score >= 15 ? '#15803d' : score >= 8 ? '#b45309' : '#6b7280';
      const skillChips = (cv.skills || []).slice(0, 8)
        .map(s => `<span class="ner-chip">${s}</span>`).join('');
      return `<tr>
        <td style="font-weight:600;width:2.5rem">${i + 1}</td>
        <td><button class="btn-secondary" style="padding:.2rem .5rem;font-size:.8rem" onclick="openDetail(${cv.id})">${cv.filename}</button></td>
        <td>${cv.name || '—'}</td>
        <td>${cv.email || '—'}</td>
        <td><strong style="color:${scoreColor}">${score.toFixed(1)}%</strong></td>
        <td><div class="ner-vals">${skillChips || '<span style="color:#9ca3af">none extracted</span>'}</div></td>
      </tr>`;
    }).join('');

    resultsEl.innerHTML = `
      <table class="ner-table">
        <thead><tr><th>#</th><th>File</th><th>Name</th><th>Email</th><th>Score</th><th>Top Skills</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Find Matches';
  }
});
