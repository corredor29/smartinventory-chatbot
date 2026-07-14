import asyncio #Permite implementar los tiempos de espera utilizados durante los reintentos automáticos (Backoff Exponencial).
from typing import Any #Tipo genérico utilizado para representar parámetros o valores de retorno que pueden ser de cualquier tipo, proporcionando flexibilidad en la definición de funciones y métodos.

import httpx #Cliente HTTP asíncrono utilizado para consumir la API esarrollada en .NET.

from app.core.config import settings #Configuración general del chatbot
from app.core.logging import logger #Logger centralizado del proyecto.

#Todas las excepciones relacionadas con la comunicación
#hacia la API .NET heredan de esta clase.
class DotnetClientError(Exception):
    """Error base para cualquier fallo al comunicarse con la API .NET."""

#Representa un problema de comunicación entre el chatbot
#y la API .NET.

#Este tipo de error ocurre cuando la API nunca alcanza a
#responder.
class DotnetConnectionError(DotnetClientError):
    """
    Fallo de red (timeout, conexión rechazada, DNS, etc.), es decir, la API
    .NET no llegó a responder. Este tipo de error sí amerita reintentos.
    """

# Representa un error devuelto por la API .NET.
# A diferencia de DotnetConnectionError, en este caso la
# solicitud sí llegó correctamente al servidor.
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

    def __init__(self) -> None: #Inicializa el cliente HTTP
        self.base_url = settings.dotnet_api_base_url.rstrip("/")
        self.max_retries = settings.dotnet_max_retries #Número máximo de intentos permitidos cuando ocurre un error temporal.
        self.backoff_base_seconds = settings.dotnet_retry_backoff_seconds #Tiempo base utilizado para calcular el Backoff Exponencial.
        self.headers: dict[str, str] = {"Content-Type": "application/json"} #Encabezados HTTP enviados en todas las solicitudes.
        if settings.dotnet_service_api_key: #Si el backend requiere autenticación mediante API Key, ésta se agrega automáticamente a los encabezados.
            self.headers["X-Api-Key"] = settings.dotnet_service_api_key
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        # Se crea de forma perezosa (no en __init__) para garantizar que quede
        # asociado al event loop que efectivamente lo usa.
        if self._client is None:
            timeout = httpx.Timeout(
                connect=5.0, # Tiempo máximo para establecer conexión.
                read=settings.dotnet_api_timeout, # Tiempo máximo esperando respuesta.
                write=10.0, # Tiempo máximo enviando datos.
                pool=5.0, #Tiempo máximo esperando una conexión libre dentro del Pool.
            )
            self._client = httpx.AsyncClient( #Se crea un único AsyncClient reutilizable.
                base_url=self.base_url, headers=self.headers, timeout=timeout
            )
        return self._client #Siempre se devuelve la misma instancia mientras la aplicación permanezca en ejecución.

    async def aclose(self) -> None:
        """Cierra la conexión HTTP subyacente. Debe llamarse al apagar la app."""
        if self._client is not None:
            await self._client.aclose() #Cierra la conexión HTTP subyacente y libera recursos asociados.
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client() #Obtiene la instancia reutilizable de AsyncClient.
        last_error: DotnetClientError | None = None #Variable utilizada para almacenar el último error ocurrido durante los intentos.

        for attempt in range(1, self.max_retries + 1): #Se intenta ejecutar la solicitud varias veces.
            try:
                response = await client.request(method, path, params=params, json=json)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                     httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_error = DotnetConnectionError( #La solicitud nunca llegó correctamente al servidor.
                    f"No se pudo conectar con la API .NET ({method} {path}): {exc}"
                )
            else:
                if response.status_code < 400: #La operación fue exitosa.
                    if not response.content:
                        return {} #Algunos endpoints pueden responder sin contenido.
                    payload = response.json()
                    # SmartInventoryAPI envuelve respuestas 2xx en { success, data }
                    # Este bloque extrae únicamente la información útil para el chatbot.
                    if (
                        isinstance(payload, dict)
                        and "data" in payload
                        and "success" in payload
                    ):
                        data = payload.get("data")
                        if isinstance(data, dict):
                            return data
                        if data is None:
                            return {}
                        return {"value": data}
                    return payload if isinstance(payload, dict) else {"value": payload}# Si la respuesta ya viene como un diccionarionormal, simplemente se devuelve.

                if response.status_code < 500:
                    # Error de negocio (400/404/etc.): nunca se reintenta.
                    raise DotnetBusinessError(response.status_code, response.text)

                # 5xx: se trata como transitorio, se reintenta.
                last_error = DotnetBusinessError(response.status_code, response.text)
            #Si todavía quedan intentos disponibles, el cliente
            #espera unos segundos antes de volver a intentar la solicitud.
            #El tiempo aumenta exponencialmente.
            if attempt < self.max_retries:
                delay = self.backoff_base_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"Intento {attempt}/{self.max_retries} fallido hacia .NET "
                    f"({method} {path}): {last_error}. Reintentando en {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error
# Realiza una solicitud HTTP utilizando el método GET.
    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)
# Realiza una solicitud HTTP utilizando el método POST.
    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)
# Realiza una solicitud HTTP utilizando el método PUT.
    async def put(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)

#Se crea una única instancia global del cliente HTTP.
# Esto permite que toda la aplicación reutilice la misma conexión HTTP y aplique reintentos de manera consistente.

dotnet_client = DotnetClient()
