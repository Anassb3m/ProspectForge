"""Evidence-backed Personalized Messaging Draft Engine."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MessageDraftResult:
    subject: str
    body: str
    evidence_citations: list[str]
    locale: str
    approval_status: str  # draft_pending, approved, rejected


def generate_message_draft(
    company_name: str,
    buyer_name: str | None,
    buyer_title: str | None,
    evidence_items: list[dict[str, Any]],
    locale: str = "en-GB",
) -> MessageDraftResult:
    """Generate localized draft referencing verified company evidence."""
    citations: list[str] = [ev.get("evidence_text", "") for ev in evidence_items if ev.get("evidence_text")]
    name_greeting = buyer_name if buyer_name else ("there" if locale == "en-GB" else "Bonjour")

    if locale == "en-GB":
        subject = f"Operational integration & service dispatch for {company_name}"
        body_lines = [
            f"Hi {name_greeting},",
            "",
            f"I came across {company_name} while researching UK field service & technical maintenance specialists.",
        ]

        if citations:
            body_lines.append("\nI noticed your operational setup indicates:")
            for cite in citations[:2]:
                body_lines.append(f"- {cite}")

        body_lines.extend([
            "",
            "We build custom integration layers connecting field service management tools (FSM), accounting software, and client portals — eliminating manual paperwork and sync delays between engineers and office staff.",
            "",
            "Would you be open to a brief 10-minute introduction call next week?",
            "",
            "Best regards,",
            "Anass",
        ])
        body = "\n".join(body_lines)

    else:  # fr-FR
        subject = f"Optimisation des flux d'intervention pour {company_name}"
        body_lines = [
            f"Bonjour {name_greeting},",
            "",
            "Je me permets de vous contacter suite à nos recherches sur les acteurs de la maintenance technique et du SAV en France.",
        ]

        if citations:
            body_lines.append("\nNous avons noté vos spécificités opérationnelles :")
            for cite in citations[:2]:
                body_lines.append(f"- {cite}")

        body_lines.extend([
            "",
            "Nous accompagnons les entreprises de services terrain dans l'interconnexion sur-mesure de leurs outils métiers (ERP, FSM, planning, facturation) afin d'éliminer la double saisie et d'accélérer la transmission des comptes rendus.",
            "",
            "Seriez-vous disponible pour un échange rapide de 10 minutes la semaine prochaine ?",
            "",
            "Bien cordialement,",
            "Anass",
        ])
        body = "\n".join(body_lines)

    return MessageDraftResult(
        subject=subject,
        body=body,
        evidence_citations=citations[:2],
        locale=locale,
        approval_status="draft_pending",
    )
