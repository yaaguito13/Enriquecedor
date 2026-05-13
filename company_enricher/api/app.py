from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from company_enricher.core.config import BASE_DIR, settings
from company_enricher.services.job_manager import job_manager


app = FastAPI(title=settings.app_name)

WEB_DIR = BASE_DIR / "company_enricher" / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "templates" / "index.html")


@app.post("/api/jobs")
async def create_job(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        job = await job_manager.create_job(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job.job_id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return job.snapshot()


@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str) -> dict[str, bool]:
    if not job_manager.pause(job_id):
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return {"ok": True}


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str) -> dict[str, bool]:
    if not job_manager.resume(job_id):
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return {"ok": True}


@app.get("/api/jobs/{job_id}/download/{artifact}")
async def download(job_id: str, artifact: str) -> FileResponse:
    job = job_manager.get(job_id)
    if not job or not job.artifacts:
        raise HTTPException(status_code=404, detail="Archivo no disponible todavía")
    artifact_map = {
        "excel": job.artifacts.enriched_excel,
        "errors": job.artifacts.errors_csv,
        "not-found": job.artifacts.not_found_csv,
        "logs": job.artifacts.log_file,
    }
    path: Path | None = artifact_map.get(artifact)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=path.name)
