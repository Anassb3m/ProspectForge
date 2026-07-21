"""Outreach Campaign and Touch Sequence State Machine."""

from dataclasses import dataclass


@dataclass
class CampaignTouchState:
    touch_id: str
    status: str  # scheduled, approved, submitted, sent, delivered, bounced, stopped
    stop_reason: str | None


def evaluate_campaign_stop_rules(
    has_replied: bool = False,
    is_bounced: bool = False,
    is_suppressed: bool = False,
    opt_out_received: bool = False,
) -> tuple[bool, str | None]:
    """Evaluate automatic campaign sequence stop conditions."""
    if has_replied:
        return True, "prospect_replied"
    if is_bounced:
        return True, "email_bounced"
    if opt_out_received:
        return True, "opt_out_requested"
    if is_suppressed:
        return True, "suppression_entry_matched"
    return False, None
