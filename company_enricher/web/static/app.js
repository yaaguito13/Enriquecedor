const state = {
  file: null,
  jobId: null,
  pollTimer: null,
};

const els = {
  dropzone: document.querySelector("#dropzone"),
  fileInput: document.querySelector("#fileInput"),
  fileName: document.querySelector("#fileName"),
  startBtn: document.querySelector("#startBtn"),
  pauseBtn: document.querySelector("#pauseBtn"),
  resumeBtn: document.querySelector("#resumeBtn"),
  downloadExcel: document.querySelector("#downloadExcel"),
  downloadLogs: document.querySelector("#downloadLogs"),
  statusText: document.querySelector("#statusText"),
  percentText: document.querySelector("#percentText"),
  progressFill: document.querySelector("#progressFill"),
  currentText: document.querySelector("#currentText"),
  processedStat: document.querySelector("#processedStat"),
  foundStat: document.querySelector("#foundStat"),
  notFoundStat: document.querySelector("#notFoundStat"),
  errorStat: document.querySelector("#errorStat"),
  resultsBody: document.querySelector("#resultsBody"),
  previewCount: document.querySelector("#previewCount"),
  logsBox: document.querySelector("#logsBox"),
  jobIdText: document.querySelector("#jobIdText"),
  connectionStatus: document.querySelector("#connectionStatus"),
  toast: document.querySelector("#toast"),
};

function setFile(file) {
  state.file = file;
  els.fileName.textContent = file ? `${file.name} · ${formatBytes(file.size)}` : "Ningún archivo seleccionado";
  els.startBtn.disabled = !file;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  window.clearTimeout(els.toast._timer);
  els.toast._timer = window.setTimeout(() => {
    els.toast.hidden = true;
  }, 4200);
}

els.fileInput.addEventListener("change", (event) => {
  setFile(event.target.files[0]);
});

["dragenter", "dragover"].forEach((eventName) => {
  els.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  els.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropzone.classList.remove("dragover");
  });
});

els.dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  if (!file.name.match(/\.(xlsx|xlsm)$/i)) {
    showToast("El archivo debe ser .xlsx o .xlsm.");
    return;
  }
  setFile(file);
});

els.startBtn.addEventListener("click", async () => {
  if (!state.file) return;
  resetUiForJob();
  const formData = new FormData();
  formData.append("file", state.file);
  try {
    els.connectionStatus.textContent = "Subiendo";
    const response = await fetch("/api/jobs", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudo crear el trabajo.");
    state.jobId = payload.job_id;
    els.jobIdText.textContent = state.jobId;
    els.pauseBtn.disabled = false;
    startPolling();
  } catch (error) {
    showToast(error.message);
    els.connectionStatus.textContent = "Error";
    els.startBtn.disabled = false;
  }
});

els.pauseBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  await fetch(`/api/jobs/${state.jobId}/pause`, { method: "POST" });
  els.pauseBtn.disabled = true;
  els.resumeBtn.disabled = false;
});

els.resumeBtn.addEventListener("click", async () => {
  if (!state.jobId) return;
  await fetch(`/api/jobs/${state.jobId}/resume`, { method: "POST" });
  els.pauseBtn.disabled = false;
  els.resumeBtn.disabled = true;
});

function resetUiForJob() {
  els.startBtn.disabled = true;
  els.downloadExcel.classList.add("disabled");
  els.downloadLogs.classList.add("disabled");
  els.resultsBody.innerHTML = `<tr><td colspan="5" class="empty">Procesando empresas...</td></tr>`;
  els.logsBox.textContent = "Creando trabajo...\n";
  updateProgress({ percent: 0, processed: 0, found: 0, not_found: 0, errors: 0, status: "queued", message: "En cola" });
}

function startPolling() {
  window.clearInterval(state.pollTimer);
  state.pollTimer = window.setInterval(fetchProgress, 1200);
  fetchProgress();
}

async function fetchProgress() {
  if (!state.jobId) return;
  try {
    const response = await fetch(`/api/jobs/${state.jobId}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudo leer el progreso.");
    updateProgress(payload);
    updateResults(payload.results_preview || []);
    updateLogs(payload.logs || []);
    if (["completed", "failed"].includes(payload.status)) {
      window.clearInterval(state.pollTimer);
      els.pauseBtn.disabled = true;
      els.resumeBtn.disabled = true;
      els.startBtn.disabled = false;
      if (payload.status === "completed") {
        enableDownload(payload);
      }
    }
  } catch (error) {
    showToast(error.message);
    els.connectionStatus.textContent = "Reconectando";
  }
}

function updateProgress(payload) {
  const percent = Number(payload.percent || 0);
  els.statusText.textContent = payload.message || statusLabel(payload.status);
  els.percentText.textContent = `${percent.toFixed(0)}%`;
  els.progressFill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  els.currentText.textContent = payload.current ? `Ahora: ${payload.current}` : statusLabel(payload.status);
  els.processedStat.textContent = payload.processed || 0;
  els.foundStat.textContent = payload.found || 0;
  els.notFoundStat.textContent = payload.not_found || 0;
  els.errorStat.textContent = payload.errors || 0;
  els.connectionStatus.textContent = statusLabel(payload.status);
}

function statusLabel(status) {
  const labels = {
    queued: "En cola",
    running: "Procesando",
    paused: "Pausado",
    completed: "Completado",
    failed: "Error",
  };
  return labels[status] || "Listo";
}

function updateResults(results) {
  els.previewCount.textContent = `${results.length} resultados`;
  if (!results.length) {
    els.resultsBody.innerHTML = `<tr><td colspan="5" class="empty">Los resultados aparecerán aquí.</td></tr>`;
    return;
  }
  els.resultsBody.innerHTML = results.slice().reverse().map((row) => {
    const badgeClass = row.estado.includes("found") ? "ok" : row.estado === "error" ? "error" : "warn";
    return `
      <tr>
        <td>${escapeHtml(row.empresa)}</td>
        <td>${escapeHtml(row.telefono || "-")}</td>
        <td>${escapeHtml(row.email || "-")}</td>
        <td><span class="badge ${badgeClass}">${escapeHtml(row.estado)}</span></td>
        <td>${escapeHtml(String(row.confianza || 0))}%</td>
      </tr>
    `;
  }).join("");
}

function updateLogs(logs) {
  els.logsBox.textContent = logs.length ? logs.join("\n") : "Sin logs todavía.";
  els.logsBox.scrollTop = els.logsBox.scrollHeight;
}

function enableDownload(payload) {
  els.downloadExcel.href = payload.download_url;
  els.downloadExcel.classList.remove("disabled");
  els.downloadLogs.href = `/api/jobs/${state.jobId}/download/logs`;
  els.downloadLogs.classList.remove("disabled");
  showToast("Excel enriquecido listo para descargar.");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
