from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llama_url: Optional[str] = None
    llama_api_key: Optional[str] = None
    pdfact_url: Optional[str] = None
    unstructured_url: Optional[str] = None
    unstructured_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
