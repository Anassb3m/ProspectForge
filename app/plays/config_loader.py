"""Market play configuration engine and validator."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketPlayConfig:
    code: str
    version: str
    name: str
    status: str  # draft, pilot, active, paused, retired
    jurisdiction: str  # GB, FR
    locale: str  # en-GB, fr-FR
    entity_policy: dict[str, list[str]] = field(default_factory=dict)
    verticals: dict[str, list[str]] = field(default_factory=dict)
    classifications: dict[str, Any] = field(default_factory=dict)
    operational_size: dict[str, Any] = field(default_factory=dict)
    evidence_rules: dict[str, Any] = field(default_factory=dict)
    buyer_roles: list[dict[str, Any]] = field(default_factory=list)
    compliance_policy: str = "uk_b2b_email_corporate_v1"
    scoring_profile: str = "field_ops_uk_v1"
    message_policy: str = "evidence_first_en_gb_v1"
    owner: str = "Anass"

    def validate(self) -> None:
        """Validate play configuration completeness and constraints."""
        if not self.code or not self.version:
            raise ValueError("Play code and version must be non-empty.")
        if self.jurisdiction not in ("GB", "FR"):
            raise ValueError(f"Unsupported jurisdiction: {self.jurisdiction}")
        if self.status not in ("draft", "pilot", "active", "paused", "retired"):
            raise ValueError(f"Invalid play status: {self.status}")
        if not self.buyer_roles:
            raise ValueError("Play must specify priority buyer roles.")


def load_play_config(raw_dict: dict[str, Any]) -> MarketPlayConfig:
    config = MarketPlayConfig(
        code=raw_dict["code"],
        version=raw_dict["version"],
        name=raw_dict["name"],
        status=raw_dict.get("status", "pilot"),
        jurisdiction=raw_dict.get("jurisdiction", "GB"),
        locale=raw_dict.get("locale", "en-GB"),
        entity_policy=raw_dict.get("entity_policy", {}),
        verticals=raw_dict.get("verticals", {}),
        classifications=raw_dict.get("classifications", {}),
        operational_size=raw_dict.get("operational_size", {}),
        evidence_rules=raw_dict.get("evidence_rules", {}),
        buyer_roles=raw_dict.get("buyer_roles", []),
        compliance_policy=raw_dict.get("compliance_policy", "uk_b2b_email_corporate_v1"),
        scoring_profile=raw_dict.get("scoring_profile", "field_ops_uk_v1"),
        message_policy=raw_dict.get("message_policy", "evidence_first_en_gb_v1"),
        owner=raw_dict.get("owner", "Anass"),
    )
    config.validate()
    return config
