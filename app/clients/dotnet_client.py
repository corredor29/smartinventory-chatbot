import httpx

from app.core.config import settings
from app.core.logging import logger


class DotnetClient:
    """
    Único punto de salida hacia la API .NET.
    Todo lo que necesite datos reales (productos, stock, ventas) pasa por aquí,
    nunca se llama httpx directamente desde otro archivo.
    """

    def __init__(self) -> None:
        self.base_url = settings.dotnet_api_base_url
        self.timeout = settings.dotnet_api_timeout
        self.headers = {
            "Content-Type": "application/json",
        }
        if settings.dotnet_service_api_key:
            self.headers["X-Api-Key"] = settings.dotnet_service_api_key

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}{path}", headers=self.headers, params=params
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, json: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}", headers=self.headers, json=json
            )
            response.raise_for_status()
            return response.json()

    async def put(self, path: str, json: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}{path}", headers=self.headers, json=json
            )
            response.raise_for_status()
            return response.json()


dotnet_client = DotnetClient()