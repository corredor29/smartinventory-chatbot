from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END

from app.graph.edges import route_after_model, route_after_tools
from app.graph.state import ChatState


def _base_state(messages: list) -> ChatState:
    return ChatState(
        session_id="abc-123",
        messages=messages,
        pending_product_id=None,
        pending_product_name=None,
        pending_quantity=None,
        pending_unit_price=None,
        customer_id=None,
        state="IN_PROGRESS",
        invoice_number=None,
        escalated=False,
    )


class TestRouteAfterModel:
    def test_routes_to_tools_when_model_requests_a_tool_call(self):
        message = AIMessage(
            content="",
            tool_calls=[{"name": "search_product", "args": {"query": "teclado"}, "id": "1"}],
        )
        state = _base_state([message])

        assert route_after_model(state) == "tools"

    def test_ends_when_model_answers_with_plain_text(self):
        state = _base_state([AIMessage(content="Claro, ¿en qué te ayudo?")])

        assert route_after_model(state) == END


class TestRouteAfterTools:
    def test_escalate_to_human_routes_to_mark_escalated(self):
        message = ToolMessage(
            content='{"success": true}', name="escalate_to_human", tool_call_id="1"
        )
        state = _base_state([message])

        assert route_after_tools(state) == "mark_escalated"

    def test_any_other_tool_routes_back_to_call_model(self):
        message = ToolMessage(
            content='{"found": true}', name="search_product", tool_call_id="1"
        )
        state = _base_state([message])

        assert route_after_tools(state) == "call_model"
