"""
Market play: FIELD_SERVICE_OPERATIONS_FR

Target: non-technical / lightly technical French SMEs that run field technicians
(install, maintain, intervene) and need operational control systems —
not software houses that build their own tools.
"""

from __future__ import annotations

FIELD_SERVICE_PLAY = {
    "code": "FIELD_SERVICE_OPERATIONS_FR",
    "name": "Field-service operations — France",
    "version": 1,
    "is_active": True,
    # Installation, maintenance, facilities — not software (62/63)
    "target_naf_prefixes": ["33", "43", "81", "71"],
    "target_naf_codes": [
        "4321A", "4321B", "4322A", "4322B", "4329A", "4329B",
        "3312Z", "3320A", "3320B", "3320C", "3320D",
        "8110Z", "8121Z", "8122Z",
        "7112B",
        "3313Z", "3314Z",
    ],
    "excluded_naf_codes": [
        "6201Z", "6202A", "6202B", "6203Z", "6209Z",
        "6311Z", "6312Z", "5829A", "5829B",
        "7022Z",  # pure management consulting often weak fit
    ],
    "excluded_naf_prefixes": ["62", "63", "58", "61"],
    # Public procurement CPV for technical works / maintenance (not software 72/48/62)
    "cpv_prefixes": [
        "45",  # construction work
        "50",  # repair and maintenance
        "507",  # repair of equipment
        "453",  # building installation
        "397",  # domestic appliances (sometimes cold chain)
        "425",  # cooling and ventilation
        "4533",  # plumbing/heating
        "4531",  # electrical
        "9091",  # cleaning (facilities-adjacent)
        "713",  # engineering / technical services
        "7999",
    ],
    "positive_keywords": [
        "maintenance",
        "entretien",
        "froid",
        "réfrigération",
        "refrigeration",
        "clim",
        "climatisation",
        "chauffage",
        "cvac",
        "hvac",
        "électrique",
        "electrique",
        "installation technique",
        "intervention",
        "technicien",
        "dépannage",
        "depannage",
        "multisite",
        "multi-sites",
        "contrat de maintenance",
        "génie climatique",
        "genie climatique",
        "sécurité incendie",
        "securite incendie",
        "SSI",
        "ascenseur",
        "plomberie",
        "chauffagiste",
        "facilities",
        "facility management",
        "GTB",
        "GMAO",
        "sav ",
        "après-vente",
        "apres-vente",
        "travaux techniques",
        "mise en service",
    ],
    "negative_keywords": [
        "développement logiciel",
        "developpement logiciel",
        "cybersécurité",
        "cybersecurite",
        "infogérance",
        "infogerance",
        "hébergement cloud",
        "hebergement cloud",
        "application mobile",
        "site web",
        "seo ",
        "marketing digital",
        "ssii",
        "esn ",
        "éditeurs de logiciels",
        "editeurs de logiciels",
    ],
    "target_sizes": ["11-50", "51-200", "1-10"],
    "target_regions": None,
    "pain_hypotheses": [
        "Devis et relances clients éclatés entre mails et tableurs",
        "Planning techniciens géré manuellement",
        "Rapports d'intervention papier / WhatsApp / PDF déconnectés",
        "Stock pièces et véhicules peu visible",
        "Double saisie commercial / technique / admin",
        "Reporting contrats récurrents trop long",
        "Preuves d'intervention difficiles à retrouver",
        "Pas de vue temps réel pour le management",
    ],
    "trigger_definitions": [
        "Attribution récente marché public maintenance / installation",
        "Plusieurs lots ou contrats en peu de temps",
        "Nouvel établissement / agence",
        "Embauche planificateur, ADV, coordinateur SAV",
        "Expansion multi-sites mentionnée",
        "Mention Excel / reporting manuel / GMAO sur site ou offre d'emploi",
    ],
    "buyer_roles": [
        {"role": "gerant_owner", "labels": ["gérant", "gerant", "président", "president", "fondateur", "dirigeant"], "priority": 1},
        {"role": "operations", "labels": ["directeur d'exploitation", "directeur operations", "directeur des opérations", "responsable exploitation"], "priority": 2},
        {"role": "service_maintenance", "labels": ["directeur de service", "responsable maintenance", "responsable sav", "directeur technique"], "priority": 3},
        {"role": "admin_finance", "labels": ["daf", "directeur administratif", "responsable administratif"], "priority": 4},
        {"role": "commercial", "labels": ["directeur commercial", "responsable commercial"], "priority": 5},
    ],
    "exclusions": [
        "ESN / éditeur logiciel / agence digitale",
        "Équipe produit/engineering interne substantielle",
        "Grande entreprise hors ticket de deal",
        "Micro-activité sans complexité opérationnelle",
        "Inactif / non diffusible / opt-out",
    ],
    "score_config": {
        "weights": {
            "fit": 0.25,
            "pain": 0.25,
            "trigger": 0.20,
            "authority": 0.15,
            "value": 0.10,
            "data_quality": 0.05,
        },
        "penalties": {
            "internal_it_team": 25,
            "oversized": 15,
            "micro_weak": 15,
            "single_source": 10,
            "guessed_catchall": 15,
            "stale_trigger": 10,
            "stale_person": 20,
        },
    },
    "readiness_config": {
        "fit_score_min": 55,
        "pain_score_min": 35,
        "trigger_score_min": 25,
        "authority_score_min": 40,
        "data_quality_min": 45,
        "independent_source_types_min": 1,  # pilot: allow 1 then human gate
        "active_signals_min": 2,
        "human_review_required": True,
        "offer_asset_required": False,  # pilot until assets uploaded
        "suppression_clear_required": True,
    },
    "offer_name": "Système de pilotage terrain (devis · interventions · techniciens · rapports)",
    "offer_summary": (
        "Un système opérationnel pour devis, interventions, techniciens, rapports, pièces "
        "et visibilité management — configuré sur le workflow réel de l'entreprise, "
        "pas un développement générique."
    ),
    "structural_keywords_website": [
        "technicien",
        "intervention",
        "maintenance",
        "dépannage",
        "depannage",
        "agence",
        "agences",
        "flotte",
        "véhicule",
        "vehicule",
        "sav",
        "contrat d'entretien",
        "contrat d entretien",
        "urgence 24",
        "astreinte",
    ],
    "registry_queries": [
        "froid commercial",
        "climatisation maintenance",
        "chauffage installation",
        "électricité bâtiment",
        "maintenance industrielle",
        "sécurité incendie installation",
        "génie climatique",
        "facility management technique",
        "dépannage technique",
        "multiservice technique",
    ],
}
