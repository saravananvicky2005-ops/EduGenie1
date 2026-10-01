"""Live smoke tests against the real Gemini API.

They are skipped automatically unless GEMINI_API_KEY is configured in your .env file.
Run them with:  pytest tests/test_live_gemini.py -v
"""

import pytest

import gemini_client  # loads .env as a side effect
from qna import answer_question_with_gemini
from quiz_module import generate_quiz
from summary_module import summarize_text
from learning_path import get_learning_recommendations

pytestmark = pytest.mark.skipif(not gemini_client.has_api_key(), reason="GEMINI_API_KEY is not configured")


def test_live_qna():
    answer = answer_question_with_gemini("Which is the largest ocean?")
    assert "pacific" in answer.lower()


def test_live_quiz_shape():
    quiz = generate_quiz("The Pythagoras Theorem")
    assert 1 <= len(quiz) <= 3
    for q in quiz:
        assert len(q["options"]) == 4
        assert q["answer"] in q["options"]


def test_live_summary():
    text = (
        "Photosynthesis is the process by which green plants, algae and some bacteria convert light energy "
        "into chemical energy. Using chlorophyll, they absorb sunlight and use it to turn carbon dioxide and "
        "water into glucose and oxygen. The glucose is used as food while the oxygen is released into the air."
    )
    assert len(summarize_text(text)) > 20


def test_live_learning_path():
    assert "beginner" in get_learning_recommendations("SQL").lower()
