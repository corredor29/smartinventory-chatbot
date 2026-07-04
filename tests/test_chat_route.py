from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app
from app.session import memory_store


class TestChatRouteValidation:
    def test_rejects_empty_message(self):
        with TestClient(app) as client:
            response = client.post(
                "/chat/message", json={"session_id": "abc-123", "message": ""}
            )
        assert response.status_code == 422

    def test_rejects_message_too_long(self):
        with TestClient(app) as client:
            response = client.post(
                "/chat/message",
                json={"session_id": "abc-123", "message": "a" * 2001},
            )
        assert response.status_code == 422

    def test_rejects_invalid_session_id_format(self):
        with TestClient(app) as client:
            response = client.post(
                "/chat/message",
                json={"session_id": "abc 123 !!", "message": "hola"},
            )
        assert response.status_code == 422


class TestChatRouteEndToEnd:
    def test_happy_path_returns_bot_response(self, mocker):
        mocker.patch(
            "app.graph.nodes.agent_model"
        ).invoke.return_value = AIMessage(content="¡Hola! ¿En qué puedo ayudarte?")

        with TestClient(app) as client:
            response = client.post(
                "/chat/message",
                json={"session_id": "session-http-1", "message": "hola"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["response"] == "¡Hola! ¿En qué puedo ayudarte?"
        assert body["state"] == "IN_PROGRESS"

        memory_store.clear_session("session-http-1")
