"""Explicit storage configuration and bounded ingestion resource settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PKDB_", extra="forbid")

    database_url: str
    file_root: Path
    upload_max_bytes: int = Field(default=256 * 1024 * 1024, gt=0)
    upload_max_files: int = Field(default=256, gt=0)
    upload_max_rows: int = Field(default=1_000_000, gt=0)
    upload_concurrency: int = Field(default=2, gt=0)
