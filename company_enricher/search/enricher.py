from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from company_enricher.core.models import CompanyRecord, EnrichmentResult
from company_enricher.core.validators import normalize_email, normalize_spanish_phone
from company_enricher.search.cache import JsonCache
from company_enricher.search.http import HttpClient
from company_enricher.search.providers import DuckDuckGoSearch, SeedUrlProvider
from company_enricher.search.scraper import SiteScraper


ProgressCallback = Callable[[CompanyRecord, str], Awaitable[None]]


class CompanyEnricher:
    def __init__(self, cache: JsonCache, client: HttpClient) -> None:
        self.search = DuckDuckGoSearch(cache, client)
        self.seed_urls = SeedUrlProvider()
        self.scraper = SiteScraper(cache, client)

    async def enrich(self, record: CompanyRecord, progress: ProgressCallback | None = None) -> EnrichmentResult:
        try:
            existing_phone = normalize_spanish_phone(record.existing_phone or "")
            existing_email = normalize_email(record.existing_email or "")
            if existing_phone and existing_email:
                return EnrichmentResult(
                    record=record,
                    phone=existing_phone,
                    email=existing_email,
                    website=record.website,
                    confidence=0.95,
                    status="found_existing",
                )

            if progress:
                await progress(record, "Buscando resultados web")
            search_results = await self.search.search_company(record)
            urls = self.seed_urls.urls_for(record, search_results)
            all_candidates = []
            for url in urls[:5]:
                if progress:
                    await progress(record, f"Analizando {url}")
                all_candidates.extend(await self.scraper.scrape(url, record))

            phone_candidate = _best(all_candidates, "phone")
            email_candidate = _best(all_candidates, "email")
            source_url = (
                phone_candidate.source_url if phone_candidate else None
            ) or (
                email_candidate.source_url if email_candidate else None
            )
            website = source_url or record.website
            phone = existing_phone or (phone_candidate.value if phone_candidate else None)
            email = existing_email or (email_candidate.value if email_candidate else None)
            confidence_values = [item.score for item in (phone_candidate, email_candidate) if item]
            confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            status = "found" if phone or email else "not_found"
            if phone and email:
                status = "found_complete"
            elif phone or email:
                status = "found_partial"

            return EnrichmentResult(
                record=record,
                phone=phone,
                email=email,
                website=website,
                source_url=source_url,
                confidence=confidence,
                status=status,
                candidates=all_candidates[:10],
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return EnrichmentResult(record=record, status="error", error=str(exc))


def _best(candidates: list, kind: str):
    filtered = [candidate for candidate in candidates if candidate.kind == kind]
    if not filtered:
        return None
    return max(filtered, key=lambda item: item.score)
