#!/usr/bin/env bash
# Restore an optional production backup into an isolated disposable database,
# migrate it, anonymize personal contact fields, and reconcile canonical truth.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
DUMP_FILE="${1:-}"
RUN_ID="$(date -u +%Y%m%d%H%M%S)_$$"
REHEARSAL_DB="prospectforge_production_rehearsal_${RUN_ID}"
TEST_DB_USER="prospectforge_test"
TEST_DB_PORT="${TEST_DB_PORT:-55439}"
DATABASE_URL="postgresql+asyncpg://${TEST_DB_USER}:test-only-password@127.0.0.1:${TEST_DB_PORT}/${REHEARSAL_DB}"
CREATED=0

compose() {
  POSTGRES_PASSWORD=test-unused docker compose --profile test "$@"
}

cleanup() {
  status=$?
  if [[ "$CREATED" -eq 1 ]]; then
    compose exec -T test-db dropdb --if-exists -U "$TEST_DB_USER" "$REHEARSAL_DB" \
      >/dev/null 2>&1 || true
  fi
  return "$status"
}
trap cleanup EXIT

if [[ -n "$DUMP_FILE" ]]; then
  [[ -f "$DUMP_FILE" ]] || {
    echo "ERROR: production-copy dump not found: $DUMP_FILE" >&2
    exit 2
  }
  case "$DUMP_FILE" in
    *.sql.gz) ;;
    *) echo "ERROR: expected an integrity-checked .sql.gz backup" >&2; exit 2 ;;
  esac
  gzip -t "$DUMP_FILE"
  echo "Backup SHA-256: $(sha256sum "$DUMP_FILE" | cut -d' ' -f1)"
else
  echo "No production-copy dump supplied; running the deterministic production-shaped fixture rehearsal."
fi

compose up -d test-db test-redis
for _ in $(seq 1 30); do
  if compose exec -T test-db pg_isready -U "$TEST_DB_USER" -d prospectforge_test \
    >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
compose exec -T test-db createdb -U "$TEST_DB_USER" "$REHEARSAL_DB"
CREATED=1

if [[ -n "$DUMP_FILE" ]]; then
  gzip -dc "$DUMP_FILE" | compose exec -T test-db \
    psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" -d "$REHEARSAL_DB"
else
  DEBUG=false ENVIRONMENT=test DATABASE_URL="$DATABASE_URL" \
    "$PYTHON_BIN" -m alembic upgrade pfscale02_20260731
  DEBUG=false ENVIRONMENT=test DATABASE_URL="$DATABASE_URL" \
    "$PYTHON_BIN" scripts/seed_canonical_backfill_rehearsal.py
fi

DEBUG=false ENVIRONMENT=test "$PYTHON_BIN" scripts/verify-production-shaped-migration.py \
  --db-url "$DATABASE_URL"

if [[ -z "$DUMP_FILE" ]]; then
  DEBUG=false ENVIRONMENT=test DATABASE_URL="$DATABASE_URL" \
    "$PYTHON_BIN" scripts/seed_production_shape.py
fi

# The database is isolated and disposable, but scrub contact/person fields
# before any diagnostic query or optional KEEP_REHEARSAL_DB workflow is added.
compose exec -T test-db psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" \
  -d "$REHEARSAL_DB" <<'SQL'
UPDATE prospects
SET company_name = 'Rehearsal Company ' || id,
    email = CASE WHEN email IS NULL THEN NULL ELSE 'prospect-' || id || '@example.invalid' END,
    phone = CASE WHEN phone IS NULL THEN NULL ELSE '+33000000000' END,
    decision_maker_name = CASE WHEN decision_maker_name IS NULL THEN NULL ELSE 'Rehearsal Person ' || id END,
    linkedin_url = NULL,
    qualification_notes = NULL,
    personalization_brief = NULL,
    notes = NULL;

UPDATE companies
SET canonical_name = 'Rehearsal Company ' || id,
    legal_name = CASE WHEN legal_name IS NULL THEN NULL ELSE 'Rehearsal Legal ' || id END;

UPDATE users
SET email = 'rehearsal-user-' || id || '@example.invalid',
    hashed_password = '!rehearsal-login-disabled!';

UPDATE contact_people
SET full_name = 'Rehearsal Contact ' || id,
    normalized_name = 'rehearsal contact ' || id,
    first_name = 'Rehearsal',
    last_name = 'Contact ' || id,
    linkedin_url = NULL;

UPDATE people
SET first_name = 'Rehearsal',
    last_name = 'Person ' || id,
    full_name = 'Rehearsal Person ' || id,
    linkedin_url = NULL;

UPDATE contact_points
SET value_normalized = CASE
      WHEN kind = 'email' THEN 'contact-' || id || '@example.invalid'
      WHEN kind = 'phone' THEN '+3300' || lpad(id::text, 7, '0')
      ELSE 'https://example.invalid/contact/' || id
    END,
    value_display = CASE
      WHEN kind = 'email' THEN 'contact-' || id || '@example.invalid'
      WHEN kind = 'phone' THEN '+3300' || lpad(id::text, 7, '0')
      ELSE 'https://example.invalid/contact/' || id
    END,
    domain = CASE WHEN kind = 'phone' THEN NULL ELSE 'example.invalid' END;

UPDATE qualification_reviews SET notes = NULL;
UPDATE qualification_reviews
SET reviewer_email = CASE
  WHEN reviewer_email IS NULL THEN NULL
  ELSE 'reviewer-' || id || '@example.invalid'
END;
UPDATE tasks SET title = 'Rehearsal task ' || id, notes = NULL;
UPDATE outreach_events
SET notes = NULL, personalization_summary = NULL, next_action = NULL;
UPDATE contact_manual_reviews
SET reviewer = 'Rehearsal reviewer ' || id, reason = NULL, evidence_url = NULL;
UPDATE contact_evidence
SET excerpt = NULL, source_url = NULL, canonical_url = NULL;
UPDATE touches SET subject = NULL, body = NULL, evidence_citations_json = NULL;
UPDATE suppression_entries
SET value_normalized = 'rehearsal-suppression-' || id,
    reason = NULL;

-- Recursively redact sensitive values inside every JSON/JSONB envelope while
-- preserving object keys, array sizes, numbers, booleans, and nulls.
CREATE OR REPLACE FUNCTION pg_temp.rehearsal_redact_json(value jsonb)
RETURNS jsonb
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  result jsonb;
BEGIN
  CASE jsonb_typeof(value)
    WHEN 'object' THEN
      SELECT jsonb_object_agg(
        key,
        CASE
          WHEN key ~* '(name|email|phone|mobile|tel|contact|person|dirigeant|representant|president|gerant|message|body|subject|note|comment|token|secret|password|linkedin|url|address|adresse|street|prenom|nom)'
            THEN CASE jsonb_typeof(item)
              WHEN 'array' THEN (
                SELECT coalesce(jsonb_agg('"<redacted>"'::jsonb), '[]'::jsonb)
                FROM jsonb_array_elements(item)
              )
              WHEN 'object' THEN pg_temp.rehearsal_redact_json(item)
              ELSE '"<redacted>"'::jsonb
            END
          ELSE pg_temp.rehearsal_redact_json(item)
        END
      ) INTO result
      FROM jsonb_each(value) AS fields(key, item);
      RETURN coalesce(result, '{}'::jsonb);
    WHEN 'array' THEN
      SELECT jsonb_agg(pg_temp.rehearsal_redact_json(item)) INTO result
      FROM jsonb_array_elements(value) AS elements(item);
      RETURN coalesce(result, '[]'::jsonb);
    ELSE
      RETURN value;
  END CASE;
END;
$$;

DO $$
DECLARE
  column_row record;
BEGIN
  FOR column_row IN
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND data_type IN ('json', 'jsonb')
  LOOP
    EXECUTE format(
      'UPDATE %I SET %I = pg_temp.rehearsal_redact_json(%I::jsonb)::%s WHERE %I IS NOT NULL',
      column_row.table_name,
      column_row.column_name,
      column_row.column_name,
      column_row.data_type,
      column_row.column_name
    );
  END LOOP;
END;
$$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM users
    WHERE email NOT LIKE '%@example.invalid'
       OR hashed_password <> '!rehearsal-login-disabled!'
  ) OR EXISTS (
    SELECT 1 FROM prospects
    WHERE email IS NOT NULL AND email NOT LIKE '%@example.invalid'
  ) OR EXISTS (
    SELECT 1 FROM contact_points
    WHERE kind = 'email' AND value_normalized NOT LIKE '%@example.invalid'
  ) OR EXISTS (
    SELECT 1 FROM touches WHERE subject IS NOT NULL OR body IS NOT NULL
  ) OR EXISTS (
    SELECT 1 FROM prospects
    WHERE notes IS NOT NULL OR qualification_notes IS NOT NULL
  ) THEN
    RAISE EXCEPTION 'rehearsal anonymization assertion failed';
  END IF;
END;
$$;

SELECT
  (SELECT count(*) FROM users) AS users_anonymized,
  (SELECT count(*) FROM prospects WHERE email LIKE '%@example.invalid') AS prospect_emails_anonymized,
  (SELECT count(*) FROM contact_points WHERE kind = 'email' AND value_normalized LIKE '%@example.invalid') AS contact_emails_anonymized,
  (SELECT count(*) FROM touches WHERE subject IS NULL AND body IS NULL) AS message_bodies_scrubbed;
SQL

DEBUG=false ENVIRONMENT=test DATABASE_URL="$DATABASE_URL" \
  "$PYTHON_BIN" scripts/reconcile_reliability.py --fail-on-anomaly

compose exec -T test-db psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" \
  -d "$REHEARSAL_DB" -c \
  "SELECT (SELECT count(*) FROM companies) AS companies,
          (SELECT count(*) FROM opportunities) AS opportunities,
          (SELECT count(*) FROM prospects) AS prospects,
          (SELECT version_num FROM alembic_version) AS revision;"

echo "Production migration rehearsal passed; disposable database will now be removed."
