"""Message-draft unit tests and qualification-gate integration coverage."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.messaging import (
    build_message_drafts,
    drafts_for_prospect,
    message_drafts_are_unlocked,
)


def _prospect(**overrides):
    values = {
        "company_name": "Froid Pro SAS",
        "sector": "Installation et maintenance frigorifique",
        "decision_maker_name": "Marie Dupont",
        "award_history": [
            {"objet": "Maintenance des installations frigorifiques", "date": "2026-07-01"}
        ],
        "recommended_offer": "un système de pilotage des interventions et rapports",
        "manual_review_state": "accepted",
        "qualification_decision": "accept",
        "opted_out": False,
        "anonymized": False,
        "is_suppressed": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


# ── Pure drafting logic (8) ────────────────────────────────────────────────


def test_connection_note_uses_first_name_and_stays_within_linkedin_limit():
    drafts = build_message_drafts(_prospect())
    assert drafts.linkedin_connection_note.startswith("Bonjour Marie,")
    assert len(drafts.linkedin_connection_note) <= 300


def test_award_reference_is_used_when_present():
    drafts = build_message_drafts(_prospect())
    assert "Maintenance des installations frigorifiques" in drafts.linkedin_first_message
    assert "Maintenance des installations frigorifiques" in drafts.email_body


def test_sector_is_the_factual_fallback_without_an_award():
    drafts = build_message_drafts(_prospect(award_history=[]))
    assert "Installation et maintenance frigorifique" in drafts.linkedin_connection_note
    assert "Installation et maintenance frigorifique" in drafts.email_body


def test_email_has_subject_signature_placeholders_and_courtesy_opt_out():
    drafts = build_message_drafts(_prospect())
    assert "Froid Pro SAS" in drafts.email_subject
    assert "[Votre prénom]" in drafts.email_body
    assert "[Votre société]" in drafts.email_body
    assert "je ne vous relancerai pas" in drafts.email_body


def test_drafts_are_deterministic():
    prospect = _prospect()
    assert build_message_drafts(prospect) == build_message_drafts(prospect)


def test_drafts_do_not_claim_the_company_has_specific_tools_or_pain():
    drafts = build_message_drafts(_prospect())
    combined = "\n".join(
        [drafts.linkedin_connection_note, drafts.linkedin_first_message, drafts.email_body]
    ).lower()
    assert "vous utilisez excel" not in combined
    assert "vous manquez" not in combined
    assert "je ne présume pas de vos outils" in combined


def test_drafts_unlock_only_after_completed_accept_state():
    accepted = _prospect()
    assert message_drafts_are_unlocked(accepted) is True
    assert drafts_for_prospect(accepted) is not None
    assert drafts_for_prospect(_prospect(manual_review_state="unreviewed")) is None
    assert drafts_for_prospect(_prospect(qualification_decision="research_more")) is None


def test_opt_out_anonymization_or_suppression_relocks_drafts():
    assert drafts_for_prospect(_prospect(opted_out=True)) is None
    assert drafts_for_prospect(_prospect(anonymized=True)) is None
    assert drafts_for_prospect(_prospect(is_suppressed=True)) is None


# ── Real HTTP qualification flow (3) ───────────────────────────────────────


async def _create_prospect(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_prospect_payload: dict,
) -> int:
    response = await client.post(
        "/api/prospects",
        json={
            **sample_prospect_payload,
            "decision_maker_name": "Marie Dupont",
            "sector": "Construction",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _accept_form(**overrides) -> dict[str, str]:
    form = {
        "decision": "accept",
        "notes": "Pain and offer checked during qualification",
        "fit_confirmed": "on",
        "pain_confirmed": "on",
        "trigger_confirmed": "on",
        "buyer_confirmed": "on",
        "contact_confirmed": "on",
        "offer_match_confirmed": "on",
    }
    form.update(overrides)
    return form


@pytest.mark.asyncio
async def test_detail_page_keeps_drafts_locked_before_acceptance(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_prospect_payload: dict,
):
    prospect_id = await _create_prospect(client, auth_headers, sample_prospect_payload)
    response = await client.get(f"/prospects/{prospect_id}", headers=auth_headers)
    assert response.status_code == 200
    assert 'id="message-drafts"' not in response.text
    assert "LinkedIn connection note" not in response.text


@pytest.mark.asyncio
async def test_full_accept_unlocks_message_drafts_on_detail_page(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_prospect_payload: dict,
):
    prospect_id = await _create_prospect(client, auth_headers, sample_prospect_payload)
    accepted = await client.post(
        f"/queue/{prospect_id}/qualify",
        data=_accept_form(),
        headers=auth_headers,
        follow_redirects=False,
    )
    assert accepted.status_code == 303

    detail = await client.get(f"/prospects/{prospect_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert 'id="message-drafts"' in detail.text
    assert "LinkedIn connection note" in detail.text
    assert "je ne vous relancerai pas" in detail.text


@pytest.mark.asyncio
async def test_missing_accept_checkbox_keeps_message_drafts_locked(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_prospect_payload: dict,
):
    prospect_id = await _create_prospect(client, auth_headers, sample_prospect_payload)
    incomplete = _accept_form()
    incomplete.pop("offer_match_confirmed")
    rejected = await client.post(
        f"/queue/{prospect_id}/qualify",
        data=incomplete,
        headers=auth_headers,
        follow_redirects=False,
    )
    assert rejected.status_code == 400

    detail = await client.get(f"/prospects/{prospect_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert 'id="message-drafts"' not in detail.text
