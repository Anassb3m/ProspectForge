"""Buyer-role + V3 score shim tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.discovery.icp import (
    compute_acquisition_score,
    format_dirigeant_name,
    pick_best_dirigeant,
    score_naf_fit,
)


def test_naf_field_vs_it():
    s, b = score_naf_fit("43.22B")
    assert s == 100
    s2, _ = score_naf_fit("62.01Z")
    assert s2 < 30


def test_pick_president():
    dirs = [
        {
            "nom": "X",
            "prenoms": "Y",
            "qualite": "Commissaire aux comptes titulaire",
            "type_dirigeant": "personne physique",
        },
        {
            "nom": "DUPONT",
            "prenoms": "MARIE",
            "qualite": "Président de SAS",
            "type_dirigeant": "personne physique",
        },
    ]
    best = pick_best_dirigeant(dirs)
    assert best["nom"] == "DUPONT"
    assert "Marie" in format_dirigeant_name(best)


def test_field_service_hot_lead_scores():
    p = SimpleNamespace(
        company_name="Clim Maintenance SA",
        naf_code="4322B",
        company_size="11-50",
        decision_maker_title="Gérant",
        decision_maker_name="Marie Dupont",
        dirigeants=[
            {
                "nom": "DUPONT",
                "prenoms": "MARIE",
                "qualite": "Gérant",
                "type_dirigeant": "personne physique",
            }
        ],
        award_history=[
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "montant": 90000,
                "objet": "Maintenance climatisation multi-sites",
                "acheteur": "Région",
            }
        ],
        last_tender_date=datetime.now(timezone.utc),
        signal_type="PUBLIC_AWARD",
        signal_details="maintenance multi-sites",
        email="marie.dupont@clim.fr",
        contact_confidence="deliverable",
        website="https://clim.fr",
        phone=None,
        data_source="DECP",
        siren="123456789",
        notes="",
        evidence_json=[],
        manual_review_state="unreviewed",
        qualification_decision=None,
        opted_out=False,
        market_play_code="FIELD_SERVICE_OPERATIONS_FR",
    )
    bd = compute_acquisition_score(p)
    assert bd.fit >= 70
    assert bd.acquisition >= 45
