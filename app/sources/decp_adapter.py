"""France DECP Public Procurement Source Adapter Wrapper."""

from typing import Any
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)


class DecpAdapter(SourceAdapter):
    code: str = "decp"
    version: str = "2.0.0"
    country_coverage: list[str] = ["FR"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        from app.discovery.decp import load_decp, filter_relevant, aggregate_by_siret
        import polars as pl
        
        days_back = query_params.get("days_back", 120)
        max_results = query_params.get("max_results", 50)
        
        try:
            raw_df = await load_decp()
            filtered_df = filter_relevant(raw_df, days_back=days_back, max_rows=max_results)
            companies = aggregate_by_siret(filtered_df)
            
            records = []
            for comp in companies:
                records.append(
                    RawSourceRecord(
                        connector_code=self.code,
                        external_id=comp.get("siret") or comp.get("siren") or "unknown",
                        record_type="company",
                        payload=comp,
                    )
                )
            return records
        except Exception as e:
            raise RuntimeError(f"DECP discovery failed: {e}")

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        company_name = payload.get("titulaire_nom", "Titulaire Marché Public")
        siren = payload.get("titulaire_siren")

        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code="FR",
            identifier_scheme="siren" if siren else None,
            identifier_value=siren,
            raw_payload=payload,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        from app.discovery.decp import discover_decp_parquet_url
        try:
            url = await discover_decp_parquet_url()
            if url:
                return SourceHealth(code=self.code, is_healthy=True, status_message="DECP URL reachable")
        except Exception as e:
            return SourceHealth(code=self.code, is_healthy=False, status_message=str(e))
        return SourceHealth(code=self.code, is_healthy=False, status_message="DECP URL not found")
