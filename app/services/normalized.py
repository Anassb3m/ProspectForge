import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Company,
    CompanyClassification,
    CompanyIdentifier,
    CompanyDomain,
    CompanyLocation,
    Opportunity,
    MarketPlayVersion,
    SourceRecord
)
import logging

logger = logging.getLogger(__name__)

async def upsert_normalized_company(
    session: AsyncSession,
    company_name: str,
    siren: Optional[str] = None,
    siret: Optional[str] = None,
    website: Optional[str] = None,
    city: Optional[str] = None,
    department: Optional[str] = None,
    source_run_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    play_code: str = "DEFAULT"
) -> Opportunity:
    # Identity joins use official identifiers only. Names and inferred domains
    # are descriptive attributes, never entity keys.
    siren = "".join(char for char in str(siren or "") if char.isdigit()) or None
    siret = "".join(char for char in str(siret or "") if char.isdigit()) or None
    if siren and len(siren) != 9:
        raise ValueError("FR SIREN must contain exactly 9 digits")
    if siret and len(siret) != 14:
        raise ValueError("FR SIRET must contain exactly 14 digits")
    if siren and siret and not siret.startswith(siren):
        raise ValueError("FR SIREN/SIRET identity contradiction")

    company_by_siret = None
    company_by_siren = None
    if siret:
        result = await session.execute(
            select(Company).join(CompanyIdentifier).where(
                CompanyIdentifier.scheme == "FR_SIRET",
                CompanyIdentifier.value_normalized == siret
            )
        )
        company_by_siret = result.scalars().first()
    if siren:
        result = await session.execute(
            select(Company).join(CompanyIdentifier).where(
                CompanyIdentifier.scheme == "FR_SIREN",
                CompanyIdentifier.value_normalized == siren
            )
        )
        company_by_siren = result.scalars().first()
    if (
        company_by_siret is not None
        and company_by_siren is not None
        and company_by_siret.id != company_by_siren.id
    ):
        company_by_siret.identity_review_state = "severe_contradiction"
        company_by_siren.identity_review_state = "severe_contradiction"
        raise ValueError("SIREN and SIRET resolve to different canonical companies")
    company = company_by_siret or company_by_siren

    if not company:
        company = Company(
            canonical_name=company_name,
            legal_name=company_name,
            country_code="FR",
            jurisdiction_code="FR",
            entity_status=(
                "inactive"
                if str((payload or {}).get("etat_administratif") or "").upper()
                in {"F", "INACTIVE", "FERME"}
                else "active"
            ),
        )
        session.add(company)
        await session.flush()
        
        if siren:
            session.add(CompanyIdentifier(
                company_id=company.id,
                scheme="FR_SIREN",
                value_normalized=siren,
                value_display=siren,
                is_primary=True,
                verified_at=datetime.now(timezone.utc),
            ))
        if siret:
            session.add(CompanyIdentifier(
                company_id=company.id,
                scheme="FR_SIRET",
                value_normalized=siret,
                value_display=siret,
                is_primary=False,
                verified_at=datetime.now(timezone.utc),
            ))
    else:
        identifiers = {
            (identifier.scheme, identifier.value_normalized)
            for identifier in (
                await session.scalars(
                    select(CompanyIdentifier).where(
                        CompanyIdentifier.company_id == company.id
                    )
                )
            ).all()
        }
        for scheme, value, primary in (
            ("FR_SIREN", siren, True),
            ("FR_SIRET", siret, False),
        ):
            if value and (scheme, value) not in identifiers:
                session.add(
                    CompanyIdentifier(
                        company_id=company.id,
                        scheme=scheme,
                        value_normalized=value,
                        value_display=value,
                        is_primary=primary,
                        verified_at=datetime.now(timezone.utc),
                    )
                )

    naf_code = str((payload or {}).get("naf_code") or "").upper().replace(".", "")
    if naf_code:
        classification = await session.scalar(
            select(CompanyClassification).where(
                CompanyClassification.company_id == company.id,
                CompanyClassification.scheme == "FR_NAF_REV2",
                CompanyClassification.code == naf_code,
            )
        )
        if classification is None:
            session.add(
                CompanyClassification(
                    company_id=company.id,
                    scheme="FR_NAF_REV2",
                    code=naf_code,
                    is_primary=True,
                )
            )

    # Add domain if provided
    if website:
        parsed = urlparse(website if "://" in website else f"https://{website}")
        domain_norm = (parsed.hostname or "").lower().removeprefix("www.")
        if not domain_norm:
            raise ValueError("Website did not contain a valid hostname")
        result = await session.execute(
            select(CompanyDomain).where(
                CompanyDomain.company_id == company.id,
                CompanyDomain.domain_normalized == domain_norm
            )
        )
        if not result.scalars().first():
            session.add(CompanyDomain(
                company_id=company.id,
                domain_normalized=domain_norm,
                domain_role="primary",
                verification_state=str(
                    (payload or {}).get("website_verification_state") or "candidate"
                ),
                match_reasons_json={
                    "source": (payload or {}).get("website_source") or "unspecified",
                    "warning": "candidate domains are not verified identity",
                },
            ))

    # Add location
    if city or department:
        result = await session.execute(
            select(CompanyLocation).where(
                CompanyLocation.company_id == company.id,
                CompanyLocation.postal_code == department
            )
        )
        if not result.scalars().first():
            session.add(CompanyLocation(
                company_id=company.id,
                location_type="registered",
                locality=city,
                postal_code=department,
                country_code="FR"
            ))

    # Add SourceRecord
    if source_run_id:
        raw_payload = payload or {}
        source_record = SourceRecord(
            source_run_id=source_run_id,
            external_id=siret or siren,
            payload_json=raw_payload,
            payload_hash=hashlib.sha256(
                json.dumps(raw_payload, default=str, sort_keys=True).encode()
            ).hexdigest(),
            processing_status="legacy",
            processing_result="normalized",
        )
        session.add(source_record)

    # Add or update Opportunity
    result = await session.execute(select(MarketPlayVersion).where(MarketPlayVersion.play_code == play_code).limit(1))
    play = result.scalars().first()
    if not play:
        play = MarketPlayVersion(play_code=play_code, version="1.0.0", status="active")
        session.add(play)
        await session.flush()

    result = await session.execute(
        select(Opportunity).where(
            Opportunity.company_id == company.id,
            Opportunity.play_version_id == play.id
        )
    )
    opp = result.scalars().first()
    if not opp:
        opp = Opportunity(
            company_id=company.id,
            play_version_id=play.id,
            status="discovered",
            priority="Medium",
            latest_score=0.0,
            readiness_state="NORMALIZED",
            outreach_ready=False,
        )
        session.add(opp)

    await session.flush()
    return opp
