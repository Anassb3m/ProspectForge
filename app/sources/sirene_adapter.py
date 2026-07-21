from typing import Any
from app.discovery.annuaire import search_companies
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)


class SireneAdapter(SourceAdapter):
    code: str = "sirene"
    version: str = "2.0.0"
    country_coverage: list[str] = ["FR"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        query = query_params.get("query", "")
        naf_code = query_params.get("naf_code", "")

        res_data = await search_companies(
            q=query,
            activite_principale=naf_code if naf_code else None,
            per_page=query_params.get("limit", 10),
        )
        results = res_data.get("results", [])

        records: list[RawSourceRecord] = []
        for item in results:
            siren = item.get("siren") or "000000000"
            records.append(
                RawSourceRecord(
                    connector_code=self.code,
                    external_id=siren,
                    record_type="company",
                    payload=item,
                    source_url=f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}",
                )
            )
        return records

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        company_name = (
            payload.get("nom_complet")
            or payload.get("nom_raison_sociale")
            or payload.get("company_name", "Entreprise Inconnue")
        )
        siren = payload.get("siren") or raw_record.external_id
        siret = payload.get("siret")
        naf = payload.get("activite_principale") or payload.get("naf_code")

        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code="FR",
            identifier_scheme="siren" if len(siren) == 9 else "siret",
            identifier_value=siren if len(siren) == 9 else (siret or siren),
            classification_scheme="FR_NAF_REV2",
            classification_code=naf,
            address={
                "street": payload.get("adresse"),
                "locality": payload.get("libelle_commune") or payload.get("city"),
                "postal_code": payload.get("code_postal") or payload.get("postal_code"),
                "country": "France",
            },
            raw_payload=payload,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        return SourceHealth(
            code=self.code, is_healthy=True, status_message="Sirene public API reachable"
        )
