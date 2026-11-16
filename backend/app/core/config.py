from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Manicure Dashboard"
    API_V1_STR: str = "/api"

    # Environment
    APP_ENV: Literal["development", "production"] = "development"
    DEMO_MODE: bool = False
    DEMO_OWNER_PASSWORD: str | None = None

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "manicure_db"
    DATABASE_URL: str | None = None
    TEST_DATABASE_URL: str | None = None

    # Auth & JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30
    COOKIE_SECURE: bool | None = None
    COOKIE_SAMESITE: str = "lax"
    COOKIE_NAME: str = "access_token"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        forbidden = ["change_me", "changeme", "replace_me", "your_secret_here"]
        v_lower = v.lower()
        for pattern in forbidden:
            if pattern in v_lower:
                raise ValueError(f"JWT_SECRET_KEY cannot contain template value '{pattern}'")
        return v

    @model_validator(mode="after")
    def validate_cookie_secure_and_env(self) -> "Settings":
        if self.APP_ENV == "production":
            if self.COOKIE_SECURE is False:
                raise ValueError("COOKIE_SECURE cannot be false in production")
            self.COOKIE_SECURE = True
        else:
            if self.COOKIE_SECURE is None:
                self.COOKIE_SECURE = False
        return self

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_test_database_url(self) -> str:
        if self.TEST_DATABASE_URL:
            url = self.TEST_DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/manicure_test_db"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
