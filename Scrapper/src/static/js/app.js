// ── Estado global ────────────────────────────
let sessionId = null;
let isRunning = false;
let eventSource = null;
let rowCount = 0;
const stats = { fuentes: 0, empresas: 0, emails: 0, telefonos: 0 };

// ── Iniciar scraping ─────────────────────────
async function startScrape(demo = false) {
  if (isRunning) return;

  const sector = document.getElementById('sectorSelect').value;
  const keywords = document.getElementById('keywords').value;

  setRunning(true);
  clearResults();
  logMessage(`Iniciando agente para sector: ${sector}${demo ? ' [DEMO]' : ''}`, 'info');

  try {
    const res = await fetch('/api/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sector, keywords, demo }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    connectSSE(sessionId);
  } catch (e) {
    logMessage(`Error al iniciar: ${e.message}`, 'error');
    setRunning(false);
  }
}

// ── SSE ──────────────────────────────────────
function connectSSE(sid) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`/api/stream/${sid}`);

  eventSource.onmessage = (e) => {
    const event = JSON.parse(e.data);
    handleEvent(event);
  };

  eventSource.onerror = () => {
    eventSource.close();
    setRunning(false);
  };
}

function handleEvent(event) {
  if (event.type === 'ping') return;

  if (event.message) {
    logMessage(event.message, event.type || 'info');
  }

  if (event.stats) {
    updateStats(event.stats);
  }

  if (event.type === 'company' && event.company) {
    appendRow(event.company);
  }

  if (event.phase) {
    updatePhase(event.phase);
    updateProgress(event.phase);
  }

  if (event.type === 'done') {
    setRunning(false);
    updatePhase('done');
    updateProgress('done');
    enableExport();
    resetStopButton();
    toast('✅ Scraping completado', 'success');
    if (eventSource) eventSource.close();
  }

  if (event.type === 'stopped') {
    setRunning(false);
    updatePhase('done');
    updateProgress('done');
    resetStopButton();
    if (rowCount > 0) enableExport();
    toast('⏹ Agente detenido', 'info');
    if (eventSource) eventSource.close();
  }

  if (event.type === 'error') {
    setRunning(false);
    updatePhase('error');
    resetStopButton();
    toast('❌ ' + event.message, 'error');
    if (eventSource) eventSource.close();
  }
}

// ── UI helpers ───────────────────────────────
function setRunning(v) {
  isRunning = v;
  document.getElementById('btnStart').classList.toggle('running', v);
  document.getElementById('btnStart').disabled = v;
  document.getElementById('btnDemo').disabled = v;
  document.getElementById('btnStop').disabled = !v;
  if (v) {
    document.getElementById('progressBar').classList.add('indeterminate');
  }
}

async function stopScrape() {
  if (!sessionId || !isRunning) return;
  document.getElementById('btnStop').disabled = true;
  document.getElementById('btnStop').textContent = 'Parando…';
  try {
    await fetch(`/api/stop/${sessionId}`, { method: 'POST' });
    logMessage('⏹ Solicitando parada al agente…', 'info');
  } catch(e) {
    logMessage('Error al parar: ' + e.message, 'error');
  }
}

function clearResults() {
  rowCount = 0;
  Object.assign(stats, { fuentes: 0, empresas: 0, emails: 0, telefonos: 0 });
  updateStats(stats);
  document.getElementById('tableBody').innerHTML = '';
  document.getElementById('resultsCount').textContent = '0 empresas encontradas';
  document.getElementById('logBox').innerHTML = '';
  document.getElementById('btnXlsx').disabled = true;
  document.getElementById('btnCsv').disabled = true;
  updatePhase('');
}

function updateStats(s) {
  const map = {
    fuentes: ['valFuentes', 'statFuentes'],
    empresas: ['valEmpresas', 'statEmpresas'],
    emails: ['valEmails', 'statEmails'],
    telefonos: ['valTelefonos', 'statTelefonos'],
  };
  for (const [key, [valId, cardId]] of Object.entries(map)) {
    if (s[key] !== undefined && s[key] !== stats[key]) {
      stats[key] = s[key];
      const el = document.getElementById(valId);
      el.textContent = s[key];
      el.classList.remove('bump');
      void el.offsetWidth;
      el.classList.add('bump');
      document.getElementById(cardId).classList.toggle('active', s[key] > 0);
    }
  }
}

function updatePhase(phase) {
  const badge = document.getElementById('phaseBadge');
  const labels = {
    searching: '🔍 Buscando fuentes',
    extracting: '🏢 Extrayendo empresas',
    enriching: '📞 Enriqueciendo contactos',
    done: '✅ Completado',
    error: '❌ Error',
    '': '',
  };
  badge.textContent = labels[phase] || phase;
  badge.className = `phase-badge${phase ? ' visible ' + phase : ''}`;
}

function updateProgress(phase) {
  const bar = document.getElementById('progressBar');
  const map = { searching: 20, extracting: 60, enriching: 85, done: 100 };
  if (phase === 'done') {
    bar.classList.remove('indeterminate');
    bar.style.width = '100%';
    setTimeout(() => { bar.style.width = '0%'; }, 2000);
  } else if (map[phase]) {
    bar.classList.add('indeterminate');
  }
}

function logMessage(msg, type = 'info') {
  const box = document.getElementById('logBox');
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  const ts = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  entry.textContent = `[${ts}] ${msg}`;
  box.appendChild(entry);
  box.scrollTop = box.scrollHeight;
}

function appendRow(company) {
  const tbody = document.getElementById('tableBody');

  // Quitar empty state si existe
  const empty = tbody.querySelector('.empty-state');
  if (empty) empty.closest('tr').remove();

  rowCount++;
  document.getElementById('resultsCount').textContent = `${rowCount} empresa${rowCount !== 1 ? 's' : ''} encontrada${rowCount !== 1 ? 's' : ''}`;

  const tr = document.createElement('tr');
  const web = company.web;
  const src = company.fuente;

  tr.innerHTML = `
    <td class="null-val">${rowCount}</td>
    <td class="td-empresa" title="${esc(company.empresa)}">${esc(company.empresa)}</td>
    <td class="td-sector"><span>${esc(company.sector)}</span></td>
    <td class="td-web">${web ? `<a href="${esc(web)}" target="_blank" rel="noopener" title="${esc(web)}">${shortUrl(web)}</a>` : '<span class="null-val">—</span>'}</td>
    <td class="td-email">${company.email ? esc(company.email) : '<span class="null-val">—</span>'}</td>
    <td class="td-phone">${company.telefono ? esc(company.telefono) : '<span class="null-val">—</span>'}</td>
    <td class="null-val" title="${esc(src || '')}">${src ? shortUrl(src) : '—'}</td>
  `;
  tbody.appendChild(tr);
}

function esc(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function shortUrl(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace('www.', '');
  } catch { return url; }
}

function resetStopButton() {
  const btn = document.getElementById('btnStop');
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="18" height="18" rx="2"/></svg> Parar`;
}

function enableExport() {
  document.getElementById('btnXlsx').disabled = false;
  document.getElementById('btnCsv').disabled = false;
}

function exportData(fmt) {
  if (!sessionId) return;
  window.location.href = `/api/export/${sessionId}/${fmt}`;
  toast(`📥 Descargando ${fmt.toUpperCase()}…`, 'success');
}

function toast(msg, type = 'info') {
  const wrap = document.getElementById('toastWrap');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Enter key en keywords ────────────────────
document.getElementById('keywords').addEventListener('keydown', e => {
  if (e.key === 'Enter') startScrape(false);
});

// ════════════════════════════════════════════
// ── Tabs ─────────────────────────────────────
// ════════════════════════════════════════════
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');
  document.getElementById('panel' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');
  if (tab === 'enrich') checkAiStatus();
}

// ════════════════════════════════════════════
// ── Enriquecimiento ───────────────────────────
// ════════════════════════════════════════════
let enrichFile      = null;
let enrichSessionId = null;
let enrichRunning   = false;
let enrichSource    = null;
let enrichRowCount  = 0;

// ── AI Status ─────────────────────────────────
let aiReady = false;

async function checkAiStatus() {
  try {
    const res  = await fetch('/api/check-ai');
    const data = await res.json();
    renderAiStatus(data.ok, data.message);
    aiReady = data.ok;
  } catch(e) {
    renderAiStatus(false, 'No se pudo verificar la API key');
  }
}

function renderAiStatus(ok, msg) {
  const bar = document.getElementById('aiStatusBar');
  const keySection = document.getElementById('apiKeySection');
  bar.style.display = 'block';
  if (ok) {
    bar.style.background = 'rgba(34,197,94,.07)';
    bar.style.borderColor = 'rgba(34,197,94,.3)';
    bar.style.color = 'var(--green)';
    bar.innerHTML = `🤖 <strong>Modo IA activo</strong> — Claude buscará en internet el contacto de cada empresa. ${msg}`;
    keySection.style.display = 'none';
  } else {
    bar.style.background = 'rgba(245,158,11,.07)';
    bar.style.borderColor = 'rgba(245,158,11,.3)';
    bar.style.color = 'var(--amber)';
    bar.innerHTML = `⚠️ <strong>Modo scraping básico</strong> — ${msg}.<br>
      Para mejores resultados con grandes empresas, añade tu API key de Anthropic:`;
    keySection.style.display = 'block';
  }
}

function onApiKeyChange(val) {
  document.getElementById('btnApplyKey').disabled = !val.startsWith('sk-ant-');
}

async function applyApiKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  if (!key) return;
  try {
    const res  = await fetch('/api/set-api-key', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({key}),
    });
    const data = await res.json();
    if (data.ok) {
      aiReady = true;
      renderAiStatus(true, data.message);
      toast('✅ API key activada — modo IA listo', 'success');
    } else {
      toast('❌ ' + data.message, 'error');
    }
  } catch(e) {
    toast('❌ Error: ' + e.message, 'error');
  }
}

// Comprobar AI al cargar la pestaña de enriquecimiento si ya está activa
if (document.getElementById('panelEnrich').classList.contains('active')) {
  checkAiStatus();
}

// ── Drag & drop ──────────────────────────────
const dropZone = document.getElementById('dropZone');
dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) onFileSelected(f);
});

function onFileSelected(file) {
  if (!file) return;
  const allowed = ['.csv','.xlsx','.xls','.xlsm','.tsv'];
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!allowed.includes(ext)) {
    toast('❌ Formato no permitido. Usa CSV o Excel.', 'error');
    return;
  }
  enrichFile = file;
  document.getElementById('chipName').textContent = file.name;
  document.getElementById('chipSize').textContent = formatBytes(file.size);
  document.getElementById('fileChip').classList.add('visible');
  document.getElementById('btnEnrich').disabled = false;
  document.getElementById('enrichHint').textContent = `${file.name} listo para procesar`;

  // Detección de columnas en el servidor (funciona con Excel y cualquier CSV)
  previewColumnsFromServer(file);
}

async function previewColumnsFromServer(file) {
  const box = document.getElementById('colDetect');
  box.style.display = 'block';
  box.innerHTML = '<span style="color:var(--text3)">⏳ Analizando columnas…</span>';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch('/api/preview', { method: 'POST', body: formData });
    const data = await res.json();

    if (!data.ok) {
      box.innerHTML = `<span style="color:var(--red)">❌ ${data.error || 'No se pudo leer el fichero'}</span>`;
      return;
    }

    const detected   = data.detected   || {};
    const undetected = data.undetected || [];
    const totalRows  = data.total_rows || 0;
    const headers    = data.headers    || [];

    // Construir línea de columnas detectadas
    const parts = Object.entries(detected).map(([k, v]) =>
      `<span style="color:var(--text2)">${k}</span> → <span style="color:var(--green);font-weight:600">${v}</span>`
    );
    const missing = undetected.map(k =>
      `<span style="color:var(--text3)">${k}: —</span>`
    );

    // Resumen de cabeceras encontradas en el fichero
    const headerList = headers.length
      ? `<span style="color:var(--text3);font-size:.65rem"> | Cabeceras en fichero: ${headers.join(', ')}</span>`
      : '';

    box.innerHTML =
      `<strong style="color:var(--text2)">Columnas detectadas</strong> `
      + `<span style="color:var(--text3);font-size:.68rem">(${totalRows} filas)</span>: &nbsp;`
      + [...parts, ...missing].join(' &nbsp;·&nbsp; ')
      + headerList;

    // Avisar si no se detectó empresa ni web (el agente no podrá funcionar)
    if (!detected.empresa && !detected.web) {
      box.innerHTML += `<br><span style="color:var(--red);font-size:.7rem">
        ⚠️ No se detectó columna de empresa ni web.
        Asegúrate de que las cabeceras incluyan palabras como
        <em>empresa</em>, <em>nombre</em>, <em>web</em> o <em>url</em>.
      </span>`;
      document.getElementById('btnEnrich').disabled = true;
    }

    // Actualizar hint con resumen
    document.getElementById('enrichHint').textContent =
      `${file.name} · ${totalRows} filas · ${Object.keys(detected).length} columnas detectadas`;

  } catch (e) {
    box.innerHTML = `<span style="color:var(--red)">❌ Error al analizar: ${e.message}</span>`;
  }
}

// ── Iniciar enriquecimiento ───────────────────
async function startEnrich() {
  if (enrichRunning || !enrichFile) return;

  setEnrichRunning(true);
  clearEnrichResults();

  const formData = new FormData();
  formData.append('file', enrichFile);

  try {
    const res = await fetch('/api/enrich', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.error) { toast('❌ ' + data.error, 'error'); setEnrichRunning(false); return; }
    enrichSessionId = data.session_id;
    connectEnrichSSE(enrichSessionId);
  } catch(e) {
    toast('❌ Error al subir fichero: ' + e.message, 'error');
    setEnrichRunning(false);
  }
}

function connectEnrichSSE(sid) {
  if (enrichSource) enrichSource.close();
  enrichSource = new EventSource(`/api/stream/${sid}`);
  enrichSource.onmessage = e => handleEnrichEvent(JSON.parse(e.data));
  enrichSource.onerror   = () => { enrichSource.close(); setEnrichRunning(false); };
}

function handleEnrichEvent(event) {
  if (event.type === 'ping') return;

  if (event.message) enrichLog(event.message, event.type || 'info');

  if (event.stats) updateEnrichStats(event.stats);

  if (event.type === 'row' && event.row) {
    appendEnrichRow(event.row, event.new_fields || []);
  }

  if (event.phase) {
    const badges = { reading:'📂 Leyendo', enriching:'🔍 Enriqueciendo', done:'✅ Listo', error:'❌ Error' };
    const b = document.getElementById('enrichPhaseBadge');
    b.textContent = badges[event.phase] || event.phase;
    b.className = `phase-badge visible ${event.phase}`;
  }

  if (event.type === 'summary' && event.summary) {
    document.getElementById('eValTotal').textContent = event.summary.total;
  }

  if (event.type === 'done') {
    setEnrichRunning(false);
    enableEnrichExport();
    toast(`✅ Enriquecimiento completado — ${event.stats?.enriched || 0} filas mejoradas`, 'success');
    if (enrichSource) enrichSource.close();
  }

  if (event.type === 'stopped') {
    setEnrichRunning(false);
    if (enrichRowCount > 0) enableEnrichExport();
    toast('⏹ Enriquecimiento detenido', 'info');
    if (enrichSource) enrichSource.close();
  }

  if (event.type === 'error') {
    setEnrichRunning(false);
    toast('❌ ' + event.message, 'error');
    if (enrichSource) enrichSource.close();
  }
}

async function stopEnrich() {
  if (!enrichSessionId) return;
  document.getElementById('btnEnrichStop').disabled = true;
  await fetch(`/api/stop/${enrichSessionId}`, { method: 'POST' }).catch(() => {});
  enrichLog('⏹ Solicitando parada…', 'info');
}

// ── Enrich UI helpers ────────────────────────
function setEnrichRunning(v) {
  enrichRunning = v;
  const btn = document.getElementById('btnEnrich');
  btn.classList.toggle('running', v);
  btn.disabled = v;
  document.getElementById('btnEnrichStop').disabled = !v;
  const pw = document.getElementById('enrichProgressWrap');
  const pb = document.getElementById('enrichProgressBar');
  const ls = document.getElementById('enrichLogSection');
  pw.style.display = v ? 'block' : 'block';
  ls.style.display = 'block';
  document.getElementById('enrichSummary').classList.add('visible');
  document.getElementById('enrichResultsWrap').style.display = 'block';
  if (v) pb.classList.add('indeterminate');
  else   pb.classList.remove('indeterminate');
}

function clearEnrichResults() {
  enrichRowCount = 0;
  document.getElementById('enrichTableBody').innerHTML = '';
  document.getElementById('enrichLogBox').innerHTML = '';
  document.getElementById('enrichCount').textContent = '0 filas';
  document.getElementById('btnEnrichXlsx').disabled = true;
  document.getElementById('btnEnrichCsv').disabled = true;
  updateEnrichStats({ total:0, enriched:0, emails:0, telefonos:0 });
}

function updateEnrichStats(s) {
  const map = { total:'eValTotal', enriched:'eValEnriched', emails:'eValEmails', telefonos:'eValTels' };
  for (const [k,id] of Object.entries(map)) {
    if (s[k] !== undefined) {
      const el = document.getElementById(id);
      if (el && el.textContent !== String(s[k])) {
        el.textContent = s[k];
        el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump');
      }
    }
  }
}

function enrichLog(msg, type = 'info') {
  const box = document.getElementById('enrichLogBox');
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  const ts = new Date().toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  entry.textContent = `[${ts}] ${msg}`;
  box.appendChild(entry);
  box.scrollTop = box.scrollHeight;
}

function appendEnrichRow(row, newFields = []) {
  const tbody = document.getElementById('enrichTableBody');
  enrichRowCount++;
  document.getElementById('enrichCount').textContent =
    `${enrichRowCount} fila${enrichRowCount !== 1 ? 's' : ''}`;

  const tr = document.createElement('tr');
  if (newFields.includes('email'))    tr.classList.add('row-new-email');
  if (newFields.includes('teléfono')) tr.classList.add('row-new-phone');
  if (!row.email && !row.telefono)    tr.classList.add('row-missing');

  const web = row.web || '';
  tr.innerHTML = `
    <td class="null-val">${enrichRowCount}</td>
    <td class="td-empresa" title="${esc(row.empresa)}">${esc(row.empresa)}</td>
    <td class="td-sector"><span>${esc(row.sector || '—')}</span></td>
    <td class="td-web">${web ? `<a href="${esc(web)}" target="_blank" rel="noopener">${shortUrl(web)}</a>` : '<span class="null-val">—</span>'}</td>
    <td class="${newFields.includes('email') ? 'td-email' : ''}">${row.email ? esc(row.email) : '<span class="null-val">—</span>'}</td>
    <td class="${newFields.includes('teléfono') ? 'td-phone' : ''}">${row.telefono ? esc(row.telefono) : '<span class="null-val">—</span>'}</td>
    <td class="null-val" title="${esc(row.fuente||'')}">${row.fuente ? shortUrl(row.fuente) : '—'}</td>
  `;
  tbody.appendChild(tr);
}

function enableEnrichExport() {
  document.getElementById('btnEnrichXlsx').disabled = false;
  document.getElementById('btnEnrichCsv').disabled = false;
}

function exportEnrich(fmt) {
  if (!enrichSessionId) return;
  window.location.href = `/api/export/${enrichSessionId}/${fmt}`;
  toast(`📥 Descargando ${fmt.toUpperCase()}…`, 'success');
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/1048576).toFixed(1) + ' MB';
}