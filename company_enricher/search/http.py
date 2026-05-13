from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx

from company_enricher.core.config import settings


class HttpClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            headers={"User-Agent": settings.user_agent},
        )

    async def get_text(self, url: str, retries: int = 2) -> str:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text" not in content_type and "html" not in content_type and "xml" not in content_type:
                    return ""
                return response.text
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                await asyncio.sleep(0.4 * (attempt + 1))
        raise RuntimeError(f"No se pudo descargar {url}: {last_error}")

    async def close(self) -> None:
        await self._client.aclose()


async def with_client(fn: Callable[[HttpClient], Awaitable[None]]) -> None:
    client = HttpClient()
    try:
        await fn(client)
    finally:
        await client.close()
