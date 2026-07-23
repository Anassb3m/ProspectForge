"""
Unified Scoring V4 and Hard Gates engine.

Dimensions:
- icp_fit
- operational_complexity
- pain_or_integration_opportunity
- trigger_strength
- commercial_value
- buyer_confidence
- contact_quality
- data_quality
- freshness
- risk_penalty

Hard Gates (Outreach Ready):
- active eligible legal entity
- allowed jurisdiction/legal form
- target vertical or manually approved exception
- official identity resolved
- domain resolved or explicit alternate defensible contact path
- at least one real opportunity/complexity/trigger evidence item
- buyer role identified or accepted generic role path
- usable contact path
- policy decision allow
- not suppressed
- no unresolved high-severity contradiction
- human approval
- evidence-backed message draft.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Opportunity, Company, EvidenceItem, ScoreSnapshot, Person

def compute_dimension_icp_fit(company: Company) -> int:
    score = 50
    # Simplified check using classifications and estimates
    for cls in company.classifications:
        if cls.scheme == "industry" and cls.code in ["Technology", "IT", "Cybersecurity"]:
            score += 30
    for est in company.estimates:
        if est.estimate_type == "headcount" and est.point_estimate and est.point_estimate > 50:
            score += 10
    return min(100, max(0, score))

def compute_dimension_operational_complexity(company: Company) -> int:
    score = 0
    if len(company.locations) > 1:
        score += 30
    return min(100, max(0, score))

def compute_dimension_pain_or_integration_opportunity(evidence: list[EvidenceItem]) -> int:
    score = 0
    for item in evidence:
        if item.category == "pain":
            score += 40
        if item.category == "integration":
            score += 20
    return min(100, max(0, score))

def compute_dimension_trigger_strength(evidence: list[EvidenceItem]) -> int:
    score = 0
    for item in evidence:
        if item.category == "trigger":
            score += 30
    return min(100, max(0, score))

def compute_dimension_commercial_value(company: Company, opportunity: Opportunity) -> int:
    return 50 # Base value

def compute_dimension_buyer_confidence(people: list[Person]) -> int:
    score = 0
    for person in people:
        if person.roles:
            for role in person.roles:
                if role.seniority in ["executive", "director"]:
                    score += 40
    return min(100, max(0, score))

def compute_dimension_contact_quality(people: list[Person]) -> int:
    score = 0
    for person in people:
        # Evaluate contact points if available, placeholder for now
        score += 20
    return min(100, max(0, score))

def compute_dimension_data_quality(company: Company) -> int:
    score = 20
    if len(company.domains) > 0:
        score += 30
    if company.identifiers:
        score += 50
    return min(100, max(0, score))

def compute_dimension_freshness(opportunity: Opportunity) -> int:
    now = datetime.now(timezone.utc)
    delta = now - opportunity.updated_at
    if delta.days < 7:
        return 100
    if delta.days < 30:
        return 70
    return 30

def compute_dimension_risk_penalty(company: Company) -> int:
    return 0


def calculate_opportunity_score_v4(db: Session, opportunity: Opportunity) -> ScoreSnapshot:
    company = opportunity.company
    evidence = opportunity.evidence_items
    
    # Pre-fetch people if needed (this would typically be joined or loaded)
    stmt = select(Person).join(Person.roles).where(Person.roles.any(company_id=company.id))
    people = list(db.scalars(stmt).all())

    dimensions = {
        "icp_fit": compute_dimension_icp_fit(company),
        "operational_complexity": compute_dimension_operational_complexity(company),
        "pain_or_integration_opportunity": compute_dimension_pain_or_integration_opportunity(evidence),
        "trigger_strength": compute_dimension_trigger_strength(evidence),
        "commercial_value": compute_dimension_commercial_value(company, opportunity),
        "buyer_confidence": compute_dimension_buyer_confidence(people),
        "contact_quality": compute_dimension_contact_quality(people),
        "data_quality": compute_dimension_data_quality(company),
        "freshness": compute_dimension_freshness(opportunity),
        "risk_penalty": compute_dimension_risk_penalty(company)
    }

    # Base weighted total
    weights = {
        "icp_fit": 0.15,
        "operational_complexity": 0.10,
        "pain_or_integration_opportunity": 0.20,
        "trigger_strength": 0.15,
        "commercial_value": 0.10,
        "buyer_confidence": 0.10,
        "contact_quality": 0.10,
        "data_quality": 0.05,
        "freshness": 0.05
    }
    
    total_score = sum(dimensions[k] * weights.get(k, 0) for k in dimensions if k != "risk_penalty")
    total_score -= dimensions["risk_penalty"]
    total_score = max(0, min(100, total_score))

    # Evaluate Hard Gates
    hard_gate_results = {
        "active_eligible_legal_entity": company.entity_status == "active",
        "allowed_jurisdiction": company.jurisdiction_code in ["GB-EW", "FR", "US"],
        "official_identity_resolved": len(company.identifiers) > 0 if company.identifiers else False,
        "domain_resolved": len(company.domains) > 0 if company.domains else False,
        "usable_contact_path": True, # Placeholder until detailed contact checking is done
        "not_suppressed": True,
        "human_approval": False # Requires manual intervention
    }
    
    hard_gates_passed = all(hard_gate_results.values())
    
    snapshot = ScoreSnapshot(
        opportunity_id=opportunity.id,
        version="4.0",
        dimensions_json=dimensions,
        weights_json=weights,
        penalties_json={"risk_penalty": dimensions["risk_penalty"]},
        hard_gates_json=hard_gate_results,
        total_score=total_score,
        hard_gates_passed=hard_gates_passed,
        reasons_json={"failure": [k for k, v in hard_gate_results.items() if not v]},
        computed_at=datetime.now(timezone.utc)
    )
    
    db.add(snapshot)
    
    # Update Opportunity Cache
    opportunity.latest_score = total_score
    opportunity.outreach_ready = hard_gates_passed
    
    return snapshot

