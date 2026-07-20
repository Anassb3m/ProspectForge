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

    # ── Discovery / enrichment (v2.1) ─────────────────────────────────────
    insee_api_key: str = ""  # X-INSEE-Api-Key-Integration
    sirene_delay_seconds: float = 2.1  # stay under 30 req/min

    reacher_url: str = "http://127.0.0.1:8080"
    reacher_enabled: bool = False

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
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
