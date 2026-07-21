"""Hard-Gated Evidence-Backed Scoring Engine."""

from dataclasses import dataclass


@dataclass
class HardGateResult:
    passed: bool
    rejection_reasons: list[str]


@dataclass
class OpportunityScoreSnapshot:
    total_score: float
    hard_gates_passed: bool
    breakdown: dict[str, float]
    rejection_reasons: list[str]


def evaluate_hard_gates(
    entity_status: str = "active",
    legal_form: str | None = None,
    domain_verification_state: str = "verified_primary",
    compliance_decision: str = "allow_send",
) -> HardGateResult:
    """Evaluate non-negotiable hard qualification gates."""
    rejections: list[str] = []

    if entity_status.lower() not in ("active", "incorporated"):
        rejections.append(f"Hard Gate Failed: Legal entity status is '{entity_status}' (must be active).")

    if legal_form and legal_form.lower() in ("sole_trader", "auto_entrepreneur"):
        rejections.append(f"Hard Gate Failed: Legal form '{legal_form}' excluded in pilot.")

    if domain_verification_state == "rejected":
        rejections.append("Hard Gate Failed: Official company domain was rejected.")

    if compliance_decision == "deny":
        rejections.append("Hard Gate Failed: Compliance policy denied outreach.")

    return HardGateResult(passed=len(rejections) == 0, rejection_reasons=rejections)


def calculate_opportunity_score(
    evidence_codes: list[str],
    has_buyer_identified: bool = True,
    has_contact_path: bool = True,
    technician_count_in_range: bool = True,
    hard_gate_result: HardGateResult | None = None,
) -> OpportunityScoreSnapshot:
    """Compute score snapshot with evidence item component weights."""
    breakdown: dict[str, float] = {}

    # Base fit component
    score = 40.0
    breakdown["base_icp_fit"] = 40.0

    # Operational complexity signals
    if "OPERATIONS.COMPLEXITY.MULTI_BRANCH" in evidence_codes:
        score += 15.0
        breakdown["multi_branch_evidence"] = 15.0
    if "OPERATIONS.COMPLEXITY.RECURRING_CONTRACTS" in evidence_codes:
        score += 15.0
        breakdown["recurring_contracts_evidence"] = 15.0
    if "OPERATIONS.COMPLEXITY.ON_CALL_247" in evidence_codes:
        score += 10.0
        breakdown["on_call_247_evidence"] = 10.0

    # Buyer & Contact readiness
    if has_buyer_identified:
        score += 10.0
        breakdown["buyer_identified"] = 10.0
    if has_contact_path:
        score += 10.0
        breakdown["contact_path_verified"] = 10.0

    total = min(score, 100.0)
    passed = hard_gate_result.passed if hard_gate_result else True

    return OpportunityScoreSnapshot(
        total_score=total if passed else 0.0,
        hard_gates_passed=passed,
        breakdown=breakdown,
        rejection_reasons=hard_gate_result.rejection_reasons if hard_gate_result else [],
    )
