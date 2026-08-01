"""France DECP Public Procurement Source Adapter Wrapper."""

from datetime import datetime, timezone
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
        if int(config.get("days_back", 120)) < 1:
            raise ValueError("DECP days_back must be positive")

    async def discover(
        self,
        checkpoint: dict[str, Any] | None,
        limit: int,
        query_params: dict[str, Any]
    ) -> tuple[list[RawSourceRecord], dict[str, Any] | None, bool]:
        from app.discovery.decp import (
            decp_plan_fingerprint,
            filter_relevant,
            load_decp,
            prepare_decp_award_records,
            slice_decp_awards_checkpointed,
        )

        days_back = query_params.get("days_back", 120)
        play_code = query_params.get("play_code")
        min_montant = query_params.get("min_montant")
        max_rows = query_params.get("max_rows")
        if not play_code:
            raise ValueError("DECP discovery requires an explicit play_code")
        await self.validate_config(query_params)

        try:
            raw_df = await load_decp()
            filtered_df = filter_relevant(
                raw_df,
                days_back=days_back,
                min_montant=min_montant,
                max_rows=max_rows,
                play_code=play_code,
            )
            awards = prepare_decp_award_records(filtered_df)
            fingerprint = decp_plan_fingerprint(
                play_code=play_code,
                days_back=days_back,
                min_montant=min_montant,
                max_rows=max_rows,
                adapter_version=self.version,
            )
            page, new_cp, exhausted = slice_decp_awards_checkpointed(
                awards,
                checkpoint=checkpoint,
                limit=limit,
                plan_fingerprint=fingerprint,
            )

            records = []
            for award in page:
                observed = datetime.fromisoformat(award["_source_event_date"])
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                records.append(
                    RawSourceRecord(
                        connector_code=self.code,
                        external_id=award["_source_external_id"],
                        record_type="award",
                        payload=award,
                        observed_at=observed,
                    )
                )

            return records, new_cp, exhausted
        except Exception as e:
            raise RuntimeError(f"DECP discovery failed: {e}")

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        company_name = payload.get("titulaire_nom") or "Titulaire Marché Public"
        siren = payload.get("siren")

        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code="FR",
            identifier_scheme="FR_SIREN" if siren else None,
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
                    is_healthy=False,
                    state=SourceCapabilityState.DEGRADED,
                    status_message=(
                        "DECP dataset manifest resolved; record retrieval and "
                        "checkpoint persistence not exercised by this health check"
                    ),
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
