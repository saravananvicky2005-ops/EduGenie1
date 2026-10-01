"""Summarization module (Gemini)."""

from gemini_client import generate_text

SYSTEM_INSTRUCTION = (
    "You are EduGenie, an AI study assistant that writes clear summaries for quick revision."
)


def summarize_text(text: str) -> str:
    """Summarize a long educational passage while keeping the core information."""
    prompt = (
        "Summarize the passage below for a student who wants to revise quickly.\n"
        "Rules:\n"
        "- Keep all of the core facts, definitions and conclusions.\n"
        "- Remove redundancy and filler.\n"
        "- Start with a 1-2 sentence overview, then list the key points as short bullet points.\n"
        "- Use simple language. Do not add information that is not in the passage.\n\n"
        "Passage:\n"
        f"{text.strip()}"
    )
    return generate_text(prompt, temperature=0.2, system_instruction=SYSTEM_INSTRUCTION)
