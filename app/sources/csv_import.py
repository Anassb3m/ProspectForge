"""Commercial CSV Data Import Adapter."""

import csv
import io
from typing import Any
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)


class CsvImportAdapter(SourceAdapter):
    code: str = "csv_import"
    version: str = "1.0.0"
    country_coverage: list[str] = ["GB", "FR"]

    async def validate_config(self, config: dict[str, Any]) -> None:
        pass

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        csv_content = query_params.get("csv_content", "")
        if not csv_content:
            return []

        records: list[RawSourceRecord] = []
        reader = csv.DictReader(io.StringIO(csv_content))
        for idx, row in enumerate(reader):
            ext_id = row.get("id") or row.get("Company Number") or row.get("SIREN") or f"csv_{idx+1}"
            records.append(
                RawSourceRecord(
                    connector_code=self.code,
                    external_id=str(ext_id),
                    record_type="company",
                    payload=dict(row),
                )
            )
        return records

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        row = raw_record.payload
        company_name = (
            row.get("Company Name")
            or row.get("company_name")
            or row.get("Company")
            or row.get("Nom")
            or "Imported Entity"
        )
        country = row.get("Country") or row.get("country_code") or "GB"
        domain = row.get("Website") or row.get("domain") or row.get("Site")
        ch_num = row.get("Company Number") or row.get("companies_house_number")
        siren = row.get("SIREN") or row.get("siren")

        scheme = "companies_house_number" if ch_num else ("siren" if siren else None)
        value = ch_num or siren

        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code=country.upper()[:2],
            identifier_scheme=scheme,
            identifier_value=value,
            domain=domain,
            officer_name=row.get("Full Name") or row.get("Contact Name"),
            officer_title=row.get("Title") or row.get("Job Title"),
            raw_payload=row,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        return SourceHealth(
            code=self.code, is_healthy=True, status_message="CSV import parser active"
        )
