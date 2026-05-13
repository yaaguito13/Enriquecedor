from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ColumnMapping:
    company: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    confidence: dict[str, float] = field(default_factory=dict)


@dataclass
class CompanyRecord:
    row_number: int
    company_name: str
    existing_phone: str | None = None
    existing_email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactCandidate:
    value: str
    kind: str
    source_url: str
    score: float
    reason: str


@dataclass
class EnrichmentResult:
    record: CompanyRecord
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    source_url: str | None = None
    confidence: float = 0.0
    status: str = "not_found"
    error: str | None = None
    candidates: list[ContactCandidate] = field(default_factory=list)


@dataclass
class ExportArtifacts:
    enriched_excel: Path
    errors_csv: Path
    not_found_csv: Path
    log_file: Path


@dataclass
class JobProgress:
    job_id: str
    status: str
    total: int = 0
    processed: int = 0
    found: int = 0
    not_found: int = 0
    errors: int = 0
    current: str = ""
    message: str = ""
    percent: float = 0.0
    results_preview: list[dict[str, Any]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    download_url: str | None = None
