from langchain_core.messages import AIMessage, HumanMessage

from app.clients.dotnet_client import dotnet_client, DotnetConnectionError
from app.graph.builder import chat_graph


def _tool_call_message(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def _initial_state(session_id: str, message_text: str) -> dict:
    return {
        "session_id": session_id,
        "messages": [HumanMessage(content=message_text)],
        "pending_product_id": None,
        "pending_product_name": None,
        "pending_quantity": None,
        "pending_unit_price": None,
        "customer_id": None,
        "state": "IN_PROGRESS",
        "invoice_number": None,
        "escalated": False,
    }


class TestFullSaleFlow:
    """
    Simula una conversación completa: buscar producto -> validar stock ->
    confirmar -> crear venta -> notificar asesor, en dos turnos de chat (como
    llegarían realmente desde el endpoint /chat/message, uno por mensaje del
    cliente).
    """

    async def test_end_to_end_sale(self, mocker):
        async def fake_get(path, params=None):
            if path == "/products/search":
                return {
                    "found": True,
                    "products": [
                        {
                            "product_id": 1,
                            "name": "Teclado Mecánico RGB",
                            "price": 150000,
                            "category_name": "Perifericos",
                            "status_name": "Activo",
                            "current_stock": 5,
                        }
                    ],
                }
            if path == "/inventory/1/stock":
                return {"current_stock": 5}
            raise AssertionError(f"GET inesperado: {path}")

        async def fake_post(path, json):
            if path == "/sales":
                return {"sale_id": 1, "invoice_number": "FAC-000001", "total": 150000}
            if path == "/chat/notify-advisor":
                return {}
            raise AssertionError(f"POST inesperado: {path}")

        mocker.patch.object(dotnet_client, "get", side_effect=fake_get)
        mocker.patch.object(dotnet_client, "post", side_effect=fake_post)

        responses = [
            # Turno 1
            _tool_call_message("search_product", {"query": "teclado mecánico"}, "call_1"),
            _tool_call_message("check_stock", {"product_id": 1, "quantity": 1}, "call_2"),
            AIMessage(
                content=(
                    "Encontré el Teclado Mecánico RGB. Hay 5 unidades disponibles. "
                    "El total por 1 unidad es $150.000 COP. ¿Deseas confirmar la compra?"
                )
            ),
            # Turno 2
            _tool_call_message(
                "create_sale",
                {"session_id": "session-1", "product_id": 1, "quantity": 1},
                "call_3",
            ),
            _tool_call_message(
                "notify_advisor",
                {
                    "session_id": "session-1",
                    "notification_type": "shipping_verification",
                    "details": "1 Teclado Mecánico RGB, factura FAC-000001",
                    "sale_id": 1,
                },
                "call_4",
            ),
            AIMessage(content="¡Listo! Tu compra fue registrada con la factura FAC-000001."),
        ]
        # `agent_model` es un RunnableBinding (pydantic estricto): no se le pueden
        # parchear atributos directamente. En su lugar se reemplaza la referencia
        # que usa el nodo `call_model` (importada como `app.graph.nodes.agent_model`).
        mock_model = mocker.patch("app.graph.nodes.agent_model")
        mock_model.invoke.side_effect = responses

        # Turno 1: el cliente pide el producto
        state = _initial_state("session-1", "Quiero comprar un teclado mecánico")
        turn1 = await chat_graph.ainvoke(state)

        assert turn1["escalated"] is False
        assert "confirmar" in turn1["messages"][-1].content.lower()

        # Turno 2: el cliente confirma la compra
        turn1["messages"].append(HumanMessage(content="Sí, confirmo"))
        turn2 = await chat_graph.ainvoke(turn1)

        assert turn2["invoice_number"] == "FAC-000001"
        assert "FAC-000001" in turn2["messages"][-1].content
        assert mock_model.invoke.call_count == 6

        dotnet_client.post.assert_any_await(
            "/sales",
            json={
                "session_id": "session-1",
                "customer_id": None,
                "items": [{"product_id": 1, "quantity": 1}],
                "origin": "Chatbot",
            },
        )
        dotnet_client.post.assert_any_await(
            "/chat/notify-advisor",
            json={
                "session_id": "session-1",
                "notification_type": "shipping_verification",
                "details": "1 Teclado Mecánico RGB, factura FAC-000001",
                "sale_id": 1,
            },
        )


class TestEscalationStopsFlow:
    async def test_escalate_to_human_ends_the_turn_without_further_model_calls(self, mocker):
        mocker.patch.object(
            dotnet_client, "post", mocker.AsyncMock(return_value={"escalation_id": 5})
        )
        mock_model = mocker.patch("app.graph.nodes.agent_model")
        mock_model.invoke.side_effect = [
            _tool_call_message(
                "escalate_to_human",
                {"session_id": "session-2", "reason": "Cliente pide hablar con una persona"},
                "call_1",
            ),
        ]

        state = _initial_state("session-2", "Quiero hablar con una persona ya")
        result = await chat_graph.ainvoke(state)

        assert result["escalated"] is True
        assert result["state"] == "WAITING_HUMAN_AGENT"
        # El grafo debe terminar justo después de mark_escalated: el modelo
        # solo se invocó una vez (para decidir escalar), nunca más después.
        assert mock_model.invoke.call_count == 1

    async def test_escalation_failure_is_reported_but_does_not_raise(self, mocker):
        mocker.patch.object(
            dotnet_client, "post", mocker.AsyncMock(side_effect=DotnetConnectionError("down"))
        )
        mock_model = mocker.patch("app.graph.nodes.agent_model")
        mock_model.invoke.side_effect = [
            _tool_call_message(
                "escalate_to_human",
                {"session_id": "session-3", "reason": "Frustración evidente"},
                "call_1",
            ),
        ]

        state = _initial_state("session-3", "Esto no funciona, quiero hablar con alguien")
        result = await chat_graph.ainvoke(state)

        # Incluso si notificar al backend .NET falla, el bot debe marcar la
        # conversación como escalada localmente y detener el flujo.
        assert result["escalated"] is True
        assert mock_model.invoke.call_count == 1
