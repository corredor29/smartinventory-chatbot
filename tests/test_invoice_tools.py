from app.agents.tools import invoice_tools
from app.clients.dotnet_client import DotnetBusinessError


class TestGetInvoice:
    async def test_found_returns_invoice_details(self, mocker):
        mocker.patch.object(
            invoice_tools.dotnet_client,
            "get",
            mocker.AsyncMock(
                return_value={
                    "invoice_number": "FAC-000001",
                    "issue_date": "2026-07-01",
                    "total": 150000,
                    "items": [{"product_id": 1, "quantity": 1}],
                }
            ),
        )

        result = await invoice_tools.get_invoice.ainvoke({"invoice_number": "FAC-000001"})

        assert result["found"] is True
        assert result["invoice_number"] == "FAC-000001"
        assert result["items"] == [{"product_id": 1, "quantity": 1}]

    async def test_not_found_returns_message_without_raising(self, mocker):
        mocker.patch.object(
            invoice_tools.dotnet_client,
            "get",
            mocker.AsyncMock(side_effect=DotnetBusinessError(404, "Not found")),
        )

        result = await invoice_tools.get_invoice.ainvoke({"invoice_number": "FAC-999999"})

        assert result["found"] is False
        assert result["message"] == "No encontré una factura con ese número."
