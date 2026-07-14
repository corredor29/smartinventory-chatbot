from pydantic import model_validator # Decorador de validación de modelos Pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict # BaseSettings permite cargar variables automáticamente desde .env


class Settings(BaseSettings):
    # Entorno
    app_env: str = "development"  # Ambiente actual de ejecución
    app_name: str = "SmartInventory-Chatbot" # Nombre de la aplicación
    debug: bool = True # Activa/desactiva modo debug
    log_level: str = "INFO" # Nivel de logging

    # Servidor
    host: str = "0.0.0.0" # Host donde correrá FastAPI
    port: int = 8000 # Puerto de la aplicación

    # Conexión con la API .NET
    dotnet_api_base_url: str = "https://localhost:5001/api" # URL base de la API externa en .NET
    dotnet_api_timeout: int = 30 # Tiempo máximo de espera HTTP
    dotnet_service_api_key: str = "" # API KEY para autenticación entre servicios
    dotnet_max_retries: int = 3 # Cantidad máxima de reintentos
    dotnet_retry_backoff_seconds: float = 0.5 # Tiempo de espera entre reintentos

    # LLM
    openai_api_key: str = "" # API KEY de OpenAI
    openai_model: str = "gpt-4o-mini" # Modelo principal utilizado por LangChain
    embedding_model: str = "text-embedding-3-small" # Modelo para embeddings/vectorización

    # Sesión
    session_store: str = "memory" # Tipo de almacenamiento de sesiones
    session_ttl_seconds: int = 3600 # Tiempo de vida de una sesión
    session_cleanup_interval_seconds: int = 300 # Intervalo de limpieza automática

    # Grafo
    graph_timeout_seconds: int = 60 # Timeout máximo del flujo conversacional

    # CORS (uno o más orígenes separados por coma)
    allowed_origins: str = "https://localhost:5001" # Lista de dominios permitidos

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Archivo desde donde se cargan variables
    #env_file=".env",

    # Ignora variables extra no declaradas
    #extra="ignore"

    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Convierte el string de origins separados por coma
        en una lista de Python.

        Ejemplo:

        Input:
            "http://localhost:3000,http://localhost:5173"

        Output:
            [
                "http://localhost:3000",
                "http://localhost:5173"
            ]
        """
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _validate_production_requirements(self) -> "Settings":
        
        """
        Valida que en producción existan variables críticas.

        Evita arrancar el sistema sin:
            - API KEY OpenAI
            - URL API .NET
            - API KEY interna

        Esto reduce errores graves de despliegue.
        """
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


settings = Settings() # Objeto global reutilizado en toda la aplicación
