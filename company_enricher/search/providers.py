from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup

from company_enricher.core.config import settings
from company_enricher.core.models import CompanyRecord
from company_enricher.core.validators import ensure_url, is_probably_website
from company_enricher.search.cache import JsonCache
from company_enricher.search.http import HttpClient


BLOCKED_HOST_PARTS = (
    "facebook.", "instagram.", "linkedin.", "twitter.", "x.com", "youtube.",
    "einforma.", "empresite.", "axesor.", "infocif.", "iberinform.",
    "expansion.com/directorio", "guia", "paginasamarillas",
)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class DuckDuckGoSearch:
    namespace = "duckduckgo"

    def __init__(self, cache: JsonCache, client: HttpClient) -> None:
        self.cache = cache
        self.client = client

    async def search_company(self, record: CompanyRecord, limit: int = 8) -> list[SearchResult]:
        location = " ".join(part for part in (record.city, record.province) if part)
        query = f'"{record.company_name}" {location} contacto telefono email web empresa España'
        cached = self.cache.get(self.namespace, query)
        if cached is not None:
            return [SearchResult(**item) for item in cached]

        await asyncio.sleep(settings.search_delay_seconds)
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        html = await self.client.get_text(url)
        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []
        for item in soup.select(".result"):
            anchor = item.select_one(".result__a")
            if not anchor or not anchor.get("href"):
                continue
            result_url = ensure_url(anchor["href"])
            snippet = item.select_one(".result__snippet")
            result = SearchResult(
                title=anchor.get_text(" ", strip=True),
                url=result_url,
                snippet=snippet.get_text(" ", strip=True) if snippet else "",
            )
            if _is_useful_result(result.url):
                results.append(result)
            if len(results) >= limit:
                break
        self.cache.set(self.namespace, query, [result.__dict__ for result in results])
        return results


class SeedUrlProvider:
    def urls_for(self, record: CompanyRecord, search_results: list[SearchResult]) -> list[str]:
        urls: list[str] = []
        if record.website and is_probably_website(record.website):
            urls.append(ensure_url(record.website))
        for result in search_results:
            urls.append(result.url)
        return _dedupe_hosts(urls)


def _is_useful_result(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return False
    return not any(part in host or part in url.lower() for part in BLOCKED_HOST_PARTS)


def _dedupe_hosts(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        parsed = urlparse(ensure_url(url))
        host = parsed.netloc.lower().replace("www.", "")
        if not host or host in seen:
            continue
        seen.add(host)
        deduped.append(parsed.geturl())
    return deduped
