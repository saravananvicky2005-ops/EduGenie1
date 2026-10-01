"""Unit tests for quiz parsing: no network, no API key needed."""

import json

import pytest

import quiz_module
from gemini_client import EduGenieError


def make_question(answer="Paris"):
    return {
        "question": "What is the capital of France?",
        "options": ["Paris", "Rome", "Madrid", "Berlin"],
        "answer": answer,
    }


def test_clean_json_block_removes_fences():
    raw = '```json\n[{"a": 1}]\n```'
    assert quiz_module.clean_json_block(raw) == '[{"a": 1}]'


def test_clean_json_block_leaves_plain_json_alone():
    assert quiz_module.clean_json_block('[{"a": 1}]') == '[{"a": 1}]'


def test_parse_quiz_valid_and_answer_still_in_options():
    raw = json.dumps([make_question() for _ in range(3)])
    quiz = quiz_module.parse_quiz(raw)
    assert len(quiz) == 3
    for q in quiz:
        assert len(q["options"]) == 4
        assert q["answer"] in q["options"]


def test_parse_quiz_accepts_fenced_json():
    raw = "```json\n" + json.dumps([make_question()]) + "\n```"
    assert len(quiz_module.parse_quiz(raw)) == 1


def test_parse_quiz_maps_letter_answer_to_option_text():
    quiz = quiz_module.parse_quiz(json.dumps([make_question(answer="B")]))
    assert quiz[0]["answer"] == "Rome"


def test_parse_quiz_fixes_answer_casing():
    quiz = quiz_module.parse_quiz(json.dumps([make_question(answer="paris")]))
    assert quiz[0]["answer"] == "Paris"


def test_parse_quiz_unwraps_questions_object():
    raw = json.dumps({"questions": [make_question()]})
    assert len(quiz_module.parse_quiz(raw)) == 1


def test_parse_quiz_skips_invalid_but_keeps_valid():
    bad = {"question": "Bad?", "options": ["x", "y"], "answer": "x"}
    quiz = quiz_module.parse_quiz(json.dumps([bad, make_question()]))
    assert len(quiz) == 1


def test_parse_quiz_caps_at_three_questions():
    raw = json.dumps([make_question() for _ in range(5)])
    assert len(quiz_module.parse_quiz(raw)) == 3


def test_parse_quiz_rejects_garbage():
    with pytest.raises(EduGenieError):
        quiz_module.parse_quiz("this is not json at all")


def test_parse_quiz_rejects_answer_not_in_options():
    with pytest.raises(EduGenieError):
        quiz_module.parse_quiz(json.dumps([make_question(answer="Tokyo")]))


def test_generate_quiz_uses_model_output(monkeypatch):
    monkeypatch.setattr(quiz_module, "generate_text", lambda *a, **k: json.dumps([make_question()]))
    quiz = quiz_module.generate_quiz("Capitals of Europe")
    assert quiz[0]["question"].startswith("What is the capital")
