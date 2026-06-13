from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    from duckduckgo_search import DDGS
except ModuleNotFoundError:
    requests = None
    BeautifulSoup = None
    DDGS = None

from .models import RecruiterContact


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4})")


def search_recruiter_evidence(company_name: str, role: str, application_link: str, max_results: int = 5) -> list[dict[str, str]]:
    if DDGS is None:
        return []
    query_parts = [company_name.strip(), "recruiter contact"]
    if role.strip():
        query_parts.insert(1, role.strip())
    if application_link.strip():
        domain = urlparse(application_link).netloc
        if domain:
            query_parts.append(domain)
    query = " ".join(part for part in query_parts if part)

    results: list[dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                url = item.get("href") or item.get("url") or ""
                if not url:
                    continue
                page_text = _fetch_page_text(url)
                evidence = _summarize_contact_signals(page_text)
                results.append(
                    {
                        "title": item.get("title", ""),
                        "href": url,
                        "snippet": item.get("body", ""),
                        "page_text": page_text[:4000],
                        "signals": evidence,
                    }
                )
    except Exception:
        return []
    return results


def extract_recruiter_contact(company_name: str, evidence: Iterable[dict[str, str]]) -> RecruiterContact:
    evidence_list = list(evidence)
    best_email = ""
    best_phone = ""
    source_url = ""
    source_title = ""
    notes = ""

    for item in evidence_list:
        text = " ".join([item.get("title", ""), item.get("snippet", ""), item.get("signals", ""), item.get("page_text", "")])
        email_match = EMAIL_RE.search(text)
        phone_match = PHONE_RE.search(text)
        if email_match and not best_email:
            best_email = email_match.group(0)
            source_url = item.get("href", "")
            source_title = item.get("title", "")
        if phone_match and not best_phone:
            best_phone = phone_match.group(0)
            source_url = source_url or item.get("href", "")
            source_title = source_title or item.get("title", "")
        if best_email and best_phone:
            break

    if not best_email and not best_phone:
        notes = f"No public recruiter email/phone surfaced for {company_name} from the searched sources."

    return RecruiterContact(
        recruiter_name="",
        recruiter_email=best_email,
        recruiter_phone=best_phone,
        source_url=source_url,
        source_title=source_title,
        notes=notes or f"Sources reviewed: {len(evidence_list)}",
    )


def _fetch_page_text(url: str) -> str:
    if requests is None or BeautifulSoup is None:
        return ""
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text


def _summarize_contact_signals(text: str) -> str:
    if not text:
        return ""
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    parts = []
    if emails:
        parts.append("emails: " + ", ".join(sorted(set(emails))[:5]))
    if phones:
        parts.append("phones: " + ", ".join(sorted(set(phones))[:5]))
    return " | ".join(parts)
