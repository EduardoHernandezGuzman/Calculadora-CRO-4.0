from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

if not settings.openai_api_key:
    settings.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
