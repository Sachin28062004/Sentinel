from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EmailRecord:
    message_id: str
    thread_id: str
    internal_date: datetime
    from_email: str
    subject: str
    snippet: str
    body_text: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlacementExtraction:
    is_placement_related: bool
    company_name: str = ""
    date_applied: str = ""
    role: str = ""
    application_link: str = ""
    status: str = ""
    job_type: str = ""
    confidence: float = 0.0


@dataclass
class RecruiterContact:
    recruiter_name: str = ""
    recruiter_email: str = ""
    recruiter_phone: str = ""
    source_url: str = ""
    source_title: str = ""
    notes: str = ""


@dataclass
class PlacementRow:
    company_name: str
    date_applied: str
    role: str
    application_link: str
    status: str
    job_type: str
