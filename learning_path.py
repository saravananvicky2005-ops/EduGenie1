"""Learning path / recommendation module (Gemini)."""

from gemini_client import generate_text

SYSTEM_INSTRUCTION = (
    "You are EduGenie, an AI tutor who designs practical, structured learning plans."
)


def get_learning_recommendations(topic: str) -> str:
    """Return a structured beginner-to-advanced learning path for the given topic."""
    prompt = (
        f"The student wants to learn about: {topic.strip()}.\n\n"
        "Suggest a structured and adaptive learning path that includes:\n"
        "1. Key topics grouped into Beginner, Intermediate and Advanced levels, in the order they should be learned.\n"
        "2. A realistic time estimate for each level.\n"
        "3. Useful resources for each level (videos, articles, books, practice sites). "
        "Only recommend resources you are confident really exist, and prefer well-known ones.\n"
        "4. A few short adaptive learning tips.\n\n"
        "Use clear headings and bullet points."
    )
    return generate_text(prompt, temperature=0.5, system_instruction=SYSTEM_INSTRUCTION)
