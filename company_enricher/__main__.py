from __future__ import annotations

import uvicorn

from company_enricher.core.config import settings


def main() -> None:
    settings.ensure_dirs()
    uvicorn.run("company_enricher.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
