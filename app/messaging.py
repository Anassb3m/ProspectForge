"""Deterministic, editable outreach drafts for qualified prospects.

Drafts are deliberately generated without an AI/API dependency. They use only
facts already stored on the prospect and never turn an award or sector into a
claim about the company's internal tools. The UI must call
``drafts_for_prospect`` so qualification remains the unlock gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MessageDrafts:
    linkedin_connection_note: str
    linkedin_first_message: str
    email_subject: str
    email_body: str


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _first_name(full_name: str | None) -> str | None:
    name = _clean(full_name)
    if not name:
        return None
    parts = [part.strip(".,") for part in name.split() if part.strip(".,")]
    while parts and parts[0].lower() in {"m", "m.", "mme", "mme.", "mr", "mrs"}:
        parts.pop(0)
    return parts[0] if parts else None


def _truncate(text: str, limit: int) -> str:
    text = _clean(text)
    if len(text) <= limit:
        return text
    shortened = text[: max(1, limit - 1)].rsplit(" ", 1)[0].rstrip(" ,;:.-")
    return f"{shortened}…"


def _award_object(prospect: Any) -> str | None:
    for award in getattr(prospect, "award_history", None) or []:
        if not isinstance(award, dict):
            continue
        object_text = _clean(award.get("objet") or award.get("object") or award.get("title"))
        if object_text:
            return _truncate(object_text, 120)
    return None


def _greeting(first_name: str | None) -> str:
    return f"Bonjour {first_name}," if first_name else "Bonjour,"


def _observed_context(prospect: Any) -> tuple[str, str]:
    """Return a factual short context and a fuller sentence for drafts."""
    award = _award_object(prospect)
    company = _clean(getattr(prospect, "company_name", None)) or "votre entreprise"
    sector = _clean(getattr(prospect, "sector", None)) or "services techniques"
    if award:
        return (
            f"votre récent marché « {award} »",
            f"J’ai repéré le récent marché « {award} » attribué à {company}.",
        )
    return (
        f"l’activité de {company} dans le secteur {sector}",
        f"Je me suis intéressé à l’activité de {company} dans le secteur {sector}.",
    )


def message_drafts_are_unlocked(prospect: Any) -> bool:
    """Only a completed human accept may unlock message drafting."""
    return bool(
        getattr(prospect, "manual_review_state", None) == "accepted"
        and getattr(prospect, "qualification_decision", None) == "accept"
        and not getattr(prospect, "opted_out", False)
        and not getattr(prospect, "anonymized", False)
        and not getattr(prospect, "is_suppressed", False)
    )


def build_message_drafts(prospect: Any) -> MessageDrafts:
    """Build four editable French drafts from known prospect facts."""
    first_name = _first_name(getattr(prospect, "decision_maker_name", None))
    greeting = _greeting(first_name)
    short_context, observed_sentence = _observed_context(prospect)
    company = _clean(getattr(prospect, "company_name", None)) or "votre entreprise"
    sector = _clean(getattr(prospect, "sector", None)) or "services techniques"
    offer = _clean(getattr(prospect, "recommended_offer", None)) or (
        "un système de pilotage des devis, interventions, techniciens et rapports"
    )

    connection_note = _truncate(
        (
            f"{greeting} j’ai vu {short_context}. "
            f"J’aide les PME de {sector} à mieux piloter leurs opérations terrain. "
            "Ouvert à un court échange ?"
        ),
        300,
    )

    linkedin_first_message = (
        f"{greeting}\n\n"
        f"{observed_sentence} Je ne présume pas de vos outils actuels : je cherche simplement "
        "à comprendre si la coordination des devis, interventions et rapports est un sujet "
        "chez vous.\n\n"
        f"Je conçois {offer}. Si le sujet est pertinent, je peux vous montrer en 15 minutes "
        "une approche concrète, puis vous me dites franchement si elle mérite d’aller plus loin.\n\n"
        "— [Votre prénom]"
    )

    email_subject = _truncate(f"{company} — pilotage des opérations terrain", 120)
    email_body = (
        f"{greeting}\n\n"
        f"{observed_sentence}\n\n"
        "Ce signal ne dit rien, à lui seul, de vos outils actuels. Je voulais donc vous poser "
        "une question simple : la coordination des devis, interventions, techniciens et rapports "
        "fait-elle partie des sujets que vous cherchez à fluidifier ?\n\n"
        f"Je conçois {offer}, configuré autour du fonctionnement réel de l’entreprise. "
        "Je peux vous présenter une approche concrète en 15 minutes, sans engagement.\n\n"
        "Si ce sujet n’est pas pertinent, dites-le-moi simplement et je ne vous relancerai pas.\n\n"
        "Bien cordialement,\n"
        "[Votre prénom]\n"
        "[Votre société]"
    )

    return MessageDrafts(
        linkedin_connection_note=connection_note,
        linkedin_first_message=linkedin_first_message,
        email_subject=email_subject,
        email_body=email_body,
    )


def drafts_for_prospect(prospect: Any) -> MessageDrafts | None:
    """Return drafts only when the human qualification gate is complete."""
    if not message_drafts_are_unlocked(prospect):
        return None
    return build_message_drafts(prospect)
