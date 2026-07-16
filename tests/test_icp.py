"""ICP / acquisition score unit tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.discovery.icp import (
    compute_acquisition_score,
    format_dirigeant_name,
    pick_best_dirigeant,
    score_naf_fit,
    score_timing_from_awards,
)


def test_naf_core():
    s, b = score_naf_fit("62.01Z")
    assert s == 100
    assert b


def test_pick_president():
    dirs = [
        {"nom": "X", "prenoms": "Y", "qualite": "Commissaire aux comptes titulaire", "type_dirigeant": "personne physique"},
        {"nom": "DUPONT", "prenoms": "MARIE", "qualite": "Président de SAS", "type_dirigeant": "personne physique"},
    ]
    best = pick_best_dirigeant(dirs)
    assert best["nom"] == "DUPONT"
    assert "Marie" in format_dirigeant_name(best)


def test_timing_recent_multi():
    today = datetime.now(timezone.utc).date().isoformat()
    history = [
        {"date": today, "montant": 80000, "objet": "Infogérance cybersécurité", "acheteur": "Ministère de l'Intérieur"},
        {"date": today, "montant": 20000, "objet": "TMA cloud", "acheteur": "Région Île-de-France"},
    ]
    score, badges, reasons = score_timing_from_awards(history, None, "DECP_WIN")
    assert score >= 70
    assert any("Multi" in b or "win" in b.lower() for b in badges)


def test_acquisition_hot_lead():
    p = SimpleNamespace(
        naf_code="6201Z",
        company_size="51-200",
        decision_maker_title="Président",
        decision_maker_name="Marie Dupont",
        dirigeants=[{"nom": "DUPONT", "prenoms": "MARIE", "qualite": "Président de SAS", "type_dirigeant": "personne physique"}],
        award_history=[
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "montant": 150000,
                "objet": "SOC cybersécurité",
                "acheteur": "Ministère",
            }
        ],
        last_tender_date=datetime.now(timezone.utc),
        signal_type="DECP_WIN",
        email="marie.dupont@acme.fr",
        contact_confidence="verified",
        website="https://acme.fr",
        phone=None,
    )
    bd = compute_acquisition_score(p)
    assert bd.acquisition >= 70
    assert bd.fit >= 70
    assert bd.badges
    assert bd.reasons
