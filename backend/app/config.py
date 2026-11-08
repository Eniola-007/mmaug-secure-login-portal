from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: Literal["development", "test", "uat", "production"] = "development"
    database_url: str = "sqlite:///./mmaug-local.db"
    entra_tenant_id: str = "71beefd7-29f4-4b9e-9cb2-e78b5dc851ad"
    entra_api_client_id: str = ""
    entra_required_scope: str = "access_as_user"
    allow_dev_auth: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    password_reset_url: str = "https://passwordreset.microsoftonline.com/"  # noqa: S105
    applicationinsights_connection_string: str = ""
    azure_ai_project_endpoint: str = ""
    azure_ai_student_agent_id: str = ""
    azure_ai_teacher_agent_id: str = ""
    azure_ai_admin_agent_id: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"

    def validate_security_mode(self) -> None:
        if self.environment in {"uat", "production"} and self.allow_dev_auth:
            raise RuntimeError("ALLOW_DEV_AUTH must never be enabled in UAT or production")
        if self.environment in {"uat", "production"} and not self.entra_api_client_id:
            raise RuntimeError("ENTRA_API_CLIENT_ID is required in UAT and production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_security_mode()
    return settings
