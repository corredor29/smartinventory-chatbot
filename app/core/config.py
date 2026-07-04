from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Entorno
    app_env: str = "development"
    app_name: str = "SmartInventory-Chatbot"
    debug: bool = True
    log_level: str = "INFO"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Conexión con la API .NET
    dotnet_api_base_url: str = "https://localhost:5001/api"
    dotnet_api_timeout: int = 30
    dotnet_service_api_key: str = ""
    dotnet_max_retries: int = 3
    dotnet_retry_backoff_seconds: float = 0.5

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Sesión
    session_store: str = "memory"
    session_ttl_seconds: int = 3600
    session_cleanup_interval_seconds: int = 300

    # Grafo
    graph_timeout_seconds: int = 60

    # CORS (uno o más orígenes separados por coma)
    allowed_origins: str = "https://localhost:5001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _validate_production_requirements(self) -> "Settings":
        if self.app_env == "production":
            missing = [
                name
                for name, value in (
                    ("openai_api_key", self.openai_api_key),
                    ("dotnet_api_base_url", self.dotnet_api_base_url),
                    ("dotnet_service_api_key", self.dotnet_service_api_key),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "Faltan variables de entorno obligatorias en producción: "
                    + ", ".join(missing)
                )
        return self


settings = Settings()
