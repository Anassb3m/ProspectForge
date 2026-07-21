"""UK Field-Operations Integration Market Play definition (FIELD_OPERATIONS_UK_V1)."""

from app.plays.config_loader import MarketPlayConfig, load_play_config

FIELD_OPERATIONS_UK_DICT = {
    "code": "FIELD_OPERATIONS_UK_V1",
    "version": "1.0.0",
    "name": "UK Field-Operations Integration & Acquisition Play",
    "status": "pilot",
    "jurisdiction": "GB",
    "locale": "en-GB",
    "owner": "Anass",
    "entity_policy": {
        "allowed_legal_forms": ["ltd", "llp", "plc"],
        "excluded_legal_forms": ["sole_trader", "unincorporated_partnership"],
    },
    "verticals": {
        "include": [
            "Commercial HVAC & Refrigeration",
            "Fire & Security Systems Installation/Maintenance",
            "Electrical Maintenance & Technical Services",
            "Industrial Machinery Maintenance",
            "Technical Building Services & Facilities Support",
            "Specialist Field Technical Inspection & Service",
        ],
        "exclude": [
            "Residential Domestic Plumbing (Sole Trader)",
            "Pure Equipment Retail (No Servicing)",
            "Non-Technical Janitorial Service",
            "Civil Engineering Infrastructure Contracting",
        ],
    },
    "classifications": {
        "scheme": "UK_SIC_2007",
        "include_codes": [
            {"code": "43220", "label": "Plumbing, heat and air-conditioning installation"},
            {"code": "43210", "label": "Electrical installation"},
            {"code": "43290", "label": "Other construction installation"},
            {"code": "33120", "label": "Repair of machinery"},
            {"code": "33130", "label": "Repair of electronic and optical equipment"},
            {"code": "33140", "label": "Repair of electrical equipment"},
            {"code": "80200", "label": "Security systems service activities"},
            {"code": "81100", "label": "Combined facilities support activities"},
        ],
        "exclude_codes": ["41202", "42110"],
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
            "OPERATIONS.COMPLEXITY.ON_CALL_247",
            "TECH.STACK.DISCONNECTED_FSM",
            "TECH.OPPORTUNITY.MANUAL_JOB_SHEETS",
            "TRIGGER.HIRING.SERVICE_COORDINATOR",
        ],
    },
    "buyer_roles": [
        {"title": "Managing Director", "code": "MANAGING_DIRECTOR", "priority": 1},
        {"title": "Operations Director", "code": "OPERATIONS_DIRECTOR", "priority": 2},
        {"title": "Head of Operations", "code": "HEAD_OF_OPERATIONS", "priority": 2},
        {"title": "Service Director", "code": "SERVICE_DIRECTOR", "priority": 3},
        {"title": "Service Manager", "code": "SERVICE_MANAGER", "priority": 3},
        {"title": "Field Service Manager", "code": "FIELD_SERVICE_MANAGER", "priority": 4},
        {"title": "Technical Director", "code": "TECHNICAL_DIRECTOR", "priority": 5},
        {"title": "General Manager", "code": "GENERAL_MANAGER", "priority": 6},
    ],
    "compliance_policy": "uk_b2b_email_corporate_v1",
    "scoring_profile": "field_ops_uk_v1",
    "message_policy": "evidence_first_en_gb_v1",
}


def get_uk_play_config() -> MarketPlayConfig:
    return load_play_config(FIELD_OPERATIONS_UK_DICT)
