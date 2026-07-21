"""Source Adapter Registry and Interface Factory."""

from typing import Any
from app.sources.base import SourceAdapter
from app.sources.companies_house import CompaniesHouseAdapter
from app.sources.csv_import import CsvImportAdapter
from app.sources.decp_adapter import DecpAdapter
from app.sources.manual import ManualResearchAdapter
from app.sources.sirene_adapter import SireneAdapter

SOURCE_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "companies_house": CompaniesHouseAdapter,
    "sirene": SireneAdapter,
    "decp": DecpAdapter,
    "csv_import": CsvImportAdapter,
    "manual": ManualResearchAdapter,
}


def get_source_adapter(code: str, **kwargs: Any) -> SourceAdapter:
    """Retrieve initialized source adapter instance by code."""
    if code not in SOURCE_ADAPTERS:
        raise KeyError(f"Unknown source adapter: {code}")
    adapter_cls = SOURCE_ADAPTERS[code]
    return adapter_cls(**kwargs)


__all__ = [
    "SourceAdapter",
    "CompaniesHouseAdapter",
    "SireneAdapter",
    "DecpAdapter",
    "CsvImportAdapter",
    "ManualResearchAdapter",
    "SOURCE_ADAPTERS",
    "get_source_adapter",
]
