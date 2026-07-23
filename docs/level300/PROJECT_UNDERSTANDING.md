# Project Understanding

ProspectForge is an internal acquisition operating system for Anass/Elevya. Its core mission is to construct a substantial, reliable company universe (10,000+ distinct raw official company entities) and distill it into evidence-backed opportunities, identify correct buyers, and defensible contact paths.

The target is to convert the best opportunities into high-quality conversations for custom field-operations systems, integrations, and operational software.

## Funnel Target
- 10,000+ raw official company entities
- 2,000–5,000 ICP candidates
- 1,000–3,000 domain-resolved companies
- 500–1,500 evidence-enriched opportunities
- 200–800 buyer-identified opportunities
- 50–250 review-ready opportunities per active cycle
- 20–50 outreach-ready opportunities per week

## Core Principles
1. **Durable Architecture**: All long-running tasks must be processed by robust queue systems (Celery) with check-pointing, retry mechanisms, and rate limits.
2. **Normalized Data**: Eradicate the flat `Prospect` table reliance. Instead, leverage normalized relations: `Company`, `CompanyIdentifier`, `Opportunity`, `EvidenceItem`, `Person`, etc.
3. **No Fabrication**: Zero generation of "fake" data (e.g. defaulting to fixtures when API keys are missing).
4. **Evidence-Backed**: Every contact claim and score must link to concrete, fetched evidence. No guessing.
