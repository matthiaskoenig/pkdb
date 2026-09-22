"""Explicit storage configuration and bounded ingestion resource settings."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PKDB_", extra="forbid")

    @field_validator("cors_origins")
    @classmethod
    def explicit_cors_origins(cls, origins):
        if any("*" in origin for origin in origins):
            raise ValueError("Credentialed CORS requires explicit origins")
        return origins

    database_url: str
    file_root: Path
    cors_origins: list[str] = Field(default_factory=list)
    browser_origin: str = "http://localhost:8080"
    secure_cookies: bool = False
    mfa_encryption_key: SecretStr | None = None
    github_client_id: str = ""
    github_client_secret: SecretStr | None = None
    orcid_client_id: str = ""
    orcid_client_secret: SecretStr | None = None
    rate_limits_enabled: bool = True
    quota_anonymous_per_minute: int = Field(default=30, gt=0)
    quota_account_per_minute: int = Field(default=120, gt=0)
    quota_key_per_minute: int = Field(default=60, gt=0)
    quota_ip_per_minute: int = Field(default=600, gt=0)
    quota_uploads_per_hour: int = Field(default=10, gt=0)
    quota_exports_per_minute: int = Field(default=10, gt=0)
    quota_account_concurrency: int = Field(default=6, gt=0)
    quota_anonymous_concurrency: int = Field(default=2, gt=0)
    upload_max_bytes: int = Field(default=256 * 1024 * 1024, gt=0)
    upload_max_files: int = Field(default=256, gt=0)
    upload_max_rows: int = Field(default=1_000_000, gt=0)
    upload_concurrency: int = Field(default=2, gt=0)

    export_max_bytes: int = Field(default=256 * 1024 * 1024, gt=0)
    export_max_rows: int = Field(default=1_000_000, gt=0)
    export_concurrency: int = Field(default=2, gt=0)

    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_sender: str | None = None
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
