import os

# Debe fijarse ANTES de que cualquier módulo de la app se importe, porque
# `app.agents.agent` construye el cliente de OpenAI (ChatOpenAI) al momento
# de importarse, y sin una api key (aunque sea falsa) esa construcción falla.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DOTNET_API_BASE_URL", "http://dotnet.test/api")
os.environ.setdefault("DOTNET_SERVICE_API_KEY", "test-service-key")
os.environ.setdefault("APP_ENV", "test")
