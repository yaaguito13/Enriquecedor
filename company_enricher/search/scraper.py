from __future__ import annotations

from collections import deque
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from company_enricher.core.config import settings
from company_enricher.core.models import ContactCandidate, CompanyRecord
from company_enricher.core.text import token_overlap
from company_enricher.core.validators import extract_emails, extract_spanish_phones, score_email
from company_enricher.search.cache import JsonCache
from company_enricher.search.http import HttpClient


CONTACT_WORDS = ("contact", "contacto", "empresa", "quienes", "aviso", "legal")


class SiteScraper:
    namespace = "site"

    def __init__(self, cache: JsonCache, client: HttpClient) -> None:
        self.cache = cache
        self.client = client

    async def scrape(self, url: str, record: CompanyRecord) -> list[ContactCandidate]:
        cached = self.cache.get(self.namespace, f"{record.company_name}|{url}")
        if cached is not None:
            return [ContactCandidate(**item) for item in cached]

        candidates: list[ContactCandidate] = []
        visited: set[str] = set()
        queue: deque[str] = deque([url])
        base_host = urlparse(url).netloc.lower().replace("www.", "")

        while queue and len(visited) < settings.max_crawl_pages_per_company:
            current_url = queue.popleft()
            if current_url in visited:
                continue
            visited.add(current_url)
            try:
                html = await self.client.get_text(current_url)
            except RuntimeError:
                continue
            if not html:
                continue
            page_candidates, links = self._extract_from_html(html, current_url, record, base_host)
            candidates.extend(page_candidates)
            for link in links:
                if link not in visited:
                    queue.append(link)

        best = _dedupe_candidates(candidates)
        self.cache.set(self.namespace, f"{record.company_name}|{url}", [item.__dict__ for item in best])
        return best

    def _extract_from_html(
        self,
        html: str,
        current_url: str,
        record: CompanyRecord,
        base_host: str,
    ) -> tuple[list[ContactCandidate], list[str]]:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        body = soup.get_text(" ", strip=True)
        page_relevance = token_overlap(record.company_name, f"{title} {body[:1200]}")
        candidates: list[ContactCandidate] = []
        for phone in extract_spanish_phones(body):
            candidates.append(
                ContactCandidate(
                    value=phone,
                    kind="phone",
                    source_url=current_url,
                    score=min(1.0, 0.55 + page_relevance * 0.35),
                    reason="Teléfono español detectado en web candidata",
                )
            )
        for email in extract_emails(body):
            candidates.append(
                ContactCandidate(
                    value=email,
                    kind="email",
                    source_url=current_url,
                    score=min(1.0, score_email(email, current_url) + page_relevance * 0.25),
                    reason="Email detectado en web candidata",
                )
            )
        links = self._contact_links(soup, current_url, base_host)
        return candidates, links

    def _contact_links(self, soup: BeautifulSoup, current_url: str, base_host: str) -> list[str]:
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True).lower()
            href = anchor["href"].lower()
            if not any(word in text or word in href for word in CONTACT_WORDS):
                continue
            absolute = urljoin(current_url, anchor["href"])
            parsed = urlparse(absolute)
            host = parsed.netloc.lower().replace("www.", "")
            if host == base_host and parsed.scheme in {"http", "https"}:
                links.append(absolute)
        return list(dict.fromkeys(links))[:4]


def _dedupe_candidates(candidates: list[ContactCandidate]) -> list[ContactCandidate]:
    best_by_key: dict[tuple[str, str], ContactCandidate] = {}
    for candidate in candidates:
        key = (candidate.kind, candidate.value)
        if key not in best_by_key or candidate.score > best_by_key[key].score:
            best_by_key[key] = candidate
    return sorted(best_by_key.values(), key=lambda item: item.score, reverse=True)
