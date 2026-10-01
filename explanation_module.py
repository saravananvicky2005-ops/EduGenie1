"""Concept explanation module.

Uses the lightweight, instruction-tuned LaMini-Flan-T5-783M model that runs locally on CPU.
The model is loaded lazily on the first request (not at import time), so the server starts
instantly and the Q&A / quiz / summary / learning-path features work even before the
~3 GB model has finished downloading.

Environment variables (see .env.example):
    EXPLAIN_BACKEND             "local" (default) or "gemini"
    EXPLAIN_FALLBACK_TO_GEMINI  "true" (default) -> use Gemini if the local model fails
    EXPLAIN_DEVICE              "cpu", "cuda", "mps" or empty for auto
    EXPLAIN_MODEL_ID            override the Hugging Face model id
"""

import logging
import os
import threading

from gemini_client import EduGenieError, GeminiError, generate_text

logger = logging.getLogger("edugenie")

MODEL_ID = os.getenv("EXPLAIN_MODEL_ID", "").strip() or "MBZUAI/LaMini-Flan-T5-783M"

_lock = threading.Lock()
_tokenizer = None
_model = None
_device = "cpu"


def _pick_device(torch) -> str:
    requested = os.getenv("EXPLAIN_DEVICE", "").strip().lower()
    if requested in {"cpu", "cuda", "mps"}:
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    """Load tokenizer + model once (thread-safe) and return them."""
    global _tokenizer, _model, _device
    if _model is not None:
        return _tokenizer, _model

    with _lock:
        if _model is None:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            logger.info("Loading local explanation model %s (first run downloads ~3 GB)...", MODEL_ID)
            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
            model.eval()
            _device = _pick_device(torch)
            model.to(_device)
            _tokenizer, _model = tokenizer, model
            logger.info("Explanation model ready on device '%s'.", _device)
    return _tokenizer, _model


def _explain_locally(topic: str) -> str:
    import torch

    tokenizer, model = _load_model()

    input_text = f"Explain the concept of '{topic}' in a simple and clear way for a school student."
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {name: tensor.to(_device) for name, tensor in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.7,
            top_k=50,
            top_p=0.95,
            do_sample=True,
            no_repeat_ngram_size=3,  # avoids the model repeating the same sentence
            repetition_penalty=1.2,
        )

    explanation = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    if not explanation:
        raise EduGenieError("The local model returned an empty explanation.")
    return explanation


def _explain_with_gemini(topic: str) -> str:
    prompt = (
        f"Explain the concept of '{topic}' in a simple and clear way for a school student. "
        "Use short sentences, everyday language and one easy example. Keep it under 150 words."
    )
    return generate_text(
        prompt,
        temperature=0.4,
        system_instruction="You are EduGenie, a patient teacher who explains ideas simply.",
    )


def explain_topic(topic: str) -> str:
    """Explain a concept in simple language."""
    topic = topic.strip()

    if os.getenv("EXPLAIN_BACKEND", "local").strip().lower() == "gemini":
        return _explain_with_gemini(topic)

    try:
        return _explain_locally(topic)
    except Exception as local_exc:
        logger.warning("Local explanation model failed: %s", local_exc)
        fallback_enabled = os.getenv("EXPLAIN_FALLBACK_TO_GEMINI", "true").strip().lower() == "true"
        if not fallback_enabled:
            raise EduGenieError(f"Local explanation model failed: {local_exc}") from local_exc
        try:
            return _explain_with_gemini(topic)
        except GeminiError as gemini_exc:
            raise EduGenieError(
                f"Local model failed ({local_exc}) and the Gemini fallback also failed ({gemini_exc})."
            ) from gemini_exc
        except EduGenieError as config_exc:
            raise EduGenieError(
                f"Local model failed ({local_exc}) and the Gemini fallback is unavailable ({config_exc})."
            ) from config_exc
