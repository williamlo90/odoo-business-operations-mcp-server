from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from psycopg.conninfo import conninfo_to_dict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)
    app_env: Literal["local", "test"] = "local"
    database_url: SecretStr
    session_minutes: int = Field(default=30, ge=1, le=120)
    login_limit: int = Field(default=10, ge=3, le=100)

    @field_validator("database_url")
    @classmethod
    def valid_database(cls, value: SecretStr) -> SecretStr:
        try:
            parts = conninfo_to_dict(value.get_secret_value())
            if not all(parts.get(key) for key in ("host", "dbname", "user", "password")):
                raise ValueError()
        except Exception:
            raise ValueError("A complete PostgreSQL connection URL is required") from None
        return value


settings = Settings()
