from typing import Any
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)

class OcdsAdapter(SourceAdapter):
    code: str = "ocds"
    version: str = "1.0.0"
    country_coverage: list[str] = ["GLOBAL"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        # Phase 4 real OCDS logic will be implemented here.
        # This will query OCDS compatible portals (like OpenOpps, UK Contracts Finder etc)
        return []

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        company_name = payload.get("tenderer_name", "Unknown OCDS Tenderer")
        company_id = payload.get("tenderer_id")
        
        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code="UNKNOWN",
            identifier_scheme="ocds_tenderer_id" if company_id else None,
            identifier_value=company_id,
            raw_payload=payload,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        return SourceHealth(
            code=self.code, is_healthy=True, status_message="OCDS parser ready"
        )
