# Scoring and Readiness Gates

## Current truth

The existing V3 human qualification and suppression tests pass, but the V4
score service is not a certified evidence-bound model. Therefore:

- nightly score reconciliation is off;
- nightly contact discovery is off;
- source ingestion rejects inline contact discovery;
- automatic outreach is unsupported and always off;
- a score alone cannot make a record contact-ready.

## Required activation gates

Before automated contact research:

1. explicit statutory company identity;
2. defensible, evidence-backed domain;
3. current fit/pain/trigger evidence with confidence and expiry;
4. suppression and diffusion checks;
5. calibrated score snapshot with component explanation;
6. minimum opportunity threshold;
7. buyer/contact evidence appropriate to the channel.

Before any outreach:

1. all preceding gates;
2. source-backed contact point, not guessed-domain or SMTP-only identity;
3. human qualification acceptance;
4. human-approved message;
5. informed-at/data-source compliance trail.

No automatic cold-send path is activated by this release.
