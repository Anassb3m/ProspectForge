"""Tests for Evidence-Backed Personalized Messaging Engine."""

from app.services.messaging_engine import generate_message_draft


def test_generate_message_draft_en_gb():
    draft = generate_message_draft(
        company_name="Apex Refrigeration Ltd",
        buyer_name="John Smith",
        buyer_title="Managing Director",
        evidence_items=[
            {"evidence_text": "Company runs 24/7 emergency response service"},
            {"evidence_text": "Multiple regional service depots in North West"},
        ],
        locale="en-GB",
    )
    assert draft.locale == "en-GB"
    assert "Apex Refrigeration Ltd" in draft.subject
    assert "Hi John Smith" in draft.body
    assert len(draft.evidence_citations) == 2
    assert "24/7 emergency response" in draft.body


def test_generate_message_draft_fr_fr():
    draft = generate_message_draft(
        company_name="Dépannage Froid SAS",
        buyer_name="Pierre Dubois",
        buyer_title="Gérant",
        evidence_items=[
            {"evidence_text": "Contrats d'entretien multi-sites"},
        ],
        locale="fr-FR",
    )
    assert draft.locale == "fr-FR"
    assert "Dépannage Froid SAS" in draft.subject
    assert "Bonjour Pierre Dubois" in draft.body
    assert len(draft.evidence_citations) == 1
