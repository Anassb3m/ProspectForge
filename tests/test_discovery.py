"""Unit tests for DECP filter, NAF mapping, email candidates, scoring v2.1."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from app.discovery.decp import aggregate_by_siret, filter_relevant
from app.discovery.emails import (
    extract_domain,
    generate_email_candidates,
    parse_person_name,
)
from app.discovery.naf import is_it_cyber_naf, map_naf_to_sector, map_tranche_effectifs
from app.discovery.reacher import pick_best_email
from app.scoring import calculate_urgency_score, explain_score, priority_from_score


class TestNaf:
    def test_it_codes(self):
        assert is_it_cyber_naf("6201Z")
        assert is_it_cyber_naf("62.01Z")
        assert is_it_cyber_naf("6311Z")
        assert not is_it_cyber_naf("4120A")

    def test_sector_map(self):
        assert map_naf_to_sector("6202A") == "IT / Digital"
        assert map_naf_to_sector("4120A") == "Construction"
        assert map_naf_to_sector("4941A") == "Logistics"

    def test_tranche(self):
        assert map_tranche_effectifs("12") == "11-50"
        assert map_tranche_effectifs("32") == "51-200"
        assert map_tranche_effectifs("01") == "1-10"


class TestEmails:
    def test_parse_name(self):
        assert parse_person_name("Marie Dupont") == ("Marie", "Dupont")
        assert parse_person_name("Jean-Pierre Martin")[1] == "Martin"

    def test_extract_domain(self):
        assert extract_domain("https://www.acme-soft.fr/contact") == "acme-soft.fr"
        assert extract_domain(None, "a@acme.fr") == "acme.fr"

    def test_candidates_named(self):
        cands = generate_email_candidates("acme.fr", "Marie", "Dupont")
        emails = [c["email"] for c in cands]
        assert "marie.dupont@acme.fr" in emails
        assert "m.dupont@acme.fr" in emails
        assert "contact@acme.fr" in emails
        # Named patterns before roles
        assert emails.index("marie.dupont@acme.fr") < emails.index("contact@acme.fr")

    def test_harvester_priority(self):
        cands = generate_email_candidates(
            "acme.fr",
            harvester_emails=["hello@acme.fr", "other@gmail.com"],
        )
        assert cands[0]["email"] == "hello@acme.fr"
        assert cands[0]["priority"] == 0


class TestDecpFilter:
    def _sample_df(self) -> pl.DataFrame:
        today = datetime.now(timezone.utc).replace(tzinfo=None)
        old = today - timedelta(days=200)
        return pl.DataFrame(
            {
                "id": ["m1", "m2", "m3", "m4"],
                "dateAttribution": [
                    today.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    old.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                ],
                "codeCPV": ["72000000", "45000000", "72000000", "30000000"],
                "objetMarche": [
                    "Infogérance SI",
                    "Travaux bâtiment",
                    "Old IT contract",
                    "Prestations cybersécurité cloud",
                ],
                "titulaire_siret": [
                    "12345678900012",
                    "98765432100011",
                    "12345678900012",
                    "11122233300044",
                ],
                "titulaire_nom": ["SoftCo", "BuildCo", "SoftCo", "CyberSME"],
                "montant": [80000.0, 10000.0, 5000.0, 120000.0],
                "acheteur_nom": ["Ministère A", "Ville B", "Ministère A", "Région C"],
            }
        )

    def test_filters_field_service_not_it_software(self):
        # V3 play: maintenance/installation — not pure software CPV 72
        today = datetime.now(timezone.utc).replace(tzinfo=None)
        old = today - timedelta(days=200)
        df = pl.DataFrame(
            {
                "id": ["m1", "m2", "m3"],
                "dateAttribution": [
                    today.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    old.strftime("%Y-%m-%d"),
                ],
                "codeCPV": ["50710000", "72000000", "45331000"],
                "objetMarche": [
                    "Contrat maintenance froid commercial",
                    "Développement logiciel métier",
                    "Installation climatisation multi-sites",
                ],
                "titulaire_siret": [
                    "12345678900012",
                    "98765432100011",
                    "11122233300044",
                ],
                "titulaire_nom": ["FroidPro", "SoftCo", "ClimTech"],
                "montant": [80000.0, 100000.0, 45000.0],
                "acheteur_nom": ["Région", "Ministère", "Ville"],
            }
        )
        filtered = filter_relevant(df, days_back=90)
        sirets = set(filtered["titulaire_siret"].to_list())
        assert "12345678900012" in sirets  # maintenance froid (keyword + CPV 50x)
        # pure software CPV 72 + negative keywords must not enter field-service play
        assert "98765432100011" not in sirets
        assert filtered.height >= 1

    def test_aggregate_multi_win(self):
        today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")
        df = pl.DataFrame(
            {
                "id": ["a", "b"],
                "dateAttribution": [today, today],
                "codeCPV": ["50710000", "45331000"],
                "objetMarche": ["Maintenance technique", "Installation chauffage"],
                "titulaire_siret": ["12345678900012", "12345678900012"],
                "titulaire_nom": ["TechCo", "TechCo"],
                "montant": [10000.0, 20000.0],
                "acheteur_nom": ["A", "B"],
            }
        )
        filtered = filter_relevant(df, days_back=90)
        companies = aggregate_by_siret(filtered)
        assert len(companies) == 1
        assert companies[0]["award_count"] == 2
        assert companies[0]["has_multiple"] is True
        assert "evidence" in companies[0]


class TestScoringV21:
    def _p(self, **kwargs):
        defaults = dict(
            signal_type="OTHER",
            signal_details=None,
            decision_maker_title=None,
            company_size="1-10",
            naf_code=None,
            award_history=None,
            contact_confidence=None,
            outreach_events=[],
            urgency_score=50,
            priority_level="Medium",
        )
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_decp_win_base(self):
        p = self._p(signal_type="DECP_WIN")
        assert calculate_urgency_score(p, []) == 80  # 50+30

    def test_decp_multi_and_cyber(self):
        p = self._p(
            signal_type="DECP_WIN",
            signal_details="multiple wins · cybersécurité",
            award_history=[
                {"date": datetime.now(timezone.utc).date().isoformat(), "montant": 60000},
                {"date": datetime.now(timezone.utc).date().isoformat(), "montant": 10000},
            ],
            naf_code="6201Z",
            company_size="11-50",
        )
        score = calculate_urgency_score(p, [])
        # 50+30+15+10+12+8 = 125 → 100
        assert score == 100
        assert priority_from_score(score) == "High"

    def test_explain_score(self):
        p = self._p(signal_type="DECP_WIN", naf_code="6202A", company_size="51-200")
        parts = explain_score(p, [])
        labels = [c["label"] for c in parts]
        assert any("DECP" in l or "BOAMP" in l or "Public" in l for l in labels)
        assert any("NAF" in l for l in labels)

    def test_pick_best_email(self):
        results = [
            {"email": "a@x.fr", "confidence": "invalid"},
            {"email": "b@x.fr", "confidence": "likely"},
            {"email": "c@x.fr", "confidence": "verified"},
        ]
        best = pick_best_email(results)
        assert best["email"] == "c@x.fr"


@pytest.mark.asyncio
async def test_discover_contacts_no_domain():
    from app.discovery.contacts import discover_contacts

    result = await discover_contacts(website=None, domain=None)
    assert result["needs_manual_review"] is True
    assert result["best_email"] is None


@pytest.mark.asyncio
async def test_discover_contacts_mocked_reacher():
    from app.discovery.contacts import discover_contacts

    mock_results = [
        {
            "email": "marie.dupont@acme.fr",
            "is_reachable": "safe",
            "is_deliverable": True,
            "is_catch_all": False,
            "confidence": "verified",
            "raw": {},
        }
    ]
    with (
        patch("app.discovery.contacts.harvest_emails", new_callable=AsyncMock, return_value=[]),
        patch(
            "app.discovery.contacts.check_emails_batch",
            new_callable=AsyncMock,
            return_value=mock_results,
        ),
        patch("app.config.get_settings") as gs,
    ):
        gs.return_value = SimpleNamespace(
            reacher_enabled=True,
            reacher_url="http://localhost:8080",
            harvester_enabled=False,
        )
        result = await discover_contacts(
            domain="acme.fr",
            person_name="Marie Dupont",
            run_harvester=False,
            verify=True,
        )
    assert result["best_email"] == "marie.dupont@acme.fr"
    assert result["contact_confidence"] == "verified"
    assert result["needs_manual_review"] is False
