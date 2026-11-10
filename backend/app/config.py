from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: Literal["development", "test", "uat", "production"] = "development"
    database_url: str = "sqlite:///./mmaug-local.db"
    entra_tenant_id: str = "71beefd7-29f4-4b9e-9cb2-e78b5dc851ad"
    entra_authority_tenant: str = "common"
    entra_api_client_id: str = ""
    entra_required_scope: str = "access_as_user"
    allow_dev_auth: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    password_reset_url: str = "https://passwordreset.microsoftonline.com/"  # noqa: S105
    applicationinsights_connection_string: str = ""
    azure_client_id: str = ""
    azure_ad_client_id: str = ""
    azure_ad_client_secret: SecretStr = SecretStr("")
    azure_ad_tenant_id: str = ""
    azure_ai_project_endpoint: str = ""
    azure_ai_model_deployment_name: str = "gpt-5.4-mini"
    azure_ai_student_agent_id: str = ""
    azure_ai_teacher_agent_id: str = ""
    azure_ai_admin_agent_id: str = ""
    knowledge_base_storage_url: str = ""
    knowledge_base_container: str = "knowledge-base"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def jwks_url(self) -> str:
        return (
            f"https://login.microsoftonline.com/{self.entra_authority_tenant}/discovery/v2.0/keys"
        )

    @property
    def alembic_database_url(self) -> str:
        # Alembic writes the URL through ConfigParser, where percent is interpolation syntax.
        return self.database_url.replace("%", "%%")

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
