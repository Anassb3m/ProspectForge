"""Field-Team and Operational-Complexity Estimator."""

from dataclasses import dataclass


@dataclass
class TechnicianEstimate:
    lower_bound: int
    upper_bound: int
    point_estimate: int | None
    method_code: str
    confidence: str  # low, medium, high, exact
    assumptions: list[str]


def estimate_field_technicians(
    workforce_band: str | None = None,
    evidence_codes: list[str] | None = None,
    team_members_found: int = 0,
) -> TechnicianEstimate:
    """Calculate bounded field technician estimate from registry prior and website evidence."""
    evidence_codes = evidence_codes or []
    assumptions: list[str] = []

    # 1. Registry employee band prior
    base_low, base_high = 10, 50
    if workforce_band:
        if "1-10" in workforce_band or "1-5" in workforce_band:
            base_low, base_high = 5, 12
            assumptions.append("Registry workforce band indicates small team")
        elif "11-50" in workforce_band or "10-49" in workforce_band:
            base_low, base_high = 12, 45
            assumptions.append("Registry workforce band indicates medium field fleet")
        elif "51-200" in workforce_band or "50-199" in workforce_band:
            base_low, base_high = 35, 120
            assumptions.append("Registry workforce band indicates substantial operations")

    # 2. Adjust for multi-branch or regional operations evidence
    if "OPERATIONS.COMPLEXITY.MULTI_BRANCH" in evidence_codes:
        base_low = max(base_low, 15)
        assumptions.append("Multi-branch evidence increases minimum technician baseline")

    if team_members_found > 0:
        assumptions.append(f"Identified {team_members_found} specific team/technical profiles")
        point = max(team_members_found, base_low + 5)
    else:
        point = (base_low + base_high) // 2

    return TechnicianEstimate(
        lower_bound=base_low,
        upper_bound=base_high,
        point_estimate=point,
        method_code="composite_registry_evidence_v1",
        confidence="medium",
        assumptions=assumptions,
    )
