# EduGenie: Google Gemini Powered Learning Assistant

A lightweight AI learning assistant built with **FastAPI** and a plain **HTML + CSS + JS** frontend.

| Feature | Endpoint | Model |
|---|---|---|
| Ask a question | `GET /qa?question=...` | Gemini |
| Explain a concept | `POST /explain/` `{"topic": "..."}` | LaMini-Flan-T5-783M (local), Gemini fallback |
| Generate a 3-question quiz | `POST /quiz` `{"text": "..."}` | Gemini |
| Summarize text | `POST /summarize/` `{"text": "..."}` | Gemini |
| Learning path | `GET /learn/recommendations?topic=...` | Gemini |
| Health check | `GET /health` | - |

## Project structure

```
EduGenie/
├── main.py                 # FastAPI app and routes
├── gemini_client.py        # Shared Gemini client, error types, .env loading
├── explanation_module.py   # Concept explanation (local LaMini-Flan-T5)
├── qna.py                  # Question answering
├── quiz_module.py          # Quiz generation + JSON validation
├── summary_module.py       # Summarization
├── learning_path.py        # Learning recommendations
├── templates/index.html    # Frontend page
├── static/style.css        # Styling
├── static/app.js           # Frontend logic (API calls, quiz UI)
├── tests/                  # Automated tests
├── requirements.txt
├── .env.example            # Copy to .env and add your key
└── .vscode/                # Debug + test settings
```

See the setup and run steps in the chat answer, or follow the quick version below.

## Quick start

```bash
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env   (then edit .env)
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

## Tests

```bash
pytest -v                              # offline tests (AI calls are mocked)
pytest tests/test_live_gemini.py -v    # real Gemini calls (needs GEMINI_API_KEY)
```
