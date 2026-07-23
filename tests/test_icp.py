"""Buyer-role + V3 score shim tests."""


from app.discovery.icp import (
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
