import pytest

from app.agents.tools import product_tools
from app.clients.dotnet_client import DotnetBusinessError, DotnetConnectionError


class TestSearchProduct:
    async def test_returns_dotnet_result_on_success(self, mocker):
        fake_result = {
            "found": True,
            "products": [{"product_id": 1, "name": "Teclado mecánico", "price": 150000}],
        }
        mocker.patch.object(
            product_tools.dotnet_client, "get", mocker.AsyncMock(return_value=fake_result)
        )

        result = await product_tools.search_product.ainvoke({"query": "teclado"})

        assert result == fake_result
        product_tools.dotnet_client.get.assert_awaited_once_with(
            "/products/search", params={"q": "teclado"}
        )

    async def test_connection_error_returns_safe_fallback(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client,
            "get",
            mocker.AsyncMock(side_effect=DotnetConnectionError("timeout")),
        )

        result = await product_tools.search_product.ainvoke({"query": "teclado"})

        assert result["found"] is False
        assert result["products"] == []
        assert "timeout" in result["error"]

    async def test_business_error_does_not_raise(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client,
            "get",
            mocker.AsyncMock(side_effect=DotnetBusinessError(500, "Internal error")),
        )

        result = await product_tools.search_product.ainvoke({"query": "teclado"})

        assert result["found"] is False

    async def test_unexpected_error_does_not_propagate(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client, "get", mocker.AsyncMock(side_effect=ValueError("boom"))
        )

        result = await product_tools.search_product.ainvoke({"query": "teclado"})

        assert result["found"] is False
        assert result["error"] == "Error inesperado del sistema."


class TestCheckStock:
    async def test_available_when_stock_covers_quantity(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client,
            "get",
            mocker.AsyncMock(return_value={"current_stock": 10}),
        )

        result = await product_tools.check_stock.ainvoke({"product_id": 1, "quantity": 3})

        assert result == {"available": True, "current_stock": 10, "requested_quantity": 3}

    async def test_not_available_when_stock_is_insufficient(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client,
            "get",
            mocker.AsyncMock(return_value={"current_stock": 1}),
        )

        result = await product_tools.check_stock.ainvoke({"product_id": 1, "quantity": 5})

        assert result["available"] is False
        assert result["current_stock"] == 1

    async def test_connection_error_reports_unavailable(self, mocker):
        mocker.patch.object(
            product_tools.dotnet_client,
            "get",
            mocker.AsyncMock(side_effect=DotnetConnectionError("no network")),
        )

        result = await product_tools.check_stock.ainvoke({"product_id": 1, "quantity": 2})

        assert result["available"] is False
        assert result["current_stock"] == 0

    async def test_rejects_quantity_above_limit(self):
        with pytest.raises(Exception):
            await product_tools.check_stock.ainvoke({"product_id": 1, "quantity": 1000})
