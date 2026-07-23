from app.services.scoring_v4 import calculate_opportunity_score_v4
from app.models import Opportunity, Company, EvidenceItem, CompanyIdentifier, CompanyDomain

def test_calculate_opportunity_score_v4_basic():
    # Setup dummy models
    company = Company(
        id="c1",
        entity_status="active",
        jurisdiction_code="GB-EW",
        canonical_name="Test Company",
    )
    
    # Needs to be able to access identifiers via relationship mapping in mock or real DB
    company.identifiers = [CompanyIdentifier(scheme="siren", value_normalized="123456789")]
    company.domains = [CompanyDomain(domain_normalized="example.com", domain_role="primary")]
    from app.models import CompanyClassification, CompanyEstimate
    company.classifications = [CompanyClassification(scheme="industry", code="Technology")]
    company.estimates = [CompanyEstimate(estimate_type="headcount", point_estimate=60)]
    
    evidence = [
        EvidenceItem(category="pain"),
        EvidenceItem(category="trigger")
    ]
    
    from datetime import datetime, timezone
    opp = Opportunity(id="o1", company=company, evidence_items=evidence, updated_at=datetime.now(timezone.utc))
    
    # Mock a minimal session object with add method
    class MockSession:
        def add(self, obj):
            pass
        def scalars(self, stmt):
            class MockResult:
                def all(self):
                    return []
            return MockResult()

    session = MockSession()
    
    snapshot = calculate_opportunity_score_v4(session, opp)
    
    # Verify dimensions
    assert snapshot.dimensions_json["icp_fit"] == 90 # 50 + 30 (Tech) + 10 (count > 50)
    assert snapshot.dimensions_json["pain_or_integration_opportunity"] == 40
    assert snapshot.dimensions_json["trigger_strength"] == 30
    assert snapshot.dimensions_json["data_quality"] == 100 # 20 + 30 + 50
    
    assert snapshot.hard_gates_passed is False
    assert opp.outreach_ready is False
    assert opp.latest_score > 0
