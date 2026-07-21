"""Multi-Jurisdiction B2B Compliance Policy Evaluator."""

from dataclasses import dataclass


@dataclass
class CompliancePolicyResult:
    policy_code: str
    jurisdiction: str
    decision: str  # allow_send, deny, needs_review
    reasons: list[str]
    opt_out_required: bool
    sender_disclosure_required: bool


def evaluate_compliance_policy(
    jurisdiction: str,
    legal_form: str | None = None,
    contact_email: str | None = None,
    is_suppressed: bool = False,
) -> CompliancePolicyResult:
    """Evaluate compliance policy for outreach to candidate prospect."""
    reasons: list[str] = []

    if is_suppressed:
        return CompliancePolicyResult(
            policy_code=f"{jurisdiction.lower()}_b2b_policy",
            jurisdiction=jurisdiction,
            decision="deny",
            reasons=["Target email or company domain is present in suppression list."],
            opt_out_required=True,
            sender_disclosure_required=True,
        )

    if jurisdiction == "GB":
        # UK PECR 2003 Rules for Corporate Subscribers (Ltd, LLP, PLC)
        if legal_form and legal_form.lower() in ("sole_trader", "unincorporated_partnership"):
            reasons.append("Sole trader / individual subscriber requires prior opt-in consent under PECR.")
            return CompliancePolicyResult(
                policy_code="uk_b2b_email_corporate_v1",
                jurisdiction="GB",
                decision="deny",
                reasons=reasons,
                opt_out_required=True,
                sender_disclosure_required=True,
            )

        reasons.append("PECR B2B Corporate Subscriber exemption applies to Ltd/LLP/PLC.")
        return CompliancePolicyResult(
            policy_code="uk_b2b_email_corporate_v1",
            jurisdiction="GB",
            decision="allow_send",
            reasons=reasons,
            opt_out_required=True,
            sender_disclosure_required=True,
        )

    elif jurisdiction == "FR":
        # French CNIL B2B Rules
        if legal_form and legal_form.lower() in ("auto_entrepreneur", "ei"):
            reasons.append("Entreprise individuelle requires explicit opt-in.")
            return CompliancePolicyResult(
                policy_code="fr_b2b_email_optout_v1",
                jurisdiction="FR",
                decision="deny",
                reasons=reasons,
                opt_out_required=True,
                sender_disclosure_required=True,
            )

        reasons.append("CNIL B2B professional relevance rule satisfied for corporate entity.")
        return CompliancePolicyResult(
            policy_code="fr_b2b_email_optout_v1",
            jurisdiction="FR",
            decision="allow_send",
            reasons=reasons,
            opt_out_required=True,
            sender_disclosure_required=True,
        )

    return CompliancePolicyResult(
        policy_code="generic_b2b_policy",
        jurisdiction=jurisdiction,
        decision="needs_review",
        reasons=["Unknown jurisdiction policy requirement."],
        opt_out_required=True,
        sender_disclosure_required=True,
    )
