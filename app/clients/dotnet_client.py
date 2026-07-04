import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


class DotnetClientError(Exception):
    """Error base para cualquier fallo al comunicarse con la API .NET."""


class DotnetConnectionError(DotnetClientError):
    """
    Fallo de red (timeout, conexión rechazada, DNS, etc.), es decir, la API
    .NET no llegó a responder. Este tipo de error sí amerita reintentos.
    """


class DotnetBusinessError(DotnetClientError):
    """
    La API .NET respondió, pero con un código de error (4xx o 5xx). Los 4xx
    son errores de negocio (producto no existe, request inválido, etc.) y
    NO se reintentan; los 5xx se tratan como transitorios y sí se reintentan.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class DotnetClient:
    """
    Único punto de salida hacia la API .NET.
    Todo lo que necesite datos reales (productos, stock, ventas) pasa por aquí,
    nunca se llama httpx directamente desde otro archivo.

    Reutiliza una única conexión HTTP (pool de httpx) durante toda la vida de
    la aplicación en lugar de abrir una conexión nueva por request, y aplica
    reintentos con backoff exponencial únicamente a fallas transitorias
    (errores de red y 5xx). Los errores 4xx nunca se reintentan porque son
    errores de negocio (ej. producto inexistente) que no cambian al reintentar.
    """

    def __init__(self) -> None:
        self.base_url = settings.dotnet_api_base_url.rstrip("/")
        self.max_retries = settings.dotnet_max_retries
        self.backoff_base_seconds = settings.dotnet_retry_backoff_seconds
        self.headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.dotnet_service_api_key:
            self.headers["X-Api-Key"] = settings.dotnet_service_api_key
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        # Se crea de forma perezosa (no en __init__) para garantizar que quede
        # asociado al event loop que efectivamente lo usa.
        if self._client is None:
            timeout = httpx.Timeout(
                connect=5.0,
                read=settings.dotnet_api_timeout,
                write=10.0,
                pool=5.0,
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url, headers=self.headers, timeout=timeout
            )
        return self._client

    async def aclose(self) -> None:
        """Cierra la conexión HTTP subyacente. Debe llamarse al apagar la app."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        last_error: DotnetClientError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.request(method, path, params=params, json=json)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                     httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_error = DotnetConnectionError(
                    f"No se pudo conectar con la API .NET ({method} {path}): {exc}"
                )
            else:
                if response.status_code < 400:
                    if not response.content:
                        return {}
                    return response.json()

                if response.status_code < 500:
                    # Error de negocio (400/404/etc.): nunca se reintenta.
                    raise DotnetBusinessError(response.status_code, response.text)

                # 5xx: se trata como transitorio, se reintenta.
                last_error = DotnetBusinessError(response.status_code, response.text)

            if attempt < self.max_retries:
                delay = self.backoff_base_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"Intento {attempt}/{self.max_retries} fallido hacia .NET "
                    f"({method} {path}): {last_error}. Reintentando en {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)


dotnet_client = DotnetClient()
