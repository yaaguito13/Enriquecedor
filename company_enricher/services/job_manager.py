from __future__ import annotations

import asyncio
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from company_enricher.core.config import settings
from company_enricher.core.excel import export_results, load_records, result_to_preview
from company_enricher.core.models import EnrichmentResult, ExportArtifacts, JobProgress
from company_enricher.search.cache import JsonCache
from company_enricher.search.enricher import CompanyEnricher
from company_enricher.search.http import HttpClient
from company_enricher.utils.logging import build_job_logger


class EnrichmentJob:
    def __init__(self, job_id: str, input_path: Path) -> None:
        self.job_id = job_id
        self.input_path = input_path
        self.progress = JobProgress(job_id=job_id, status="queued", message="Trabajo en cola")
        self.results: list[EnrichmentResult] = []
        self.artifacts: ExportArtifacts | None = None
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.cancelled = False
        self.task: asyncio.Task[None] | None = None
        self.logger, self.log_file = build_job_logger(job_id, settings.log_dir)

    def snapshot(self) -> dict[str, Any]:
        progress = asdict(self.progress)
        progress["paused"] = not self.pause_event.is_set()
        return progress

    def append_log(self, message: str) -> None:
        self.logger.info(message)
        self.progress.logs.append(message)
        self.progress.logs = self.progress.logs[-120:]


class JobManager:
    def __init__(self) -> None:
        settings.ensure_dirs()
        self.jobs: dict[str, EnrichmentJob] = {}
        self.cache = JsonCache(settings.cache_dir)

    async def create_job(self, file: UploadFile) -> EnrichmentJob:
        if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("Sube un archivo Excel .xlsx o .xlsm.")
        job_id = uuid.uuid4().hex[:12]
        destination = settings.upload_dir / f"{job_id}_{Path(file.filename).name}"
        with destination.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        if destination.stat().st_size > settings.max_upload_mb * 1024 * 1024:
            destination.unlink(missing_ok=True)
            raise ValueError(f"El archivo supera el límite de {settings.max_upload_mb} MB.")
        job = EnrichmentJob(job_id, destination)
        self.jobs[job_id] = job
        job.task = asyncio.create_task(self._run_job(job))
        return job

    def get(self, job_id: str) -> EnrichmentJob | None:
        return self.jobs.get(job_id)

    def pause(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job:
            return False
        job.pause_event.clear()
        job.progress.status = "paused"
        job.progress.message = "Procesamiento pausado"
        job.append_log("Trabajo pausado por el usuario")
        return True

    def resume(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job:
            return False
        job.pause_event.set()
        if job.progress.status == "paused":
            job.progress.status = "running"
        job.progress.message = "Procesamiento reanudado"
        job.append_log("Trabajo reanudado por el usuario")
        return True

    async def _run_job(self, job: EnrichmentJob) -> None:
        client = HttpClient()
        try:
            job.progress.status = "running"
            job.append_log("Leyendo Excel y detectando columnas")
            header_row, mapping, records = load_records(job.input_path)
            job.progress.total = len(records)
            job.progress.message = f"Detectadas {len(records)} empresas"
            job.append_log(f"Columnas detectadas: {mapping}")

            if not records:
                raise ValueError("No se encontraron empresas para procesar.")

            enricher = CompanyEnricher(self.cache, client)
            semaphore = asyncio.Semaphore(settings.max_concurrency)
            result_slots: list[EnrichmentResult | None] = [None] * len(records)

            async def process_one(index: int) -> None:
                record = records[index]
                await job.pause_event.wait()
                async with semaphore:
                    await job.pause_event.wait()
                    job.progress.current = record.company_name
                    job.append_log(f"Procesando: {record.company_name}")

                    async def progress_callback(_, message: str) -> None:
                        job.progress.current = record.company_name
                        job.progress.message = message

                    result = await enricher.enrich(record, progress_callback)
                    result_slots[index] = result
                    self._mark_processed(job, result)

            await asyncio.gather(*(process_one(index) for index in range(len(records))))
            job.results = [result for result in result_slots if result is not None]
            job.progress.message = "Exportando resultados"
            job.append_log("Exportando Excel enriquecido y CSV auxiliares")
            job.artifacts = export_results(
                input_path=job.input_path,
                output_dir=settings.output_dir,
                job_id=job.job_id,
                header_row=header_row,
                results=job.results,
                log_file=job.log_file,
            )
            job.progress.status = "completed"
            job.progress.percent = 100
            job.progress.current = ""
            job.progress.message = "Procesamiento completado"
            job.progress.download_url = f"/api/jobs/{job.job_id}/download/excel"
            job.append_log("Trabajo completado")
        except Exception as exc:
            job.progress.status = "failed"
            job.progress.message = str(exc)
            job.progress.errors += 1
            job.append_log(f"Error fatal: {exc}")
        finally:
            await client.close()

    def _mark_processed(self, job: EnrichmentJob, result: EnrichmentResult) -> None:
        job.progress.processed += 1
        if result.status == "error":
            job.progress.errors += 1
        elif result.status == "not_found":
            job.progress.not_found += 1
        else:
            job.progress.found += 1
        job.progress.percent = round(job.progress.processed / max(job.progress.total, 1) * 100, 1)
        preview = result_to_preview(result)
        job.progress.results_preview.append(preview)
        job.progress.results_preview = job.progress.results_preview[-80:]
        job.append_log(f"{result.record.company_name}: {result.status}")


job_manager = JobManager()
