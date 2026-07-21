"""France Field-Operations Integration Market Play definition (FIELD_OPERATIONS_FR_V2)."""

from app.plays.config_loader import MarketPlayConfig, load_play_config

FIELD_OPERATIONS_FR_DICT = {
    "code": "FIELD_OPERATIONS_FR_V2",
    "version": "2.0.0",
    "name": "France Operations & SAV Integration Play",
    "status": "pilot",
    "jurisdiction": "FR",
    "locale": "fr-FR",
    "owner": "Anass",
    "entity_policy": {
        "allowed_legal_forms": ["sas", "sarl", "sa", "sasu"],
        "excluded_legal_forms": ["auto_entrepreneur", "ei", "micro_entreprise"],
    },
    "verticals": {
        "include": [
            "Froid Commercial / Réfrigération Industrialisée",
            "CVC (Chauffage, Ventilation, Climatisation) & Maintenance Technique",
            "Maintenance Électrique & Courants Forts/Faibles",
            "Sécurité Incendie & Contrôle d'Accès",
            "Maintenance Industrielle Multi-Sites",
            "Services Techniques du Bâtiment & Facilities Management",
            "SAV Technique & Service Client Terrain",
        ],
        "exclude": [
            "Artisan Indépendant Sans Salariés",
            "Vente d'Équipements Sans Service Après-Vente",
            "Nettoyage Industriel Non Technique",
        ],
    },
    "classifications": {
        "scheme": "FR_NAF_REV2",
        "include_codes": [
            {"code": "4322B", "label": "Installation d'équipements thermiques et de climatisation"},
            {"code": "4321A", "label": "Travaux d'installation électrique dans tous locaux"},
            {"code": "3312Z", "label": "Réparation de machines et équipements mécaniques"},
            {"code": "3313Z", "label": "Réparation d'équipements électroniques et optiques"},
            {"code": "3314Z", "label": "Réparation d'équipements électriques"},
            {"code": "8020Z", "label": "Activités liées aux systèmes de sécurité"},
            {"code": "8110Z", "label": "Services combinés de soutien liés aux bâtiments"},
        ],
        "exclude_codes": ["4120A"],
    },
    "operational_size": {
        "min_field_technicians": 10,
        "max_field_technicians": 75,
        "allow_unknown_with_complexity": True,
    },
    "evidence_rules": {
        "required_any": [
            "OPERATIONS.COMPLEXITY.MULTI_BRANCH",
            "OPERATIONS.COMPLEXITY.RECURRING_CONTRACTS",
            "OPERATIONS.COMPLEXITY.ASTREINTE_247",
            "TECH.STACK.DISCONNECTED_FSM",
            "TECH.OPPORTUNITY.MANUAL_BON_INTERVENTION",
            "TRIGGER.HIRING.PLANIFICATEUR",
        ],
    },
    "buyer_roles": [
        {"title": "Gérant / Président", "code": "GERANT_PRESIDENT", "priority": 1},
        {"title": "Directeur Général", "code": "DIRECTEUR_GENERAL", "priority": 1},
        {"title": "Directeur des Opérations", "code": "DIRECTEUR_OPERATIONS", "priority": 2},
        {"title": "Responsable d'Exploitation", "code": "RESPONSABLE_EXPLOITATION", "priority": 3},
        {"title": "Responsable SAV", "code": "RESPONSABLE_SAV", "priority": 3},
        {"title": "Directeur Technique", "code": "DIRECTEUR_TECHNIQUE", "priority": 4},
        {"title": "Responsable Maintenance", "code": "RESPONSABLE_MAINTENANCE", "priority": 5},
    ],
    "compliance_policy": "fr_b2b_email_optout_v1",
    "scoring_profile": "field_ops_fr_v2",
    "message_policy": "evidence_first_fr_fr_v1",
}


def get_fr_play_config() -> MarketPlayConfig:
    return load_play_config(FIELD_OPERATIONS_FR_DICT)
