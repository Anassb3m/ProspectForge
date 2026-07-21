"""Base classes and Protocol interface for source adapters."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass
class SourceHealth:
    code: str
    is_healthy: bool
    status_message: str
    last_checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RawSourceRecord:
    connector_code: str
    external_id: str
    record_type: str  # company, officer, contract, job, page
    payload: dict[str, Any]
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: str | None = None


@dataclass
class NormalizedObservation:
    connector_code: str
    company_name: str
    country_code: str
    identifier_scheme: str | None = None
    identifier_value: str | None = None
    classification_scheme: str | None = None
    classification_code: str | None = None
    domain: str | None = None
    address: dict[str, Any] | None = None
    officer_name: str | None = None
    officer_title: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    code: str
    version: str
    country_coverage: list[str]

    async def validate_config(self, config: dict[str, Any]) -> None:
        ...

    async def discover(
        self, query_params: dict[str, Any]
    ) -> list[RawSourceRecord]:
        ...

    def normalize(
        self, raw_record: RawSourceRecord
    ) -> list[NormalizedObservation]:
        ...

    async def healthcheck(self) -> SourceHealth:
        ...
