"""Evidence-bound French field-operations scoring and hard readiness gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial import is_suppressed
from app.models import (
    CompanyClassification,
    CompanyDomain,
    CompanyIdentifier,
    CompanyLocation,
    ComplianceDecision,
    ContactEvidence,
    ContactPerson,
    ContactPoint,
    EvidenceItem,
    MarketPlayVersion,
    Opportunity,
    PersonRole,
    Prospect,
    QualificationReview,
    ScoreSnapshot,
)
from app.plays import require_play

PROFILE_CODE = "field_ops_fr_v2"
PROFILE_VERSION = "2.0.0"
CALCULATOR_VERSION = "5.0.0"
WEIGHTS = {
    "icp_fit": 25,
    "operational_complexity": 20,
    "trigger_timing": 15,
    "buyer_contact_quality": 15,
    "evidence_data_quality": 15,
    "commercial_relevance": 10,
}
BUYER_ROLES = {
    "owner",
    "executive",
    "operations",
    "service",
    "maintenance",
    "technical",
    "exploitation",
    "administration_finance",
    "planning_methods",
    "gerant_president",
    "directeur_general",
    "directeur_operations",
    "responsable_exploitation",
    "responsable_sav",
    "directeur_technique",
    "responsable_maintenance",
}
VERIFIED_DOMAIN_STATES = {"verified", "official", "manually_confirmed"}
OPERATIONAL_CATEGORIES = {
    "structural_fit",
    "operations",
    "complexity",
    "pain",
    "integration",
}
TRIGGER_CATEGORIES = {"trigger", "timing"}
PRIMARY_SOURCE_TYPES = {
    "official_registry",
    "registry",
    "decp",
    "official_website",
    "public_contract",
    "manual_verified",
}


def _current(item: EvidenceItem, now: datetime) -> bool:
    if not item.is_active or item.contradiction_status not in {"none", "resolved"}:
        return False
    expires = item.expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            return False
    return True


def _ratio(points: float, cap: int) -> float:
    return round(max(0.0, min(float(cap), points)), 2)


def evaluate_field_ops_profile(
    *,
    company_status: str,
    jurisdiction: str,
    identity_state: str,
    identifier_verified: bool,
    relevant_classification: bool,
    classification_override: bool,
    verified_domain: bool,
    evidence: list[EvidenceItem],
    buyer_role: bool,
    usable_contact: bool,
    contact_provenance: bool,
    suppressed: bool,
    compliance_allowed: bool,
    human_approved: bool,
    location_count: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pure, table-testable score/gate evaluation; scores never override gates."""
    now = now or datetime.now(timezone.utc)
    current = [item for item in evidence if _current(item, now)]
    operational = [item for item in current if item.category in OPERATIONAL_CATEGORIES]
    triggers = [item for item in current if item.category in TRIGGER_CATEGORIES]
    contradictions = [
        item for item in evidence if item.contradiction_status not in {"none", "resolved"}
    ]
    severe_identity_clear = identity_state != "severe_contradiction"

    icp = 0.0
    icp += 6 if company_status == "active" else 0
    icp += 5 if jurisdiction == "FR" else 0
    icp += 8 if relevant_classification or classification_override else 0
    icp += 6 if identifier_verified else 2 if identity_state == "provisional_review" else 0

    operational_score = min(14.0, sum(item.strength * 7 for item in operational))
    if location_count > 1:
        operational_score += 4
    if len(operational) >= 2:
        operational_score += 2

    trigger_score = min(15.0, sum(item.strength * 7.5 for item in triggers))
    buyer_score = (6 if buyer_role else 0) + (5 if usable_contact else 0)
    buyer_score += 4 if contact_provenance else 0

    evidence_score = min(7.0, len(current) * 2.0)
    evidence_score += min(
        5.0,
        sum(1.25 for item in current if item.source_type in PRIMARY_SOURCE_TYPES),
    )
    evidence_score += 3 if any(item.verification_state == "manually_confirmed" for item in current) else 0

    commercial_score = 0.0
    if operational:
        commercial_score += 5
    if triggers:
        commercial_score += 3
    if buyer_role or usable_contact:
        commercial_score += 2

    risk_penalty = min(25.0, len(contradictions) * 7.5)
    if not severe_identity_clear:
        risk_penalty = max(risk_penalty, 25.0)

    dimensions = {
        "icp_fit": _ratio(icp, WEIGHTS["icp_fit"]),
        "operational_complexity": _ratio(
            operational_score, WEIGHTS["operational_complexity"]
        ),
        "trigger_timing": _ratio(trigger_score, WEIGHTS["trigger_timing"]),
        "buyer_contact_quality": _ratio(
            buyer_score, WEIGHTS["buyer_contact_quality"]
        ),
        "evidence_data_quality": _ratio(
            evidence_score, WEIGHTS["evidence_data_quality"]
        ),
        "commercial_relevance": _ratio(
            commercial_score, WEIGHTS["commercial_relevance"]
        ),
    }
    total = max(0.0, min(100.0, sum(dimensions.values()) - risk_penalty))
    gates = {
        "active_legal_entity": company_status == "active",
        "correct_jurisdiction": jurisdiction == "FR",
        "relevant_classification": relevant_classification or classification_override,
        "official_identifier_or_provisional_review": (
            identifier_verified or identity_state == "provisional_review"
        ),
        "no_severe_identity_contradiction": severe_identity_clear,
        "verified_official_domain": verified_domain,
        "minimum_operational_evidence": bool(operational),
        "appropriate_buyer_or_role_route": buyer_role,
        "contact_path_usable": usable_contact,
        "contact_provenance_recorded": contact_provenance,
        "suppression_check_passed": not suppressed,
        "compliance_professional_relevance": compliance_allowed,
        "human_approval": human_approved,
    }
    all_gates = all(gates.values())
    if suppressed:
        readiness = "SUPPRESSED"
    elif not gates["active_legal_entity"] or not gates["correct_jurisdiction"]:
        readiness = "ICP_REJECTED"
    elif not gates["relevant_classification"]:
        readiness = "ICP_REJECTED"
    elif not gates["official_identifier_or_provisional_review"] or not severe_identity_clear:
        readiness = "IDENTITY_REVIEW"
    elif not operational:
        readiness = "EVIDENCE_INSUFFICIENT"
    elif not verified_domain or not usable_contact:
        readiness = "CONTACT_RESEARCH_ELIGIBLE"
    elif not contact_provenance or not buyer_role or not compliance_allowed or not human_approved:
        readiness = "HUMAN_REVIEW_REQUIRED"
    elif all_gates:
        readiness = "CONTACT_READY"
    else:
        readiness = "SCORED"
    return {
        "dimensions": dimensions,
        "risk_penalty": risk_penalty,
        "total_score": round(total, 2),
        "hard_gates": gates,
        "hard_gates_passed": all_gates,
        "readiness_state": readiness,
        "evidence_refs": [item.id for item in current if item.id],
    }


async def calculate_opportunity_score_v4(
    db: AsyncSession, opportunity: Opportunity
) -> ScoreSnapshot:
    """Calculate and persist an idempotent, fully explainable score snapshot."""
    company = opportunity.company
    play_version = await db.get(MarketPlayVersion, opportunity.play_version_id)
    if play_version is None:
        raise ValueError("Opportunity has no market-play version")
    play = require_play(play_version.play_code)
    evidence = list(
        (
            await db.scalars(
                select(EvidenceItem).where(
                    EvidenceItem.opportunity_id == opportunity.id
                )
            )
        ).all()
    )
    identifiers = list(
        (
            await db.scalars(
                select(CompanyIdentifier).where(
                    CompanyIdentifier.company_id == company.id
                )
            )
        ).all()
    )
    domains = list(
        (
            await db.scalars(
                select(CompanyDomain).where(CompanyDomain.company_id == company.id)
            )
        ).all()
    )
    classifications = list(
        (
            await db.scalars(
                select(CompanyClassification).where(
                    CompanyClassification.company_id == company.id
                )
            )
        ).all()
    )
    location_count = len(
        (
            await db.scalars(
                select(CompanyLocation.id).where(
                    CompanyLocation.company_id == company.id
                )
            )
        ).all()
    )
    canonical_roles = list(
        (
            await db.scalars(
                select(PersonRole).where(
                    PersonRole.company_id == company.id,
                    PersonRole.is_current.is_(True),
                )
            )
        ).all()
    )
    prospect = await db.scalar(
        select(Prospect).where(Prospect.opportunity_id == opportunity.id)
    )
    contact_people: list[ContactPerson] = []
    contact_points: list[ContactPoint] = []
    contact_evidence_ids: set[int] = set()
    review = None
    suppressed = False
    if prospect is not None:
        contact_people = list(
            (
                await db.scalars(
                    select(ContactPerson).where(
                        ContactPerson.prospect_id == prospect.id,
                        ContactPerson.is_active.is_(True),
                    )
                )
            ).all()
        )
        contact_points = list(
            (
                await db.scalars(
                    select(ContactPoint).where(ContactPoint.prospect_id == prospect.id)
                )
            ).all()
        )
        point_ids = [point.id for point in contact_points if point.id is not None]
        if point_ids:
            contact_evidence_ids = set(
                (
                    await db.scalars(
                        select(ContactEvidence.contact_point_id).where(
                            ContactEvidence.contact_point_id.in_(point_ids),
                            ContactEvidence.is_active.is_(True),
                        )
                    )
                ).all()
            )
        review = await db.scalar(
            select(QualificationReview)
            .where(QualificationReview.prospect_id == prospect.id)
            .order_by(QualificationReview.created_at.desc(), QualificationReview.id.desc())
            .limit(1)
        )
        suppressed = prospect.opted_out or await is_suppressed(
            db,
            email=prospect.email,
            domain=next((domain.domain_normalized for domain in domains), None),
            siren=prospect.siren,
        )
    latest_compliance = await db.scalar(
        select(ComplianceDecision)
        .where(ComplianceDecision.opportunity_id == opportunity.id)
        .order_by(ComplianceDecision.evaluated_at.desc(), ComplianceDecision.id.desc())
        .limit(1)
    )

    allowed_codes = {
        str(item["code"]).upper().replace(".", "")
        for item in play.get("classifications", {}).get("include_codes", [])
    }
    relevant_classification = any(
        item.scheme == "FR_NAF_REV2"
        and item.code.upper().replace(".", "") in allowed_codes
        for item in classifications
    )
    identifier_verified = any(
        item.scheme in {"FR_SIREN", "FR_SIRET"} and item.verified_at is not None
        for item in identifiers
    )
    verified_domain = any(
        item.verification_state in VERIFIED_DOMAIN_STATES for item in domains
    )
    usable_points = [
        point
        for point in contact_points
        if point.is_usable
        and not point.is_suppressed
        and point.utility_state in {"usable_personal", "usable_role", "usable_generic"}
        and point.person_match_state not in {"pattern_inferred", "name_only_guess"}
    ]
    contact_provenance = any(
        point.id in contact_evidence_ids for point in usable_points
    )
    legacy_buyer = any(
        person.role_category in BUYER_ROLES
        and person.source_count > 0
        and person.company_match_state in {"exact", "strong"}
        for person in contact_people
    )
    canonical_buyer = any(
        role.normalized_role.lower() in BUYER_ROLES
        and role.confidence >= 0.7
        and bool(role.source_evidence_id)
        for role in canonical_roles
    )
    role_route = any(
        point.utility_state == "usable_role" and point.id in contact_evidence_ids
        for point in usable_points
    )
    human_approved = bool(review and review.decision == "accept")
    classification_override = bool(review and review.fit_confirmed)
    compliance_allowed = bool(
        latest_compliance and latest_compliance.decision.lower() in {"allow", "approved"}
    )

    result = evaluate_field_ops_profile(
        company_status=company.entity_status,
        jurisdiction=company.jurisdiction_code,
        identity_state=company.identity_review_state,
        identifier_verified=identifier_verified,
        relevant_classification=relevant_classification,
        classification_override=classification_override,
        verified_domain=verified_domain,
        evidence=evidence,
        buyer_role=canonical_buyer or legacy_buyer or role_route,
        usable_contact=bool(usable_points),
        contact_provenance=contact_provenance,
        suppressed=suppressed,
        compliance_allowed=compliance_allowed,
        human_approved=human_approved,
        location_count=location_count,
    )
    inputs = {
        "company_record_version": company.record_version,
        "identifier_ids": [item.id for item in identifiers],
        "domain_states": {item.id: item.verification_state for item in domains},
        "classification_ids": [item.id for item in classifications],
        "evidence": [
            {
                "id": item.id,
                "code": item.code,
                "category": item.category,
                "source_type": item.source_type,
                "confidence": item.confidence,
                "strength": item.strength,
                "is_active": item.is_active,
                "verification": item.verification_state,
                "contradiction": item.contradiction_status,
                "observed_at": (
                    item.observed_at.isoformat() if item.observed_at else None
                ),
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            }
            for item in evidence
        ],
        "contact_point_ids": [point.id for point in usable_points],
        "contact_evidence_ids": sorted(contact_evidence_ids),
        "qualification_id": review.id if review else None,
        "compliance_id": latest_compliance.id if latest_compliance else None,
        "suppressed": suppressed,
        "profile_version": PROFILE_VERSION,
        "calculator_version": CALCULATOR_VERSION,
    }
    input_revision = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, default=str).encode()
    ).hexdigest()
    existing = await db.scalar(
        select(ScoreSnapshot).where(
            ScoreSnapshot.opportunity_id == opportunity.id,
            ScoreSnapshot.profile_code == PROFILE_CODE,
            ScoreSnapshot.input_revision == input_revision,
        )
    )
    if existing is not None:
        opportunity.latest_score = existing.total_score
        opportunity.readiness_state = existing.readiness_state
        opportunity.outreach_ready = existing.hard_gates_passed
        return existing

    snapshot = ScoreSnapshot(
        opportunity_id=opportunity.id,
        version=PROFILE_VERSION,
        profile_code=PROFILE_CODE,
        input_revision=input_revision,
        calculator_version=CALCULATOR_VERSION,
        readiness_state=result["readiness_state"],
        inputs_json=inputs,
        dimensions_json=result["dimensions"],
        weights_json=WEIGHTS,
        penalties_json={"risk_contradiction_penalty": result["risk_penalty"]},
        hard_gates_json=result["hard_gates"],
        total_score=result["total_score"],
        hard_gates_passed=result["hard_gates_passed"],
        reasons_json={
            "failed_gates": [
                key for key, passed in result["hard_gates"].items() if not passed
            ]
        },
        evidence_refs_json=result["evidence_refs"],
        breakdown_json={
            "profile": PROFILE_CODE,
            "profile_version": PROFILE_VERSION,
            "calculator_version": CALCULATOR_VERSION,
        },
        computed_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    opportunity.latest_score = result["total_score"]
    opportunity.readiness_state = result["readiness_state"]
    opportunity.outreach_ready = result["hard_gates_passed"]
    return snapshot
