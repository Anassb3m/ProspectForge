"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ProspectForge"
    secret_key: str = "change-me"
    debug: bool = False
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./prospectforge.db"
    redis_url: str = "redis://localhost:6379/0"

    access_token_expire_minutes: int = 1440
    admin_email: str = "admin@prospectforge.local"
    admin_password: str = "changeme"

    # Behind reverse proxy (Caddy/nginx)
    trusted_hosts: str = "*"  # comma-separated, e.g. "prospects.example.com,localhost"
    force_https_cookies: bool | None = None  # None = auto from environment
    tls_mode: str = "internal"

    # Legacy (optional)
    hunter_api_key: str = ""

    enable_scheduler: bool = False

    # ── Phase 9: Production Activation Safeguards ─────────────────────────
    outreach_enabled: bool = False
    max_cohort_size: int = 10

    # ── Discovery / enrichment (v2.1) ─────────────────────────────────────
    companies_house_api_key: str = ""  # UK Companies House REST API
    insee_api_key: str = ""  # X-INSEE-Api-Key-Integration
    sirene_delay_seconds: float = 2.1  # stay under 30 req/min

    reacher_url: str = "http://127.0.0.1:8080"
    reacher_enabled: bool = False
    reacher_timeout_seconds: float = 20.0
    contact_reacher_concurrency: int = 2

    harvester_enabled: bool = False
    harvester_sources: str = "duckduckgo,crtsh"

    decp_parquet_url: str = ""  # override auto-discovery from data.gouv.fr
    decp_cache_path: str = "./data/decp_cache.parquet"
    decp_cache_hours: int = 20
    decp_days_back: int = 90
    decp_min_montant: float = 0  # 0 = no minimum
    decp_max_awards: int = 0  # 0 = unlimited after filter
    decp_max_companies: int = 200  # cap nightly upserts
    ingestion_run_contacts: bool = False  # heavy; enable when Reacher is up
    enable_nightly_ingestion: bool = False  # V3: off until live-source validation

    # Contact intelligence limits. Keep these deliberately small in production.
    contact_min_opportunity_score: int = 40
    nightly_contact_batch_size: int = 8
    contact_crawl_max_pages: int = 12
    contact_crawl_max_depth: int = 2
    contact_crawl_max_redirects: int = 4
    contact_crawl_max_response_bytes: int = 2 * 1024 * 1024
    contact_crawl_request_timeout_seconds: float = 10.0
    contact_crawl_total_timeout_seconds: float = 90.0
    contact_domain_concurrency: int = 2
    contact_max_email_candidates: int = 6
    contact_refresh_days: int = 30

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def cookie_secure(self) -> bool:
        if self.force_https_cookies is not None:
            return self.force_https_cookies
        return self.is_production

    @property
    def trusted_host_list(self) -> list[str]:
        if not self.trusted_hosts or self.trusted_hosts.strip() == "*":
            return ["*"]
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    def production_validation_errors(self) -> list[str]:
        """Return unsafe production settings instead of failing silently at runtime."""
        if not self.is_production:
            return []

        errors: list[str] = []
        weak_keys = {
            "change-me",
            "change-me-to-a-long-random-string",
            "dev-secret-key-change-in-production-abc123xyz",
            "CHANGE_ME_long_random_string",
        }
        if self.debug:
            errors.append("DEBUG must be false")
        if self.is_sqlite:
            errors.append("DATABASE_URL must use PostgreSQL")
        if self.secret_key in weak_keys or len(self.secret_key) < 32:
            errors.append("SECRET_KEY must be a unique value of at least 32 characters")
        if self.admin_email.endswith("@prospectforge.local") or "@" not in self.admin_email:
            errors.append("ADMIN_EMAIL must be a real operator email address")
        if self.admin_password in {"changeme", "testpass123", "CHANGE_ME_strong_admin_password"}:
            errors.append("ADMIN_PASSWORD is still a placeholder")
        elif len(self.admin_password) < 14:
            errors.append("ADMIN_PASSWORD must contain at least 14 characters")
        if self.trusted_host_list == ["*"]:
            errors.append("TRUSTED_HOSTS must explicitly list the production domain or IP")
        if not self.cookie_secure:
            errors.append("FORCE_HTTPS_COOKIES must be true in production")
        if self.tls_mode not in {"internal", "external", "acme"}:
            errors.append("TLS_MODE must be internal, external, or acme")
        bounded = {
            "NIGHTLY_CONTACT_BATCH_SIZE": (self.nightly_contact_batch_size, 1, 50),
            "CONTACT_CRAWL_MAX_PAGES": (self.contact_crawl_max_pages, 1, 30),
            "CONTACT_DOMAIN_CONCURRENCY": (self.contact_domain_concurrency, 1, 4),
            "CONTACT_REACHER_CONCURRENCY": (self.contact_reacher_concurrency, 1, 5),
            "CONTACT_MAX_EMAIL_CANDIDATES": (self.contact_max_email_candidates, 1, 12),
        }
        for name, (value, minimum, maximum) in bounded.items():
            if not minimum <= value <= maximum:
                errors.append(f"{name} must be between {minimum} and {maximum}")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
