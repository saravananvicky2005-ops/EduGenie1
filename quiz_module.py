"""Quiz generation module (Gemini).

Generates three multiple-choice questions (four options each) from a topic or passage and
returns them as a Python list of dicts:
    [{"question": str, "options": [str, str, str, str], "answer": str}, ...]
"""

import json
import random
import re
from typing import Any, List

from gemini_client import EduGenieError, generate_text

NUM_QUESTIONS = 3
NUM_OPTIONS = 4


def clean_json_block(text: str) -> str:
    """Remove Markdown ```json code fences that models sometimes wrap around JSON."""
    cleaned = re.sub(r"```(?:json)?\s*(.*?)```", r"\1", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def _extract_json_array(text: str) -> Any:
    """Parse JSON; if there is stray text around it, fall back to the outermost [...] block."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _normalise_question(item: Any) -> dict:
    """Validate one question and make sure `answer` exactly matches one of the options."""
    if not isinstance(item, dict):
        raise ValueError("question is not an object")

    question = str(item.get("question", "")).strip()
    options = item.get("options")
    answer = str(item.get("answer", "")).strip()

    if not question:
        raise ValueError("missing question text")
    if not isinstance(options, list) or len(options) != NUM_OPTIONS:
        raise ValueError(f"question must have exactly {NUM_OPTIONS} options")
    options = [str(o).strip() for o in options]
    if len(set(o.lower() for o in options)) != NUM_OPTIONS or not all(options):
        raise ValueError("options must be four distinct, non-empty strings")

    # The model may answer with a letter ("B", "B)") or with slightly different casing.
    if answer not in options:
        match = re.fullmatch(r"\(?([A-Da-d])[\).:]?", answer)
        lowered = [o.lower() for o in options]
        if match:
            answer = options[ord(match.group(1).upper()) - ord("A")]
        elif answer.lower() in lowered:
            answer = options[lowered.index(answer.lower())]
        else:
            raise ValueError("answer does not match any option")

    # Shuffle so the correct answer is not always in the same position.
    random.shuffle(options)
    return {"question": question, "options": options, "answer": answer}


def parse_quiz(raw: str) -> List[dict]:
    """Turn the raw model output into a validated list of questions."""
    try:
        data = _extract_json_array(clean_json_block(raw))
    except json.JSONDecodeError as exc:
        raise EduGenieError(f"Could not parse the quiz returned by the model as JSON: {exc}") from exc

    if isinstance(data, dict):  # some models wrap the list: {"questions": [...]}
        data = data.get("questions", data.get("quiz", []))
    if not isinstance(data, list) or not data:
        raise EduGenieError("The model did not return a list of quiz questions.")

    questions, problems = [], []
    for index, item in enumerate(data, start=1):
        try:
            questions.append(_normalise_question(item))
        except ValueError as exc:
            problems.append(f"question {index}: {exc}")

    if not questions:
        raise EduGenieError("The generated quiz was invalid (" + "; ".join(problems) + ").")
    return questions[:NUM_QUESTIONS]


def generate_quiz(text: str) -> list:
    """Generate a 3-question multiple-choice quiz from a topic or passage."""
    prompt = (
        "You are a quiz generator for students.\n\n"
        f"From the following topic or passage, create {NUM_QUESTIONS} multiple-choice questions. "
        "Each question must include:\n"
        '- a "question"\n'
        f'- a list of {NUM_OPTIONS} different "options" (one correct, three plausible distractors)\n'
        '- a correct "answer" that is copied EXACTLY, character for character, from one of the options\n\n'
        "Return ONLY valid JSON (no Markdown, no commentary) in exactly this shape:\n"
        "[\n"
        '  {"question": "What is ...?", "options": ["A", "B", "C", "D"], "answer": "A"}\n'
        "]\n\n"
        "Topic or passage:\n"
        f"{text.strip()}"
    )
    raw = generate_text(prompt, json_output=True, temperature=0.6)
    return parse_quiz(raw)
