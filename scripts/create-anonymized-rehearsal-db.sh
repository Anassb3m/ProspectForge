#!/usr/bin/env bash
set -eo pipefail

# Scripts to create an anonymized rehearsal database.
# Usage: ./scripts/create-anonymized-rehearsal-db.sh [path_to_production_dump.sql.gz]

DUMP_FILE=$1
DB_CONTAINER="prospectforge-test-db-1"
DB_USER="prospectforge_test"
DB_NAME="prospectforge_rehearsal"

echo "Starting isolated PostgreSQL for rehearsal..."
docker compose --profile test up -d test-db

echo "Waiting for PostgreSQL to be ready..."
until docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d prospectforge_test; do
  sleep 1
done

echo "Recreating rehearsal database..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d prospectforge_test -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d prospectforge_test -c "CREATE DATABASE $DB_NAME;"

if [ -n "$DUMP_FILE" ] && [ -f "$DUMP_FILE" ]; then
    echo "Restoring production dump into rehearsal database..."
    zcat "$DUMP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"
else
    echo "No dump file provided. Seeding rehearsal database with production-shaped fixture..."
    export DATABASE_URL="postgresql+asyncpg://${DB_USER}:test-only-password@127.0.0.1:55439/${DB_NAME}"
    .venv/bin/alembic upgrade head
    .venv/bin/python scripts/seed_production_shape.py
fi

echo "Anonymizing personal and sensitive data..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    -- Anonymize Prospect emails and phones
    UPDATE prospects SET 
        email = CONCAT('user_', id, '@example.com'),
        phone = '+33000000000',
        decision_maker_name = CONCAT('Person ', id)
    WHERE email IS NOT NULL OR phone IS NOT NULL OR decision_maker_name IS NOT NULL;
    
    -- Anonymize Persons
    UPDATE persons SET 
        first_name = CONCAT('First', id),
        last_name = CONCAT('Last', id),
        linkedin_url = NULL;

    -- Anonymize ContactPoints
    UPDATE contact_points SET 
        value = CONCAT('contact_', id, '@example.com')
    WHERE channel = 'email';
    
    UPDATE contact_points SET 
        value = '+33000000000'
    WHERE channel = 'phone';
    
    -- Clear message drafts and sensitive notes
    UPDATE qualification_reviews SET notes = 'Anonymized note';
    UPDATE outreach_events SET notes = 'Anonymized note', content = 'Anonymized content';
"

echo "Anonymized rehearsal database $DB_NAME is ready."
