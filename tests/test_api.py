"""API tests. The AI calls are replaced with fakes, so no API key, network or model download is needed."""

import pytest
from fastapi.testclient import TestClient

import main
from gemini_client import GeminiConfigError, GeminiError


@pytest.fixture()
def client():
    return TestClient(main.app)


def test_home_page_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "EduGenie" in response.text


def test_static_files_served(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "gemini_model" in body


def test_qa_success(client, monkeypatch):
    monkeypatch.setattr(main, "answer_question_with_gemini", lambda q: f"Answer to {q}")
    response = client.get("/qa", params={"question": "Which is the largest ocean?"})
    assert response.status_code == 200
    assert response.json() == {"answer": "Answer to Which is the largest ocean?"}


def test_qa_requires_question(client):
    assert client.get("/qa").status_code == 422


def test_qa_gemini_error_is_clean_json(client, monkeypatch):
    def boom(_):
        raise GeminiError("quota exceeded")

    monkeypatch.setattr(main, "answer_question_with_gemini", boom)
    response = client.get("/qa", params={"question": "hi"})
    assert response.status_code == 502
    assert response.json() == {"error": "quota exceeded"}


def test_missing_api_key_reports_500(client, monkeypatch):
    def no_key(_):
        raise GeminiConfigError("GEMINI_API_KEY is not set")

    monkeypatch.setattr(main, "answer_question_with_gemini", no_key)
    response = client.get("/qa", params={"question": "hi"})
    assert response.status_code == 500
    assert "GEMINI_API_KEY" in response.json()["error"]


@pytest.mark.parametrize("path", ["/explain", "/explain/"])
def test_explain_success_with_and_without_trailing_slash(client, monkeypatch, path):
    monkeypatch.setattr(main, "explain_topic", lambda t: f"{t} explained")
    response = client.post(path, json={"topic": "Photosynthesis"})
    assert response.status_code == 200
    assert response.json() == {"topic": "Photosynthesis", "explanation": "Photosynthesis explained"}


def test_explain_requires_topic(client):
    response = client.post("/explain/", json={})
    assert response.status_code == 400
    assert response.json() == {"error": "Please provide a topic."}


def test_explain_rejects_invalid_json(client):
    response = client.post("/explain/", content="not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400


@pytest.mark.parametrize("path", ["/summarize", "/summarize/"])
def test_summarize_success(client, monkeypatch, path):
    monkeypatch.setattr(main, "summarize_text", lambda t: "short")
    response = client.post(path, json={"text": "A very long paragraph"})
    assert response.status_code == 200
    assert response.json() == {"summary": "short"}


def test_summarize_requires_text(client):
    assert client.post("/summarize/", json={"text": "   "}).status_code == 400


def test_quiz_success(client, monkeypatch):
    fake = [{"question": "Q?", "options": ["a", "b", "c", "d"], "answer": "a"}]
    monkeypatch.setattr(main, "generate_quiz", lambda t: fake)
    response = client.post("/quiz", json={"text": "Solar System"})
    assert response.status_code == 200
    assert response.json() == {"quiz": fake}


def test_quiz_requires_text(client):
    response = client.post("/quiz", json={})
    assert response.status_code == 400
    assert response.json() == {"error": "Please provide text for quiz."}


def test_quiz_rejects_oversized_input(client):
    response = client.post("/quiz", json={"text": "x" * (main.MAX_INPUT_CHARS + 1)})
    assert response.status_code == 400


def test_learning_recommendations_success(client, monkeypatch):
    monkeypatch.setattr(main, "get_learning_recommendations", lambda t: f"Plan for {t}")
    response = client.get("/learn/recommendations", params={"topic": "SQL"})
    assert response.status_code == 200
    assert response.json() == {"topic": "SQL", "recommendation": "Plan for SQL"}
