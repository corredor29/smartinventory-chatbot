from pydantic_settings import BaseSettings


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

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Sesión
    session_store: str = "memory"

    # CORS
    allowed_origins: str = "https://localhost:5001"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()