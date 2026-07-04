import httpx
import pytest

from app.clients.dotnet_client import DotnetBusinessError, DotnetClient


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text
        self.content = b"{}" if json_data is not None else b""

    def json(self):
        return self._json


@pytest.fixture
def client(mocker):
    """
    DotnetClient con reintentos rápidos (sin esperar de verdad) y con su
    cliente httpx interno reemplazado por un mock, para probar la lógica de
    reintentos/errores sin hacer red real.
    """
    c = DotnetClient()
    c.max_retries = 3
    c.backoff_base_seconds = 0.01
    fake_httpx_client = mocker.AsyncMock()
    c._client = fake_httpx_client
    mocker.patch("app.clients.dotnet_client.asyncio.sleep", mocker.AsyncMock())
    return c


class TestRetryOnTransientFailures:
    async def test_retries_connection_error_then_succeeds(self, client, mocker):
        client._client.request.side_effect = [
            httpx.ConnectError("no route to host"),
            FakeResponse(200, {"ok": True}),
        ]

        result = await client.get("/products/search")

        assert result == {"ok": True}
        assert client._client.request.await_count == 2

    async def test_retries_on_5xx_then_succeeds(self, client):
        client._client.request.side_effect = [
            FakeResponse(503, text="Service Unavailable"),
            FakeResponse(200, {"ok": True}),
        ]

        result = await client.get("/products/search")

        assert result == {"ok": True}
        assert client._client.request.await_count == 2

    async def test_exhausts_retries_and_raises(self, client):
        client._client.request.side_effect = [
            httpx.ConnectTimeout("timeout"),
            httpx.ConnectTimeout("timeout"),
            httpx.ConnectTimeout("timeout"),
        ]

        with pytest.raises(Exception):
            await client.get("/products/search")

        assert client._client.request.await_count == 3


class TestNoRetryOnBusinessErrors:
    async def test_404_raises_immediately_without_retry(self, client):
        client._client.request.side_effect = [FakeResponse(404, text="Not found")]

        with pytest.raises(DotnetBusinessError) as exc_info:
            await client.get("/products/999")

        assert exc_info.value.status_code == 404
        assert client._client.request.await_count == 1

    async def test_400_raises_immediately_without_retry(self, client):
        client._client.request.side_effect = [FakeResponse(400, text="Bad request")]

        with pytest.raises(DotnetBusinessError):
            await client.post("/sales", json={"foo": "bar"})

        assert client._client.request.await_count == 1


class TestSuccessResponses:
    async def test_returns_empty_dict_for_no_content_response(self, client):
        client._client.request.side_effect = [FakeResponse(204)]

        result = await client.put("/inventory/1/stock")

        assert result == {}
