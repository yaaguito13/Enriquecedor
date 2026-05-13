from __future__ import annotations

import re
from urllib.parse import urlparse

import phonenumbers


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
NOISE_EMAIL_PREFIXES = {
    "noreply",
    "no-reply",
    "donotreply",
    "example",
    "test",
    "prueba",
}
GENERIC_ALLOWED = {
    "info",
    "contacto",
    "administracion",
    "comercial",
    "ventas",
    "clientes",
    "atencioncliente",
    "hola",
}


def extract_emails(text: str) -> list[str]:
    seen: set[str] = set()
    emails: list[str] = []
    for match in EMAIL_RE.findall(text or ""):
        email = normalize_email(match)
        if email and email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def normalize_email(email: str) -> str | None:
    cleaned = email.strip(" .,:;()[]{}<>").lower()
    if not EMAIL_RE.fullmatch(cleaned):
        return None
    local, domain = cleaned.split("@", 1)
    if local in NOISE_EMAIL_PREFIXES:
        return None
    if any(domain.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return None
    return cleaned


def score_email(email: str, website: str | None = None) -> float:
    local, domain = email.split("@", 1)
    score = 0.45
    if local in GENERIC_ALLOWED:
        score += 0.25
    if website:
        host = urlparse(ensure_url(website)).netloc.replace("www.", "")
        if host and (domain == host or domain.endswith("." + host) or host.endswith(domain)):
            score += 0.25
    if any(token in local for token in ("rrhh", "jobs", "empleo", "privacy", "legal")):
        score -= 0.2
    return max(0.0, min(score, 1.0))


def extract_spanish_phones(text: str) -> list[str]:
    candidates = set(re.findall(r"(?:\+34[\s.-]?)?(?:[6897]\d[\s.-]?){4}\d", text or ""))
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        phone = normalize_spanish_phone(candidate)
        if phone and phone not in seen:
            seen.add(phone)
            normalized.append(phone)
    return normalized


def normalize_spanish_phone(value: str) -> str | None:
    raw = re.sub(r"[^\d+]", "", value or "")
    if raw.startswith("0034"):
        raw = "+34" + raw[4:]
    if raw.startswith("34") and len(raw) == 11:
        raw = "+34" + raw[2:]
    if not raw.startswith("+"):
        raw = "+34" + raw
    try:
        parsed = phonenumbers.parse(raw, "ES")
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number_for_region(parsed, "ES"):
        return None
    national = str(parsed.national_number)
    if national.startswith(("6", "7")):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


def ensure_url(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


def is_probably_website(value: str) -> bool:
    value = value.strip().lower()
    return "." in value and "@" not in value and not value.endswith((".png", ".jpg", ".pdf"))
