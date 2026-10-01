"""EduGenie - Google Gemini powered learning assistant (FastAPI backend).

Run with:  uvicorn main:app --reload
Open:      http://127.0.0.1:8000
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from explanation_module import explain_topic
from gemini_client import EduGenieError, get_model_name, has_api_key
from learning_path import get_learning_recommendations
from qna import answer_question_with_gemini
from quiz_module import generate_quiz
from summary_module import summarize_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent
MAX_INPUT_CHARS = 20000

app = FastAPI(title="EduGenie", description="Google Gemini powered learning assistant", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ------------------------------------------------------------------ helpers
@app.exception_handler(EduGenieError)
async def edugenie_error_handler(request: Request, exc: EduGenieError):
    """Turn any module error into a clean JSON message the frontend can display."""
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})


async def read_field(request: Request, field: str):
    """Read a string field from a JSON body. Returns (value, error_response)."""
    try:
        data = await request.json()
    except Exception:
        return None, JSONResponse(status_code=400, content={"error": "Request body must be valid JSON."})
    if not isinstance(data, dict):
        return None, JSONResponse(status_code=400, content={"error": "Request body must be a JSON object."})

    value = data.get(field)
    value = value.strip() if isinstance(value, str) else ""
    return value, None


def too_long(value: str):
    if len(value) > MAX_INPUT_CHARS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Input is too long (maximum {MAX_INPUT_CHARS} characters)."},
        )
    return None


# ------------------------------------------------------------------ pages
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
async def health():
    """Quick status check: handy for testing the setup."""
    return {"status": "ok", "gemini_model": get_model_name(), "gemini_key_configured": has_api_key()}


# ------------------------------------------------------------------ API routes
# Q&A - GET API using Gemini
@app.get("/qa")
async def answer_question(question: str = Query(..., min_length=1, max_length=MAX_INPUT_CHARS)):
    question = question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Please provide a question."})
    answer = await run_in_threadpool(answer_question_with_gemini, question)
    return {"answer": answer}


# Explanation - POST API (local LaMini-Flan-T5, falls back to Gemini)
@app.post("/explain")
@app.post("/explain/")
async def explain_api(request: Request):
    topic, error = await read_field(request, "topic")
    if error is not None:
        return error
    if not topic:
        return JSONResponse(status_code=400, content={"error": "Please provide a topic."})
    if (error := too_long(topic)) is not None:
        return error
    explanation = await run_in_threadpool(explain_topic, topic)
    return {"topic": topic, "explanation": explanation}


# Summarization - POST API
@app.post("/summarize")
@app.post("/summarize/")
async def summarize_api(request: Request):
    text, error = await read_field(request, "text")
    if error is not None:
        return error
    if not text:
        return JSONResponse(status_code=400, content={"error": "Please provide text to summarize."})
    if (error := too_long(text)) is not None:
        return error
    summary = await run_in_threadpool(summarize_text, text)
    return {"summary": summary}


# Quiz generation - POST API
@app.post("/quiz")
@app.post("/quiz/")
async def quiz_api(request: Request):
    text, error = await read_field(request, "text")
    if error is not None:
        return error
    if not text:
        return JSONResponse(status_code=400, content={"error": "Please provide text for quiz."})
    if (error := too_long(text)) is not None:
        return error
    quiz = await run_in_threadpool(generate_quiz, text)
    return JSONResponse(content={"quiz": quiz})


# Learning recommendations - GET API
@app.get("/learn/recommendations")
async def learning_recommendation_api(topic: str = Query(..., min_length=1, max_length=MAX_INPUT_CHARS)):
    topic = topic.strip()
    if not topic:
        return JSONResponse(status_code=400, content={"error": "Please provide a topic."})
    recommendation = await run_in_threadpool(get_learning_recommendations, topic)
    return {"topic": topic, "recommendation": recommendation}
