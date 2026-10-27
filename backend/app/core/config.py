"""Configuración centralizada. Ningún secreto vive en el código: todo viene del entorno / .env."""

from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Aplicación ──
    app_name: str = "Catalogos SaaS API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    # "a,b,c" en el .env → ['a','b','c'] (NoDecode evita que pydantic-settings exija JSON)
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)
    privacy_policy_version: str = "2026-10-27-v2"

    # ── Base de datos ──
    database_url: SecretStr
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_timeout: int = Field(default=30, ge=1)
    db_echo: bool = False
    db_behind_pooler: bool = True
    db_require_ssl: bool = True

    # ── Supabase ──
    supabase_url: AnyHttpUrl
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "product-images"

    # ── Suscripciones y avisos (proveedores opcionales hasta configurar credenciales) ──
    billing_grace_days: int = Field(default=2, ge=0, le=7)
    billing_trial_days: int = Field(default=6, ge=1, le=30)
    billing_monthly_price_cop: int = Field(default=15000, ge=0)
    billing_extra_catalog_price_cop: int = Field(default=5000, ge=0)
    billing_whatsapp_number: str | None = None
    app_timezone: str = "America/Bogota"
    max_product_image_bytes: int = Field(default=2_097_152, ge=1024, le=10_485_760)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_use_ssl: bool = False
    whatsapp_access_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_template_name: str | None = None
    whatsapp_order_template_name: str | None = None
    whatsapp_template_language: str = "es_CO"
    whatsapp_graph_api_version: str | None = None

    # ── Reglas de negocio ──
    max_products_per_store: int = Field(default=50, ge=1)

    # ── Validadores ──
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _force_asyncpg_driver(cls, value: Any) -> Any:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        for prefix in ("postgresql://", "postgres://"):
            if raw.startswith(prefix):
                raw = "postgresql+asyncpg://" + raw[len(prefix) :]
        if not raw.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL debe ser una URL de PostgreSQL")
        return raw

    @field_validator("supabase_jwt_secret", "supabase_service_role_key", "smtp_password", "whatsapp_access_token", mode="before")
    @classmethod
    def _empty_to_none(cls, value: Any) -> Any:
        return None if value in ("", None) else value

    @field_validator("admin_emails", mode="before")
    @classmethod
    def _normalize_admin_emails(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [email.strip().lower() for email in value.split(",") if email.strip()]
        if isinstance(value, list):
            return [email.strip().lower() for email in value if isinstance(email, str) and email.strip()]
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG debe ser false en producción")
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS debe incluir el origen HTTPS del frontend en producción")
            for origin in self.cors_origins:
                parsed = urlsplit(origin)
                if (
                    "*" in origin
                    or parsed.scheme != "https"
                    or not parsed.netloc
                    or parsed.path not in ("", "/")
                    or parsed.query
                    or parsed.fragment
                    or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                ):
                    raise ValueError("En producción, cada CORS_ORIGINS debe ser un origen HTTPS exacto del frontend")
        return self

    # ── Derivados ──
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def supabase_base_url(self) -> str:
        return str(self.supabase_url).rstrip("/")

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_base_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # los campos requeridos vienen del entorno
