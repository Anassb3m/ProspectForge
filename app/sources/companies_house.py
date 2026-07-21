"""Companies House UK Source Adapter Implementation."""

import os
from typing import Any
import httpx
from app.sources.base import (
    NormalizedObservation,
    RawSourceRecord,
    SourceAdapter,
    SourceHealth,
)

COMPANIES_HOUSE_BASE_URL = "https://api.company-information.service.gov.uk"


class CompaniesHouseAdapter(SourceAdapter):
    code: str = "companies_house"
    version: str = "1.0.0"
    country_coverage: list[str] = ["GB"]

    def __init__(self, api_key: str | None = None) -> None:
        raw_key = api_key or os.getenv("COMPANIES_HOUSE_API_KEY", "")
        self.api_key = raw_key.strip()

    async def validate_config(self, config: dict[str, Any]) -> None:
        if not self.api_key and not config.get("allow_mock", True):
            raise ValueError("Companies House API key missing.")

    async def discover(self, query_params: dict[str, Any]) -> list[RawSourceRecord]:
        """Search Companies House by name or company number."""
        query = query_params.get("query", "")
        company_number = query_params.get("company_number", "")
        sic_codes = query_params.get("sic_codes", [])

        if not self.api_key:
            # Fixture mode when API key is not configured
            return [
                RawSourceRecord(
                    connector_code=self.code,
                    external_id=company_number or "12984570",
                    record_type="company",
                    payload={
                        "company_number": company_number or "12984570",
                        "company_name": query or "Apex Commercial Refrigeration & HVAC Ltd",
                        "company_status": "active",
                        "type": "ltd",
                        "date_of_creation": "2018-05-14",
                        "sic_codes": sic_codes or ["43220", "43210"],
                        "registered_office_address": {
                            "address_line_1": "10 Commercial Way",
                            "locality": "Manchester",
                            "postal_code": "M1 2AB",
                            "country": "England",
                        },
                    },
                    source_url=f"https://find-and-update.company-information.service.gov.uk/company/{company_number or '12984570'}",
                )
            ]

        records: list[RawSourceRecord] = []
        async with httpx.AsyncClient(
            auth=(self.api_key, ""), timeout=10.0
        ) as client:
            if company_number:
                resp = await client.get(f"{COMPANIES_HOUSE_BASE_URL}/company/{company_number}")
                if resp.status_code == 200:
                    data = resp.json()
                    records.append(
                        RawSourceRecord(
                            connector_code=self.code,
                            external_id=data.get("company_number", ""),
                            record_type="company",
                            payload=data,
                            source_url=f"https://find-and-update.company-information.service.gov.uk/company/{data.get('company_number')}",
                        )
                    )
            elif query:
                resp = await client.get(
                    f"{COMPANIES_HOUSE_BASE_URL}/search/companies", params={"q": query, "items_per_page": 10}
                )
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        records.append(
                            RawSourceRecord(
                                connector_code=self.code,
                                external_id=item.get("company_number", ""),
                                record_type="company",
                                payload=item,
                                source_url=f"https://find-and-update.company-information.service.gov.uk/company/{item.get('company_number')}",
                            )
                        )
        return records

    def normalize(self, raw_record: RawSourceRecord) -> list[NormalizedObservation]:
        payload = raw_record.payload
        company_number = payload.get("company_number") or raw_record.external_id
        company_name = payload.get("company_name") or payload.get("title", "Unknown Legal Entity")
        sic_codes = payload.get("sic_codes", [])
        address = payload.get("registered_office_address", {})

        obs = NormalizedObservation(
            connector_code=self.code,
            company_name=company_name,
            country_code="GB",
            identifier_scheme="companies_house_number",
            identifier_value=company_number,
            classification_scheme="UK_SIC_2007",
            classification_code=sic_codes[0] if sic_codes else None,
            address={
                "street": address.get("address_line_1"),
                "locality": address.get("locality"),
                "postal_code": address.get("postal_code"),
                "country": address.get("country", "England"),
            },
            raw_payload=payload,
        )
        return [obs]

    async def healthcheck(self) -> SourceHealth:
        if not self.api_key:
            return SourceHealth(
                code=self.code, is_healthy=True, status_message="Running in fixture mode (no API key set)"
            )
        async with httpx.AsyncClient(auth=(self.api_key, ""), timeout=5.0) as client:
            try:
                resp = await client.get(f"{COMPANIES_HOUSE_BASE_URL}/company/00000006")
                return SourceHealth(
                    code=self.code,
                    is_healthy=resp.status_code in (200, 404),
                    status_message=f"HTTP {resp.status_code}",
                )
            except Exception as exc:
                return SourceHealth(code=self.code, is_healthy=False, status_message=str(exc))
