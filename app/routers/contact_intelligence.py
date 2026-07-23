"""Authenticated operator actions for source-backed contact dossiers."""

from __future__ import annotations

import hashlib
from typing import Annotated, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import get_current_user
from app.contact_intelligence.extractors import normalize_email, normalize_phone
from app.contact_intelligence.safety import UnsafeURLError, normalize_http_url
from app.contact_intelligence.service import (
    DiscoveryAlreadyRunning,
    DiscoveryNotEligible,
    project_primary_contact_to_prospect,
    record_manual_review,
    run_contact_discovery,
)
from app.contact_intelligence.confidence import derive_utility, is_usable
from app.database import get_db
from app.models import ContactEvidence, ContactManualReview, ContactPoint, User

router = APIRouter(tags=["contact-intelligence"])


@router.post("/prospects/{prospect_id}/contact-intelligence/run")
async def form_run_contact_discovery(
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    force: Annotated[Optional[str], Form()] = None,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    try:
        await run_contact_discovery(db, prospect, actor=user.email, force=bool(force))
    except DiscoveryAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DiscoveryNotEligible as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RedirectResponse(url=f"/prospects/{prospect_id}#contact-intelligence", status_code=303)


@router.post("/prospects/{prospect_id}/contact-intelligence/review")
async def form_review_contact(
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    decision: Annotated[str, Form()],
    person_id: Annotated[Optional[int], Form()] = None,
    contact_point_id: Annotated[Optional[int], Form()] = None,
    reason: Annotated[Optional[str], Form()] = None,
    evidence_url: Annotated[Optional[str], Form()] = None,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if bool(person_id) == bool(contact_point_id):
        raise HTTPException(status_code=400, detail="Choose exactly one person or contact point")
    try:
        await record_manual_review(
            db, prospect, reviewer=user.email, decision=decision,
            person_id=person_id, contact_point_id=contact_point_id,
            reason=reason, evidence_url=evidence_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/prospects/{prospect_id}#contact-intelligence", status_code=303)


@router.post("/prospects/{prospect_id}/contact-intelligence/add")
async def form_add_manual_contact(
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    kind: Annotated[str, Form()],
    value: Annotated[str, Form()],
    source_url: Annotated[str, Form()],
    publication_state: Annotated[str, Form()] = "unknown",
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    allowed_kinds = {"email", "phone", "contact_form", "linkedin", "generic_contact_page"}
    if kind not in allowed_kinds:
        raise HTTPException(status_code=400, detail="Unsupported contact type")
    if publication_state not in {
        "published_personal", "published_role", "published_generic", "not_published", "unknown"
    }:
        raise HTTPException(status_code=400, detail="Invalid publication state")
    try:
        normalized_source = normalize_http_url(source_url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if kind == "email":
        normalized = normalize_email(value)
    elif kind == "phone":
        normalized = normalize_phone(value)
    else:
        try:
            normalized = normalize_http_url(value)
        except UnsafeURLError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid contact value")
    if kind == "linkedin" and not (urlsplit(normalized).hostname or "").endswith("linkedin.com"):
        raise HTTPException(status_code=400, detail="LinkedIn URL must use linkedin.com")
    person_match = {
        "published_personal": "strong_person_match",
        "published_role": "role_mailbox",
        "published_generic": "generic_company_mailbox",
    }.get(publication_state, "unknown")
    utility = derive_utility(
        kind=kind, publication_state=publication_state, deliverability_state="unchecked",
        person_match_state=person_match, manually_confirmed=True,
    )
    point = await db.scalar(
        select(ContactPoint).where(
            and_(
                ContactPoint.prospect_id == prospect.id,
                ContactPoint.kind == kind,
                ContactPoint.value_normalized == normalized,
            )
        )
    )
    previous_state = point.utility_state if point else "not_recorded"
    if point is None:
        point = ContactPoint(
            prospect_id=prospect.id, kind=kind, value_normalized=normalized,
            value_display=normalized,
            domain=(
                urlsplit(normalized).hostname
                if kind != "email"
                else normalized.rsplit("@", 1)[1]
            ),
            source_class="manual_operator", publication_state=publication_state,
            person_match_state=person_match, deliverability_state="unchecked",
            verification_state="unchecked", utility_state=utility,
            confidence_score=100, manually_confirmed=True, is_usable=is_usable(utility),
            requires_manual_review=False,
        )
        db.add(point)
        await db.flush()
    else:
        point.value_display = normalized
        point.source_class = "manual_operator"
        point.publication_state = publication_state
        point.person_match_state = person_match
        point.utility_state = utility
        point.confidence_score = 100
        point.manually_confirmed = True
        point.rejection_reason = None
        point.is_suppressed = False
        point.is_usable = is_usable(utility)
        point.requires_manual_review = False
    fingerprint = hashlib.sha256(
        f"{prospect.id}|manual_operator|{normalized_source}|{kind}|{normalized}".encode()
    ).hexdigest()
    existing_evidence = await db.scalar(
        select(ContactEvidence.id).where(ContactEvidence.fingerprint == fingerprint)
    )
    if existing_evidence is None:
        db.add(
            ContactEvidence(
                prospect_id=prospect.id, contact_point_id=point.id, fingerprint=fingerprint,
                source_adapter="manual_operator", source_url=normalized_source,
                canonical_url=normalized_source, source_domain=urlsplit(normalized_source).hostname,
                evidence_type=f"manual_{kind}", excerpt=f"Operator-confirmed {kind}",
                confidence=100, raw_metadata={"entered_manually": True},
            )
        )
    db.add(
        ContactManualReview(
            contact_point_id=point.id,
            reviewer=user.email,
            decision="confirm",
            previous_state=previous_state,
            new_state=utility,
            reason="operator_added_source_backed_contact",
            evidence_url=normalized_source,
        )
    )
    await db.flush()
    await project_primary_contact_to_prospect(db, prospect)
    return RedirectResponse(url=f"/prospects/{prospect_id}#contact-intelligence", status_code=303)
