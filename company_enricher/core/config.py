from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


def _path(name: str, default: str) -> Path:
    return (BASE_DIR / os.getenv(name, default)).resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Enriquecedor Excel Empresas")
    environment: str = os.getenv("ENVIRONMENT", "local")
    upload_dir: Path = _path("UPLOAD_DIR", "data/uploads")
    output_dir: Path = _path("OUTPUT_DIR", "data/outputs")
    log_dir: Path = _path("LOG_DIR", "data/logs")
    cache_dir: Path = _path("CACHE_DIR", "data/cache")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "30"))
    max_concurrency: int = int(os.getenv("MAX_CONCURRENCY", "5"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
    search_delay_seconds: float = float(os.getenv("SEARCH_DELAY_SECONDS", "0.8"))
    max_crawl_pages_per_company: int = int(os.getenv("MAX_CRAWL_PAGES_PER_COMPANY", "4"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; ExcelCompanyEnricher/1.0; +local)",
    )

    def ensure_dirs(self) -> None:
        for directory in (self.upload_dir, self.output_dir, self.log_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
