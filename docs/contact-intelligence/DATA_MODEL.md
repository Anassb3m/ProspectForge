# Data model

The normalized tables are authoritative. Existing fields on `prospects` are compatibility projections.

```text
prospects
├── contact_people
│   ├── contact_points
│   ├── contact_evidence
│   └── contact_manual_reviews
├── contact_points
│   ├── contact_evidence
│   ├── contact_verification_events
│   └── contact_manual_reviews
└── contact_discovery_runs
```

## Integrity rules

- Person uniqueness: prospect + normalized name + normalized role.
- Contact-point uniqueness: prospect + kind + normalized value.
- Evidence uniqueness: stable SHA-256 fingerprint of prospect, adapter, source, fact, subject, and content hash.
- Manual confirmations and rejections are not overwritten by automated merges.
- Foreign keys use cascade for prospect-owned records and `SET NULL` for evidence/reviews that should remain intelligible when a point/person is removed.
- Database checks constrain the critical role, match, publication, deliverability, kind, and utility states.

## Compatibility projection

- `decision_maker_name/title`: selected primary person.
- `linkedin_url`: official publication or manual confirmation only.
- `phone`: selected public business phone.
- `email`: usable published/manual or strongly pattern-confirmed path only; name-only guesses are never projected.
- `contact_source`, `contact_confidence`, `contact_discovery_state`: derived from the selected point.
- `contact_candidates`: bounded ten-row compatibility summary.

Migration revision: `pfci60_20260720`, down revision `005`. Production reportedly has a different unshared revision; reconcile before deployment.
