from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Prospect, CompanyName, CompanyLocation, CompanyIdentifier

class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_identifier(self, identifier_type: str, value: str) -> Optional[Prospect]:
        stmt = select(CompanyIdentifier).where(
            CompanyIdentifier.identifier_type == identifier_type,
            CompanyIdentifier.value == value
        )
        result = await self.session.execute(stmt)
        ident = result.scalar_one_or_none()
        if not ident:
            return None
        
        prospect_stmt = select(Prospect).where(Prospect.id == ident.prospect_id)
        p_result = await self.session.execute(prospect_stmt)
        return p_result.scalar_one_or_none()

    async def upsert_company(
        self,
        *,
        prospect_id: int,
        name: str,
        siren: Optional[str] = None,
        siret: Optional[str] = None,
        city: Optional[str] = None,
        country: str = "France"
    ) -> None:
        """Upsert core identity records for a prospect."""
        
        # Upsert Name
        stmt = select(CompanyName).where(CompanyName.prospect_id == prospect_id)
        result = await self.session.execute(stmt)
        existing_name = result.scalar_one_or_none()
        if existing_name:
            existing_name.name = name
        else:
            self.session.add(CompanyName(prospect_id=prospect_id, name=name, source="ingestion"))

        # Upsert Identifiers
        if siren:
            stmt = select(CompanyIdentifier).where(
                CompanyIdentifier.prospect_id == prospect_id,
                CompanyIdentifier.identifier_type == "siren"
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                self.session.add(CompanyIdentifier(prospect_id=prospect_id, identifier_type="siren", value=siren))
        
        if siret:
            stmt = select(CompanyIdentifier).where(
                CompanyIdentifier.prospect_id == prospect_id,
                CompanyIdentifier.identifier_type == "siret"
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                self.session.add(CompanyIdentifier(prospect_id=prospect_id, identifier_type="siret", value=siret))

        # Upsert Location
        if city:
            stmt = select(CompanyLocation).where(CompanyLocation.prospect_id == prospect_id)
            result = await self.session.execute(stmt)
            existing_loc = result.scalar_one_or_none()
            if existing_loc:
                existing_loc.city = city
                existing_loc.country = country
            else:
                self.session.add(CompanyLocation(prospect_id=prospect_id, city=city, country=country))
