from app.agents.tools import escalation_tools
from app.clients.dotnet_client import DotnetConnectionError


class TestEscalateToHuman:
    async def test_success_returns_escalation_id(self, mocker):
        mocker.patch.object(
            escalation_tools.dotnet_client,
            "post",
            mocker.AsyncMock(return_value={"escalation_id": 99}),
        )

        result = await escalation_tools.escalate_to_human.ainvoke(
            {"session_id": "abc-123", "reason": "Cliente pide hablar con una persona"}
        )

        assert result["success"] is True
        assert result["escalation_id"] == 99
        escalation_tools.dotnet_client.post.assert_awaited_once_with(
            "/chat/escalate",
            json={"session_id": "abc-123", "reason": "Cliente pide hablar con una persona"},
        )

    async def test_connection_error_does_not_raise(self, mocker):
        mocker.patch.object(
            escalation_tools.dotnet_client,
            "post",
            mocker.AsyncMock(side_effect=DotnetConnectionError("no network")),
        )

        result = await escalation_tools.escalate_to_human.ainvoke(
            {"session_id": "abc-123", "reason": "Frustración del cliente"}
        )

        assert result["success"] is False


class TestNotifyAdvisor:
    async def test_success(self, mocker):
        mocker.patch.object(
            escalation_tools.dotnet_client, "post", mocker.AsyncMock(return_value={})
        )

        result = await escalation_tools.notify_advisor.ainvoke(
            {
                "session_id": "abc-123",
                "notification_type": "shipping_verification",
                "details": "1 teclado, factura FAC-000001",
                "sale_id": 1,
            }
        )

        assert result == {"success": True}

    async def test_failure_does_not_raise(self, mocker):
        mocker.patch.object(
            escalation_tools.dotnet_client,
            "post",
            mocker.AsyncMock(side_effect=DotnetConnectionError("no network")),
        )

        result = await escalation_tools.notify_advisor.ainvoke(
            {
                "session_id": "abc-123",
                "notification_type": "sale_problem",
                "details": "create_sale falló",
            }
        )

        assert result["success"] is False
