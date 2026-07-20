"""Typed adapter boundary and independent contact-confidence dimensions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol


class PublicationState(StrEnum):
    PUBLISHED_PERSONAL = "published_personal"
    PUBLISHED_ROLE = "published_role"
    PUBLISHED_GENERIC = "published_generic"
    NOT_PUBLISHED = "not_published"
    UNKNOWN = "unknown"


class DeliverabilityState(StrEnum):
    DELIVERABLE = "deliverable"
    CATCH_ALL = "catch_all"
    RISKY = "risky"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"
    UNCHECKED = "unchecked"
    ERROR = "error"


class PersonMatchState(StrEnum):
    EXACT_PERSON_PUBLISHED = "exact_person_published"
    EXACT_PERSON_PATTERN_CONFIRMED = "exact_person_pattern_confirmed"
    STRONG_PERSON_MATCH = "strong_person_match"
    ROLE_MAILBOX = "role_mailbox"
    GENERIC_COMPANY_MAILBOX = "generic_company_mailbox"
    PATTERN_INFERRED = "pattern_inferred"
    NAME_ONLY_GUESS = "name_only_guess"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class UtilityState(StrEnum):
    USABLE_PERSONAL = "usable_personal"
    USABLE_ROLE = "usable_role"
    USABLE_GENERIC = "usable_generic"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    VERIFICATION_REQUIRED = "verification_required"
    INVALID = "invalid"
    SUPPRESSED = "suppressed"
    STALE = "stale"
    NO_CONTACT = "no_contact"


class DomainMatchState(StrEnum):
    EXACT_LEGAL_MATCH = "exact_legal_match"
    STRONG_BRAND_MATCH = "strong_brand_match"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"


@dataclass(slots=True)
class PersonFact:
    full_name: str
    job_title: str | None = None
    role_category: str = "unknown"
    buyer_role_score: int = 0
    company_match_state: str = "unknown"
    identity_confidence: int = 0
    linkedin_url: str | None = None
    source_url: str | None = None
    source_adapter: str = "official_website"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContactPointFact:
    kind: str
    value: str
    publication_state: str = PublicationState.UNKNOWN
    person_match_state: str = PersonMatchState.UNKNOWN
    deliverability_state: str = DeliverabilityState.UNCHECKED
    source_class: str = "company_website"
    source_url: str | None = None
    person_name: str | None = None
    department: str | None = None
    confidence: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceFact:
    evidence_type: str
    source_adapter: str
    source_url: str | None
    excerpt: str | None = None
    page_title: str | None = None
    confidence: int = 50
    content_hash: str | None = None
    person_name: str | None = None
    contact_value: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContactDiscoveryContext:
    prospect_id: int
    company_name: str
    website: str | None
    siren: str | None = None
    company_size: str | None = None
    market_play_code: str | None = None
    started_at: datetime | None = None


@dataclass(slots=True)
class ContactSourceResult:
    people: list[PersonFact] = field(default_factory=list)
    contact_points: list[ContactPointFact] = field(default_factory=list)
    evidence: list[EvidenceFact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    source_timestamps: dict[str, str] = field(default_factory=dict)


class ContactSourceAdapter(Protocol):
    name: str

    async def discover(self, context: ContactDiscoveryContext) -> ContactSourceResult: ...
