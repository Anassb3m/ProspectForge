"""Client discovery pipeline: DECP → Sirene → email waterfall → score."""

from app.discovery.emails import generate_email_candidates, parse_person_name
from app.discovery.naf import is_it_cyber_naf, map_naf_to_sector, map_tranche_effectifs
from app.discovery.reacher import check_email, check_emails_batch
from app.discovery.sirene import enrich_sirene

__all__ = [
    "generate_email_candidates",
    "parse_person_name",
    "is_it_cyber_naf",
    "map_naf_to_sector",
    "map_tranche_effectifs",
    "check_email",
    "check_emails_batch",
    "enrich_sirene",
]
