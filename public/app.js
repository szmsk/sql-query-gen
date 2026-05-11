'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let isGenerating = false;
let history      = [];

const EXAMPLES = [
  'How many patients are enrolled in each trial?',
  'Show all active patients with their country',
  'Which patients had severe adverse events?',
  'What is the average haemoglobin level per trial?',
  'List trials by phase and current status',
  'Count adverse events by severity level',
  'Show patients enrolled in Phase III trial',
  'Which patients have completed their trial?',
  'Show all measurements for patient ID 1',
  'How many patients per country?',
  'List all trials with their target enrollment numbers',
  'Show unresolved adverse events with patient names',
];

// ── Init ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadSchema();
  renderExamples();
});

function toggleKey() {
  const inp = document.getElementById('apiKey');
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

// ── Schema tree ────────────────────────────────────────────────────────────
async function loadSchema() {
  try {
    const res  = await fetch('/api/schema');
    const data = await res.json();
    renderSchema(data.tables);
  } catch {
    document.getElementById('schemaTree').innerHTML =
      '<div style="color:var(--text3);font-size:12px">Could not load schema</div>';
  }
}

function renderSchema(tables) {
  const tree = document.getElementById('schemaTree');
  tree.innerHTML = '';
  for (const [name, info] of Object.entries(tables)) {
    const wrap = document.createElement('div');
    wrap.className = 'schema-table';

    const hdr = document.createElement('div');
    hdr.className = 'schema-table-hdr';
    hdr.innerHTML = `<span>${name}</span><span class="tbl-count">${info.row_count} rows</span>`;
    hdr.onclick = () => cols.classList.toggle('open');

    const cols = document.createElement('div');
    cols.className = 'schema-cols';
    cols.innerHTML = info.columns.map(col =>
      `<div class="schema-col">
        <span class="col-name">${col.name}</span>
        <span class="col-type">${col.type}</span>
      </div>`
    ).join('');

    wrap.appendChild(hdr);
    wrap.appendChild(cols);
    tree.appendChild(wrap);
  }
}

// ── Examples ───────────────────────────────────────────────────────────────
function renderExamples() {
  const list = document.getElementById('exampleList');
  EXAMPLES.forEach(q => {
    const btn = document.createElement('button');
    btn.className = 'example-btn';
    btn.textContent = q;
    btn.onclick = () => {
      document.getElementById('questionInput').value = q;
      autoResize(document.getElementById('questionInput'));
      generate();
    };
    list.appendChild(btn);
  });
}

// ── Generate SQL ───────────────────────────────────────────────────────────
async function generate() {
  if (isGenerating) return;

  const apiKey   = document.getElementById('apiKey').value.trim();
  const question = document.getElementById('questionInput').value.trim();

  if (!apiKey)   return showError('Please enter your Anthropic API key.');
  if (!question) return showError('Please type a question.');

  isGenerating = true;
  hideError();
  setGenLoading(true);

  // Hide previous results
  document.getElementById('sqlBlock').style.display     = 'none';
  document.getElementById('resultsBlock').style.display = 'none';

  try {
    const res  = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, prompt: question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Generation failed');

    // Show SQL editor
    const editor = document.getElementById('sqlEditor');
    editor.value = data.sql;
    autoResizeEl(editor);
    document.getElementById('sqlBlock').style.display = 'block';

    // Auto-run
    await runQuery();

    // Save to history
    pushHistory(question, data.sql);

  } catch (err) {
    showError(err.message);
  }

  setGenLoading(false);
  isGenerating = false;
}

// ── Run query ──────────────────────────────────────────────────────────────
async function runQuery() {
  const query = document.getElementById('sqlEditor').value.trim();
  if (!query) return showError('No SQL query to run.');

  hideError();
  document.getElementById('resultsBlock').style.display = 'none';

  const runBtn = document.getElementById('runBtn');
  runBtn.disabled = true;
  runBtn.textContent = '⏳ Running...';

  try {
    const res  = await fetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Execution failed');

    renderResults(data);

  } catch (err) {
    showError(err.message);
  }

  runBtn.disabled = false;
  runBtn.textContent = '▶ Run Query';
}

// ── Render results table ───────────────────────────────────────────────────
function renderResults(data) {
  const block = document.getElementById('resultsBlock');
  const meta  = document.getElementById('resultsMeta');
  const head  = document.getElementById('tableHead');
  const body  = document.getElementById('tableBody');
  const noRes = document.getElementById('noResults');
  const wrap  = block.querySelector('.table-wrap');

  meta.textContent = `${data.count} row${data.count !== 1 ? 's' : ''} · ${data.elapsed}ms`;
  block.style.display = 'block';

  if (data.count === 0) {
    wrap.style.display = 'none';
    noRes.style.display = 'block';
    return;
  }

  wrap.style.display = 'block';
  noRes.style.display = 'none';

  // Header
  head.innerHTML = '<tr>' + data.columns.map(c =>
    `<th>${escHtml(c)}</th>`
  ).join('') + '</tr>';

  // Rows
  body.innerHTML = data.rows.map(row =>
    '<tr>' + data.columns.map(col => {
      const val = row[col];
      if (val === null || val === undefined) {
        return '<td><span class="null-val">NULL</span></td>';
      }
      return `<td title="${escHtml(String(val))}">${escHtml(String(val))}</td>`;
    }).join('') + '</tr>'
  ).join('');
}

// ── History ────────────────────────────────────────────────────────────────
function pushHistory(question, sql) {
  history.unshift({ question, sql, ts: new Date().toLocaleTimeString() });
  if (history.length > 10) history.pop();
  renderHistory();
}

function renderHistory() {
  const block = document.getElementById('historyBlock');
  const list  = document.getElementById('historyList');
  block.style.display = 'block';
  list.innerHTML = history.map((h, i) =>
    `<div class="history-item" onclick="loadHistory(${i})">
      <div class="history-q">${escHtml(h.question)}</div>
      <div class="history-sql">${escHtml(h.sql)}</div>
    </div>`
  ).join('');
}

function loadHistory(i) {
  const h = history[i];
  document.getElementById('questionInput').value = h.question;
  document.getElementById('sqlEditor').value = h.sql;
  autoResizeEl(document.getElementById('sqlEditor'));
  document.getElementById('sqlBlock').style.display = 'block';
  runQuery();
}

// ── Utilities ──────────────────────────────────────────────────────────────
function copySQL() {
  const sql = document.getElementById('sqlEditor').value;
  navigator.clipboard.writeText(sql).then(() => {
    const btn = document.querySelector('.small-btn:not(.primary)');
    btn.textContent = '✓ Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

function showError(msg) {
  const el = document.getElementById('errorBlock');
  document.getElementById('errorMsg').textContent = msg;
  el.style.display = 'flex';
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  document.getElementById('errorBlock').style.display = 'none';
}

function setGenLoading(val) {
  const btn = document.getElementById('genBtn');
  btn.disabled = val;
  btn.innerHTML = val
    ? '<span class="spinner"></span>Generating...'
    : 'Generate SQL ↗';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 150) + 'px';
}

function autoResizeEl(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    generate();
  }
}
