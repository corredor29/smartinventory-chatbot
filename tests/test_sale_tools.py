import pytest

from app.agents.tools import sale_tools
from app.clients.dotnet_client import DotnetBusinessError, DotnetConnectionError


class TestCreateSale:
    async def test_success_returns_invoice_details(self, mocker):
        mocker.patch.object(
            sale_tools.dotnet_client,
            "post",
            mocker.AsyncMock(
                return_value={
                    "sale_id": 42,
                    "invoice_number": "FAC-000042",
                    "total": 150000,
                }
            ),
        )

        result = await sale_tools.create_sale.ainvoke(
            {"session_id": "abc-123", "product_id": 1, "quantity": 2, "customer_id": 7}
        )

        assert result["success"] is True
        assert result["invoice_number"] == "FAC-000042"
        assert result["sale_id"] == 42
        sale_tools.dotnet_client.post.assert_awaited_once_with(
            "/sales",
            json={
                "session_id": "abc-123",
                "customer_id": 7,
                "items": [{"product_id": 1, "quantity": 2}],
                "origin": "Chatbot",
            },
        )

    async def test_business_error_returns_failure_without_raising(self, mocker):
        mocker.patch.object(
            sale_tools.dotnet_client,
            "post",
            mocker.AsyncMock(side_effect=DotnetBusinessError(400, "Stock insuficiente")),
        )

        result = await sale_tools.create_sale.ainvoke(
            {"session_id": "abc-123", "product_id": 1, "quantity": 2}
        )

        assert result["success"] is False
        assert "Stock insuficiente" in result["error"]

    async def test_connection_error_returns_failure_without_raising(self, mocker):
        mocker.patch.object(
            sale_tools.dotnet_client,
            "post",
            mocker.AsyncMock(side_effect=DotnetConnectionError("no network")),
        )

        result = await sale_tools.create_sale.ainvoke(
            {"session_id": "abc-123", "product_id": 1, "quantity": 2}
        )

        assert result["success"] is False

    async def test_rejects_non_positive_quantity(self):
        with pytest.raises(Exception):
            await sale_tools.create_sale.ainvoke(
                {"session_id": "abc-123", "product_id": 1, "quantity": 0}
            )

    async def test_rejects_quantity_above_limit(self):
        with pytest.raises(Exception):
            await sale_tools.create_sale.ainvoke(
                {"session_id": "abc-123", "product_id": 1, "quantity": 500}
            )
