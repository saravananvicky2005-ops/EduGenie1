"""Question answering module (Gemini)."""

from gemini_client import generate_text

SYSTEM_INSTRUCTION = (
    "You are EduGenie, a friendly and accurate AI tutor for students of all levels. "
    "Answer clearly and concisely. Lead with the direct answer, then add a short explanation "
    "if it helps understanding. If you are not sure, say so instead of guessing."
)


def answer_question_with_gemini(question: str) -> str:
    """Return a concise, student-friendly answer to a general or academic question."""
    prompt = f"Student's question: {question.strip()}"
    return generate_text(prompt, temperature=0.3, system_instruction=SYSTEM_INSTRUCTION)
