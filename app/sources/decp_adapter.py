"""France DECP Public Procurement Source Adapter Wrapper."""

from typing import Any
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
    SourceCapabilityState,
)


class DecpAdapter(SourceAdapter):
    code: str = "decp"
    version: str = "2.0.0"
    country_coverage: list[str] = ["FR"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(
        self,
        checkpoint: dict[str, Any] | None,
        limit: int,
        query_params: dict[str, Any]
    ) -> tuple[list[RawSourceRecord], dict[str, Any] | None, bool]:
        from app.discovery.decp import load_decp, filter_relevant, aggregate_by_siret

        days_back = query_params.get("days_back", 120)
        play_code = query_params.get("play_code")

        try:
            raw_df = await load_decp()
            filtered_df = filter_relevant(raw_df, days_back=days_back, play_code=play_code)
            companies = aggregate_by_siret(filtered_df)

            # Sort descending by last_tender_date, then external_id
            for c in companies:
                c["_sort_id"] = c.get("siret") or c.get("siren") or "unknown"
                c["_sort_date"] = c.get("last_tender_date") or ""

            companies.sort(key=lambda x: (x["_sort_date"], x["_sort_id"]), reverse=True)

            start_idx = 0
            if checkpoint:
                cp_date = checkpoint.get("event_date", "")
                cp_id = checkpoint.get("external_id", "")
                for i, c in enumerate(companies):
                    if (c["_sort_date"], c["_sort_id"]) < (cp_date, cp_id):
                        start_idx = i
                        break
                else:
                    start_idx = len(companies)

            page = companies[start_idx : start_idx + limit]
            exhausted = (start_idx + limit >= len(companies))

            records = []
            new_cp = checkpoint
            for comp in page:
                records.append(
                    RawSourceRecord(
                        connector_code=self.code,
                        external_id=comp["_sort_id"],
                        record_type="company",
                        payload=comp,
                    )
                )
                new_cp = {"event_date": comp["_sort_date"], "external_id": comp["_sort_id"]}

            return records, new_cp, exhausted
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
                return SourceHealth(
                    code=self.code,
                    is_healthy=True,
                    state=SourceCapabilityState.HEALTHY,
                    status_message="DECP dataset manifest resolved",
                )
        except Exception as e:
            return SourceHealth(
                code=self.code,
                is_healthy=False,
                state=SourceCapabilityState.UPSTREAM_UNAVAILABLE,
                status_message=str(e),
            )
        return SourceHealth(
            code=self.code,
            is_healthy=False,
            state=SourceCapabilityState.DEGRADED,
            status_message="DECP dataset URL not found",
        )
