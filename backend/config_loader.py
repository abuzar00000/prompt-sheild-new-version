from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def load_yaml_settings() -> dict[str, Any]:
    root = project_root()
    path = root / "config" / "settings.yml"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    grok_api_key: str | None = Field(default=None, validation_alias="GROK_API_KEY")
    grok_base_url: str | None = Field(default=None, validation_alias="GROK_BASE_URL")
    grok_model: str | None = Field(default=None, validation_alias="GROK_MODEL")
    grok_api: str | None = Field(default=None, validation_alias="GROK_API")
    grok_store: bool | None = Field(default=None, validation_alias="GROK_STORE")

    rewrite_provider: str | None = Field(default=None, validation_alias="REWRITE_PROVIDER")
    ollama_base_url: str | None = Field(default=None, validation_alias="OLLAMA_BASE_URL")
    ollama_model: str | None = Field(default=None, validation_alias="OLLAMA_MODEL")

    grok_answer_enabled: bool | None = Field(default=None, validation_alias="GROK_ANSWER_ENABLED")

    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_answer_enabled: bool | None = Field(default=None, validation_alias="GEMINI_ANSWER_ENABLED")


def merged_settings() -> dict[str, Any]:
    data = load_yaml_settings()
    env = EnvSettings()
    grok = dict(data.get("grok") or {})
    if env.grok_base_url:
        grok["base_url"] = env.grok_base_url
    if env.grok_model:
        grok["model"] = env.grok_model
    if env.grok_api:
        grok["api"] = env.grok_api
    if env.grok_store is not None:
        grok["store"] = env.grok_store
    data["grok"] = grok
    data["_grok_api_key"] = env.grok_api_key or os.environ.get("GROK_API_KEY")

    rewrite = dict(data.get("rewrite") or {})
    if env.rewrite_provider:
        rewrite["provider"] = env.rewrite_provider.strip().lower()
    data["rewrite"] = rewrite

    ollama = dict(data.get("ollama") or {})
    if env.ollama_base_url:
        ollama["base_url"] = env.ollama_base_url.rstrip("/")
    if env.ollama_model:
        ollama["model"] = env.ollama_model
    data["ollama"] = ollama

    grok_answer = dict(data.get("grok_answer") or {})
    if env.grok_answer_enabled is not None:
        grok_answer["enabled"] = env.grok_answer_enabled
    data["grok_answer"] = grok_answer

    data["_google_api_key"] = (
        env.google_api_key
        or env.gemini_api_key
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )

    gemini_answer = dict(data.get("gemini_answer") or {})
    if env.gemini_answer_enabled is not None:
        gemini_answer["enabled"] = env.gemini_answer_enabled
    data["gemini_answer"] = gemini_answer

    return data
