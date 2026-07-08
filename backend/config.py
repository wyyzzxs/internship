import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DASHCOPE_API_KEY: str = ""
    AMAP_JS_API_KEY: str = ""
    HEFENG_KEY: str = ""
    USE_MOCK: bool = True
    DATABASE_URL: str = "sqlite:///./sessions.db"

    # Use pydantic-settings config to read .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
