# ProspectForge production image
FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="ProspectForge" \
      org.opencontainers.image.source="https://github.com/Anassb3m/ProspectForge"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --shell /usr/sbin/nologin --create-home app

# Install package
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts/entrypoint.sh /entrypoint.sh

RUN pip install --no-cache-dir . \
    && chmod +x /entrypoint.sh \
    && mkdir -p /app/data /app/backups \
    && chown -R app:app /app /entrypoint.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
