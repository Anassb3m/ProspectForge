"""Configuration safety gates used by the production entrypoint."""

from app.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "debug": False,
        "database_url": "postgresql+asyncpg://prospectforge:password@db/prospectforge",
        "secret_key": "a" * 64,
        "admin_email": "operator@example.com",
        "admin_password": "a-strong-admin-passphrase",
        "trusted_hosts": "prospects.example.com,127.0.0.1",
        "force_https_cookies": True,
        "tls_mode": "acme",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_safe_production_settings_pass_validation():
    assert _production_settings().production_validation_errors() == []


def test_production_rejects_insecure_defaults():
    settings = _production_settings(
        debug=True,
        database_url="sqlite+aiosqlite:///./prospectforge.db",
        secret_key="change-me",
        admin_email="admin@prospectforge.local",
        admin_password="changeme",
        trusted_hosts="*",
        force_https_cookies=False,
        tls_mode="off",
    )

    errors = settings.production_validation_errors()
    assert len(errors) == 8
    assert any("PostgreSQL" in error for error in errors)
    assert any("TRUSTED_HOSTS" in error for error in errors)
    assert any("HTTPS" in error for error in errors)


def test_non_production_does_not_require_production_secrets():
    settings = Settings(_env_file=None, environment="development")
    assert settings.production_validation_errors() == []
