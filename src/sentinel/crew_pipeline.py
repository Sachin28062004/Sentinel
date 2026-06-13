from __future__ import annotations

import re

from .config import Settings
from .models import EmailRecord, PlacementExtraction, RecruiterContact


def analyze_email_with_crew(settings: Settings, email: EmailRecord) -> PlacementExtraction:
    return _local_email_extraction(email)


def refine_recruiter_contact_with_crew(
    settings: Settings,
    company_name: str,
    role: str,
    evidence: list[dict[str, str]],
    fallback_contact: RecruiterContact,
) -> RecruiterContact:
    return fallback_contact


def _local_email_extraction(email: EmailRecord) -> PlacementExtraction:
    text = " ".join([email.subject, email.from_email, email.snippet, email.body_text])
    lower = text.lower()

    application_patterns = [
        r"\bthank you for applying\b",
        r"\bthank you for your application\b",
        r"\byour application to\b",
        r"\bapplication received\b",
        r"\bwe(?:'|’)re currently in the process of taking and reviewing applications\b",
        r"\bwe(?:'|’)ve received your application\b",
        r"\bwe have received your application\b",
    ]
    is_related = any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in application_patterns)

    company_name = _guess_company_name(email)
    role = _extract_role(text)
    application_link = _extract_application_link(text)
    status = _extract_status(lower)
    job_type = _extract_job_type(lower)

    return PlacementExtraction(
        is_placement_related=is_related,
        company_name=company_name,
        date_applied=email.internal_date.astimezone().strftime("%d-%m-%Y"),
        role=role,
        application_link=application_link,
        status=status,
        job_type=job_type,
        confidence=0.98 if is_related else 0.02,
    )


def _guess_company_name(email: EmailRecord) -> str:
    subject = email.subject.strip()
    subject_patterns = [
        r"^([A-Z][A-Z0-9&.\- ]{2,60})\s*-\s*thank you for applying",
        r"^([A-Z][A-Z0-9&.\- ]{2,60})\s*-\s*application received",
        r"^your application to\s+([A-Z][A-Za-z0-9&.\- ]{2,60})",
    ]
    for pattern in subject_patterns:
        match = re.search(pattern, subject, flags=re.IGNORECASE)
        if match:
            company = match.group(1).strip(" .,-")
            if company:
                return company.lower()

    display_name = email.from_email.split("<", 1)[0].strip().strip('"').strip("'")
    if display_name:
        display_name = re.sub(
            r"\b(Human Resources|HR|Recruiting Team|Recruiting|Recruitment|Do Not Reply|Donotreply|No Reply)\b.*$",
            "",
            display_name,
            flags=re.IGNORECASE,
        ).strip()
        if display_name:
            parts = display_name.split()
            if parts:
                return parts[0].strip(" .,-").lower()

    from_email = email.from_email.lower()
    domain_match = re.search(r"@([a-z0-9.-]+)", from_email)
    if domain_match:
        domain = domain_match.group(1)
        parts = [part for part in domain.split(".") if part]
        generic = {"careers", "career", "jobs", "job", "hiring", "recruiting", "recruitment", "talent", "apply", "mail", "noreply", "no-reply"}
        for part in reversed(parts[:-1] if len(parts) > 1 else parts):
            if part not in generic:
                return part.replace("-", " ").replace("_", " ").strip().lower()

    body_patterns = [
        r"thank you for applying for the (.+?) position with ([A-Z][A-Za-z0-9&.\- ]{2,60})",
        r"thank you for taking the time to complete your application for our (.+?)(?:\.|$)",
        r"your application to ([A-Z][A-Za-z0-9&.\- ]{2,60})",
        r"application received[:\s]+(.+?)\bposition\b.*?\bwith\s+([A-Z][A-Za-z0-9&.\- ]{2,60})",
    ]
    for pattern in body_patterns:
        match = re.search(pattern, email.body_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            if match.lastindex and match.lastindex >= 2:
                return match.group(2).strip(" .,-").lower()
            return match.group(1).strip(" .,-").lower()

    subject_match = re.search(r"application(?: received)?[:\-\s]+(?:to\s+)?([A-Z][A-Za-z0-9&.\- ]{2,60})", email.subject, flags=re.IGNORECASE)
    if subject_match:
        return subject_match.group(1).strip(" .,-").lower()

    return ""


def _extract_role(text: str) -> str:
    clean = _normalize_text(text)
    patterns = [
        r"JR\d+\s+([^\(\n]+?)\s+\(CAND",
        r"thank you for applying for the (.+?) position",
        r"thank you for taking the time to complete your application for our (.+?) role",
        r"thank you for taking the time to complete your application for our (.+?) position",
        r"your application to [^.]*? for the (.+?) position",
        r"application received[:\s]+(.+?)\s+position",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.IGNORECASE | re.DOTALL)
        if match:
            role = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if role:
                return role
    return ""


def _extract_application_link(text: str) -> str:
    matches = list(re.finditer(r"https?://[^\s)>\"']+", text))
    if not matches:
        return ""

    lower_text = text.lower()
    for match in matches:
        url = match.group(0).rstrip(".,)")
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 120)
        context = lower_text[start:end]
        if any(word in url.lower() for word in ["userhome", "careers", "jobs", "talent", "open roles"]):
            continue
        if any(
            phrase in context
            for phrase in [
                "apply now",
                "apply here",
                "submit application",
                "view application",
                "complete your application",
                "application link",
            ]
        ):
            return url
    return ""


def _extract_status(lower_text: str) -> str:
    if any(phrase in lower_text for phrase in ["thank you for applying", "application received", "received your application", "currently in the process", "reviewing applications", "we have received your application"]):
        return "Pending"
    if any(phrase in lower_text for phrase in ["selected to move forward", "interview", "assessment", "shortlist"]):
        return "Pending"
    if any(phrase in lower_text for phrase in ["offer", "offer letter", "offer released", "offer extended"]):
        return "Offer"
    if any(phrase in lower_text for phrase in ["rejected", "not selected", "unsuccessful", "declined"]):
        return "Rejected"
    return "Pending" if "application" in lower_text else ""


def _extract_job_type(lower_text: str) -> str:
    if any(key in lower_text for key in ["internship", "intern"]):
        return "Internship"
    if any(key in lower_text for key in ["full time", "full-time", "ft", "permanent", "regular"]):
        return "Full Time"
    return "Full Time" if "application" in lower_text else ""


def _normalize_text(text: str) -> str:
    return (
        text.replace("\u200e", " ")
        .replace("\u200f", " ")
        .replace("\ufeff", " ")
        .replace("\xa0", " ")
    )
