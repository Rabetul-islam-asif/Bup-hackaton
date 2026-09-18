"""Configuration settings for GridWise service."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    nvidia_model: str = Field(
        default="meta/llama-3.2-11b-vision-instruct", alias="NVIDIA_MODEL"
    )
    nvidia_api_url: str = Field(
        default="https://integrate.api.nvidia.com/v1/chat/completions",
        alias="NVIDIA_API_URL",
    )
    llm_timeout_seconds: float = Field(default=22.0, alias="LLM_TIMEOUT_SECONDS")
    total_request_deadline_seconds: float = Field(
        default=27.0, alias="TOTAL_REQUEST_DEADLINE_SECONDS"
    )
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    def is_llm_configured(self) -> bool:
        return bool(self.nvidia_api_key and self.nvidia_api_key.strip())

    def sanitized_dict(self) -> dict[str, str | float | int]:
        return {
            "nvidia_model": self.nvidia_model,
            "nvidia_api_url": self.nvidia_api_url,
            "llm_timeout_seconds": self.llm_timeout_seconds,
            "total_request_deadline_seconds": self.total_request_deadline_seconds,
            "host": self.host,
            "port": self.port,
            "nvidia_api_key_configured": self.is_llm_configured(),
        }


# Global singleton settings
settings = Settings()
