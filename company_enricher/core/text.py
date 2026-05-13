from __future__ import annotations

import re
import unicodedata


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_company_name(name: str) -> str:
    normalized = normalize_text(name)
    legal_forms = (
        "s l", "sl", "s l u", "slu", "s a", "sa", "s a u", "sau",
        "sociedad limitada", "sociedad anonima", "cb", "c b", "sc", "s coop",
    )
    for form in legal_forms:
        normalized = re.sub(rf"\b{re.escape(form)}\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def token_overlap(a: str, b: str) -> float:
    left = set(compact_company_name(a).split())
    right = set(compact_company_name(b).split())
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left), len(right))
