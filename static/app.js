"use strict";

/* ------------------------------------------------------------------
   Task definitions: one entry per option in the dropdown.
   ------------------------------------------------------------------ */
const TASKS = {
    qna: {
        label: "Ask EduGenie a question:",
        placeholder: "Which is the largest ocean?",
        button: "Get Answer",
        title: "Answer",
        hint: "",
        request: (text) => fetch("/qa?question=" + encodeURIComponent(text)),
        render: (data, body) => renderMarkdown(body, data.answer),
    },
    explain: {
        label: "Which concept needs an explanation?",
        placeholder: "Photosynthesis",
        button: "Explain",
        title: "Explanation",
        hint: "The first explanation can take a few minutes: the local LaMini-Flan-T5 model is downloaded and loaded once.",
        request: (text) => postJSON("/explain/", { topic: text }),
        render: (data, body) => renderMarkdown(body, data.explanation),
    },
    quiz: {
        label: "Enter a topic or paste a passage to be quizzed on:",
        placeholder: "Solar System",
        button: "Generate Quiz",
        title: "Quiz",
        hint: "You will get 3 multiple-choice questions with 4 options each.",
        request: (text) => postJSON("/quiz", { text: text }),
        render: (data, body) => renderQuiz(body, data.quiz),
    },
    summary: {
        label: "Paste the text you want summarized:",
        placeholder: "Paste long content to summarize...",
        button: "Summarize",
        title: "Summary",
        hint: "",
        request: (text) => postJSON("/summarize/", { text: text }),
        render: (data, body) => renderMarkdown(body, data.summary),
    },
    path: {
        label: "What do you want to learn?",
        placeholder: "SQL",
        button: "Recommend Path",
        title: "Learning Path",
        hint: "Get a beginner-to-advanced plan with timelines and resources.",
        request: (text) => fetch("/learn/recommendations?topic=" + encodeURIComponent(text)),
        render: (data, body) => renderMarkdown(body, data.recommendation),
    },
};

const form = document.getElementById("taskForm");
const taskSelect = document.getElementById("task");
const inputLabel = document.getElementById("inputLabel");
const userInput = document.getElementById("userInput");
const hint = document.getElementById("hint");
const submitBtn = document.getElementById("submitBtn");
const resultCard = document.getElementById("resultCard");
const resultTitle = document.getElementById("resultTitle");
const resultBody = document.getElementById("resultBody");

function postJSON(url, payload) {
    return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

/* ------------------------------------------------------------------
   UI updates
   ------------------------------------------------------------------ */
function applyTask() {
    const task = TASKS[taskSelect.value];
    inputLabel.textContent = task.label;
    userInput.placeholder = task.placeholder;
    submitBtn.textContent = task.button;
    hint.textContent = task.hint;
}

function showLoading() {
    resultBody.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "loading";
    const spinner = document.createElement("div");
    spinner.className = "spinner";
    const msg = document.createElement("span");
    msg.textContent = "EduGenie is thinking...";
    wrap.append(spinner, msg);
    resultBody.appendChild(wrap);
}

function showError(message) {
    resultBody.innerHTML = "";
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = message;
    resultBody.appendChild(box);
}

/* ------------------------------------------------------------------
   Tiny, safe Markdown renderer (headings, bold, italics, code, lists).
   All text is HTML-escaped first, so model output cannot inject markup.
   ------------------------------------------------------------------ */
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function inlineMarkdown(escaped) {
    return escaped
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[\s(])\*([^\s*][^*]*?)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
}

function markdownToHtml(source) {
    const lines = escapeHtml(source).split(/\r?\n/);
    const out = [];
    let listType = null;

    const closeList = () => {
        if (listType) {
            out.push("</" + listType + ">");
            listType = null;
        }
    };

    for (const rawLine of lines) {
        const line = rawLine.replace(/\s+$/, "");

        if (!line.trim()) {
            closeList();
            continue;
        }

        const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
        if (heading) {
            closeList();
            out.push("<h4>" + inlineMarkdown(heading[1]) + "</h4>");
            continue;
        }

        const bullet = line.match(/^(\s*)[*\-+]\s+(.*)$/);
        const numbered = line.match(/^(\s*)\d+[.)]\s+(.*)$/);
        if (bullet || numbered) {
            const type = bullet ? "ul" : "ol";
            const match = bullet || numbered;
            if (listType !== type) {
                closeList();
                out.push("<" + type + ">");
                listType = type;
            }
            const indentLevel = Math.floor(match[1].length / 2);
            const style = indentLevel ? ' style="margin-left:' + indentLevel * 18 + 'px"' : "";
            out.push("<li" + style + ">" + inlineMarkdown(match[2]) + "</li>");
            continue;
        }

        closeList();
        const standaloneBold = line.match(/^\s*\*\*(.+?)\*\*:?\s*$/);
        if (standaloneBold) {
            out.push("<h4>" + inlineMarkdown(standaloneBold[1]) + "</h4>");
        } else {
            out.push("<p>" + inlineMarkdown(line.trim()) + "</p>");
        }
    }
    closeList();
    return out.join("\n");
}

function renderMarkdown(container, text) {
    container.innerHTML = markdownToHtml(String(text || ""));
}

/* ------------------------------------------------------------------
   Interactive quiz: shows right/wrong instantly and reveals the correct answer.
   ------------------------------------------------------------------ */
function renderQuiz(container, quiz) {
    container.innerHTML = "";
    if (!Array.isArray(quiz) || quiz.length === 0) {
        showError("No quiz questions were returned. Please try again.");
        return;
    }

    let answered = 0;
    let correctCount = 0;
    const scoreEl = document.createElement("div");
    scoreEl.className = "score";

    quiz.forEach((item, index) => {
        const block = document.createElement("div");
        block.className = "quiz-question";

        const heading = document.createElement("h3");
        heading.textContent = (index + 1) + ". " + item.question;
        block.appendChild(heading);

        const feedback = document.createElement("div");
        feedback.className = "feedback";
        const buttons = [];

        item.options.forEach((option, optionIndex) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "option";
            btn.textContent = String.fromCharCode(65 + optionIndex) + ". " + option;
            btn.addEventListener("click", () => {
                const isCorrect = option === item.answer;
                buttons.forEach((b) => (b.disabled = true));
                btn.classList.add(isCorrect ? "correct" : "wrong");

                if (isCorrect) {
                    correctCount += 1;
                    feedback.className = "feedback ok";
                    feedback.textContent = "✅ Correct!";
                } else {
                    const right = buttons[item.options.indexOf(item.answer)];
                    if (right) right.classList.add("correct");
                    feedback.className = "feedback no";
                    feedback.textContent = "❌ Not quite. The correct answer is: " + item.answer;
                }

                answered += 1;
                if (answered === quiz.length) {
                    scoreEl.textContent = "Your score: " + correctCount + " / " + quiz.length;
                }
            });
            buttons.push(btn);
            block.appendChild(btn);
        });

        block.appendChild(feedback);
        container.appendChild(block);
    });

    container.appendChild(scoreEl);
}

/* ------------------------------------------------------------------
   Form submission
   ------------------------------------------------------------------ */
async function handleSubmit(event) {
    event.preventDefault();

    const text = userInput.value.trim();
    if (!text) return;

    const task = TASKS[taskSelect.value];
    resultTitle.textContent = task.title;
    resultCard.classList.remove("hidden");
    showLoading();
    submitBtn.disabled = true;

    try {
        const response = await task.request(text);
        let data = null;
        try {
            data = await response.json();
        } catch (_) {
            /* non-JSON response; handled below */
        }

        if (!response.ok) {
            let message = "Something went wrong (HTTP " + response.status + ").";
            if (data && data.error) message = data.error;
            else if (data && data.detail) message = typeof data.detail === "string" ? data.detail : "Invalid input.";
            showError(message);
            return;
        }

        resultBody.innerHTML = "";
        task.render(data, resultBody);
    } catch (err) {
        showError("Could not reach the EduGenie server. Is it running? (" + err.message + ")");
    } finally {
        submitBtn.disabled = false;
        resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

taskSelect.addEventListener("change", applyTask);
form.addEventListener("submit", handleSubmit);

// Ctrl/Cmd + Enter submits from the textarea.
userInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        form.requestSubmit();
    }
});

applyTask();
