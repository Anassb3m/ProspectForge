"""Manual Research Source Adapter."""

from typing import Any
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)


class ManualResearchAdapter(SourceAdapter):
    code: str = "manual"
    version: str = "1.0.0"
    country_coverage: list[str] = ["GB", "FR"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        return [
            RawSourceRecord(
                connector_code=self.code,
                external_id=query_params.get("external_id", "manual_entry"),
                record_type=query_params.get("record_type", "company"),
                payload=query_params,
                source_url=query_params.get("source_url"),
            )
        ]

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=payload.get("company_name", "Manual Target"),
            country_code=payload.get("country_code", "GB"),
            identifier_scheme=payload.get("identifier_scheme"),
            identifier_value=payload.get("identifier_value"),
            domain=payload.get("domain"),
            officer_name=payload.get("officer_name"),
            officer_title=payload.get("officer_title"),
            raw_payload=payload,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        return SourceHealth(
            code=self.code, is_healthy=True, status_message="Manual research entry ready"
        )
