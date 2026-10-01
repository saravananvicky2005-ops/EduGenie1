"""Shared Gemini helper used by the Q&A, quiz, summary and learning-path modules.

Uses the current `google-genai` SDK (the older `google-generativeai` package is deprecated).
Configuration comes from the `.env` file next to this script.
"""

import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the project folder no matter where the server is started from.
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger("edugenie")

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODELS = "gemini-3.7-flash,gemini-3.5-flash-lite"

# HTTP status codes that are usually temporary: wait and retry, then try a backup model.
RETRYABLE_CODES = {429, 500, 502, 503, 504}
RETRIES_PER_MODEL = 2   # extra attempts per model after the first try
BACKOFF_SECONDS = 1.5


class EduGenieError(RuntimeError):
    """Base error for anything that goes wrong inside an EduGenie module."""

    status_code = 502


class GeminiConfigError(EduGenieError):
    """Raised when the Gemini API key is missing."""

    status_code = 500


class GeminiError(EduGenieError):
    """Raised when a call to the Gemini API fails or returns nothing usable."""

    status_code = 502


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def get_model_chain() -> list:
    """Primary model first, then the backup models (duplicates removed)."""
    backups = os.getenv("GEMINI_FALLBACK_MODELS")
    if backups is None:
        backups = DEFAULT_FALLBACK_MODELS
    chain = [get_model_name()] + [m.strip() for m in backups.split(",") if m.strip()]
    seen, unique = set(), []
    for model in chain:
        if model not in seen:
            seen.add(model)
            unique.append(model)
    return unique


def _status_code(exc: Exception) -> int:
    """Best-effort HTTP status code of a Gemini SDK error (0 if unknown)."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    text = str(exc)
    for candidate in (429, 500, 502, 503, 504, 404, 403, 400):
        if str(candidate) in text[:20]:
            return candidate
    return 0


def has_api_key() -> bool:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    return bool(key.strip()) and key.strip() != "your_gemini_api_key_here"


@lru_cache(maxsize=1)
def _get_client():
    if not has_api_key():
        raise GeminiConfigError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://aistudio.google.com/apikey, then restart the server."
        )
    try:
        from google import genai
    except ImportError as exc:
        raise GeminiConfigError(
            "The 'google-genai' package is not installed. Run: pip install -r requirements.txt"
        ) from exc
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")).strip()
    return genai.Client(api_key=api_key)


def generate_text(
    prompt: str,
    *,
    json_output: bool = False,
    temperature: float = 0.4,
    system_instruction: Optional[str] = None,
) -> str:
    """Send a prompt to Gemini and return the response text.

    Temporary overload errors (503/429/...) are retried automatically, and if the main model
    stays unavailable the backup models from GEMINI_FALLBACK_MODELS are tried in order.
    Raises GeminiConfigError / GeminiError with a readable message if everything fails.
    """
    client = _get_client()  # validates the key and the SDK before anything else
    from google.genai import types

    config_kwargs = {"temperature": temperature}
    if json_output:
        config_kwargs["response_mime_type"] = "application/json"
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    config = types.GenerateContentConfig(**config_kwargs)

    failures = []
    for model in get_model_chain():
        for attempt in range(RETRIES_PER_MODEL + 1):
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
            except Exception as exc:
                code = _status_code(exc)
                logger.warning("Gemini call failed (model=%s, attempt=%d, code=%s): %s", model, attempt + 1, code, exc)
                if code in RETRYABLE_CODES and attempt < RETRIES_PER_MODEL:
                    time.sleep(BACKOFF_SECONDS * (attempt + 1))
                    continue
                failures.append(f"{model}: {exc}")
                break  # give up on this model (404, bad key, retries used up...) and try the next one

            text = (getattr(response, "text", None) or "").strip()
            if text:
                if failures:
                    logger.info("Answered by backup model %s", model)
                return text
            failures.append(f"{model}: empty response (possibly blocked by safety filters)")
            break

    raise GeminiError(
        "Gemini API request failed on every model tried. "
        "This is usually temporary (high demand), so wait a minute and try again. Details: "
        + " | ".join(failures)
    )
