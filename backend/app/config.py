from pydantic_settings import BaseSettings
from typing import List
import json

_PLACEHOLDER_KEYS = {
    "dev_secret_change_in_production",
    "change_me_to_a_random_secret_key_32chars",
}

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://algomaster:algomaster_secret@db:5432/algomaster"
    CODE_RUNNER_URL: str = "http://code-runner:5000"
    # REDIS_URL removed — Redis is not used in this application
    SECRET_KEY: str = "dev_secret_change_in_production"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ENVIRONMENT: str = "development"
    BACKEND_CORS_ORIGINS: str = '["http://localhost","http://localhost:5173","http://localhost:3000"]'

    @property
    def cors_origins(self) -> List[str]:
        return json.loads(self.BACKEND_CORS_ORIGINS)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

if settings.SECRET_KEY in _PLACEHOLDER_KEYS:
    raise RuntimeError(
        "SECRET_KEY is still set to the default placeholder. "
        "Generate a real key with: python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and set it in your .env file."
    )
