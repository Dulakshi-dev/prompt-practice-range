"""
Prompt Practice Range — backend

A single FastAPI service that:
  1. Serves the static frontend (index.html / app.js / style.css)
  2. Proxies the "practice" chat between the employee and the AI assistant
     for a fixed task scenario
  3. Grades the *process* (how they prompted), not just the final output,
     using a structured rubric and an LLM-as-judge call

Model provider: Groq (Llama 3.3 70B) — free-tier friendly, fast, good enough
for both the in-scenario assistant and the grading pass.
Swap GROQ_API_KEY / MODEL below for a different provider if needed.
"""

import os
import json
import time
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

app = FastAPI(title="Prompt Practice Range")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# The task scenario. In a real product this would be a bank of scenarios
# picked per-role; for the prototype we ship one strong scenario end to end.
# ---------------------------------------------------------------------------
SCENARIO = {
    "id": "shipment-delay-email",
    "title": "Client apology email",
    "brief": (
        "A key client's order (Order #48210) is going to arrive 9 days late "
        "because of a supplier issue on your end. Use the AI assistant below "
        "to help you draft a professional email to the client explaining the "
        "delay, keeping the relationship intact, and offering a fair "
        "resolution. You have up to 6 messages with the assistant. When "
        "you're happy with the result, paste your FINAL email into the box "
        "at the bottom and submit."
    ),
    "max_turns": 6,
}

SYSTEM_PROMPT_ASSISTANT = (
    "You are a helpful AI writing assistant embedded in a workplace tool. "
    "An employee is using you to help draft a client email for this task:\n\n"
    f"{SCENARIO['brief']}\n\n"
    "Behave like a realistic, competent assistant: if the employee gives you "
    "a vague instruction (e.g. 'write the email'), don't silently invent "
    "specific facts like discount percentages or dates — either ask a brief "
    "clarifying question or clearly flag the placeholders you used. If they "
    "give you specifics, use them. Keep replies focused and not overly long."
)

GRADER_SYSTEM_PROMPT = """You are grading how well an employee used an AI assistant to complete a workplace writing task — you are scoring their PROCESS, not just whether the final email reads nicely.

Score each of these 0-10, as integers, based on the full transcript:

- specificity: Did they give the assistant concrete, useful context (client tone, specific facts, constraints) rather than vague one-line requests, especially as the conversation went on?
- iteration_quality: Did they refine intelligently across turns (pushing back, correcting, narrowing) rather than either accepting the first draft blindly or repeating the same request without adjusting?
- verification_habit: Is there evidence they checked the assistant's output for invented facts/placeholders and corrected or flagged them, rather than passing along whatever the AI wrote unchecked?
- efficiency: Did they reach a usable result without wasting turns on redundant or overly narrow requests?

Also write:
- one_line_verdict: one sentence, direct, on their overall prompting skill.
- strength: the single most notable thing they did well (1 sentence).
- improve: the single most useful thing to improve next time (1 sentence).

Respond with ONLY valid JSON, no markdown fences, in exactly this shape:
{"specificity": int, "iteration_quality": int, "verification_habit": int, "efficiency": int, "one_line_verdict": str, "strength": str, "improve": str}
"""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    history: List[ChatTurn]


class ChatResponse(BaseModel):
    reply: str
    turns_used: int
    turns_remaining: int


class GradeRequest(BaseModel):
    history: List[ChatTurn]
    final_email: str


class GradeResponse(BaseModel):
    specificity: int
    iteration_quality: int
    verification_habit: int
    efficiency: int
    overall: float
    one_line_verdict: str
    strength: str
    improve: str


async def call_groq(system: str, messages: list, max_tokens: int = 600, temperature: float = 0.7) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is missing GROQ_API_KEY. Set it as an environment variable.",
        )
    full_messages = [{"role": "system", "content": system}] + messages
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "messages": full_messages,
                "temperature": temperature,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Model API error: {resp.text[:300]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail=f"Unexpected model response shape: {str(data)[:300]}")


@app.get("/api/scenario")
def get_scenario():
    return SCENARIO


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    user_turns = sum(1 for t in req.history if t.role == "user")
    if user_turns == 0:
        raise HTTPException(status_code=400, detail="No user message provided.")
    if user_turns > SCENARIO["max_turns"]:
        raise HTTPException(status_code=400, detail="Turn limit reached for this scenario.")

    messages = [{"role": t.role, "content": t.content} for t in req.history]
    reply = await call_groq(SYSTEM_PROMPT_ASSISTANT, messages)

    return ChatResponse(
        reply=reply,
        turns_used=user_turns,
        turns_remaining=max(0, SCENARIO["max_turns"] - user_turns),
    )


@app.post("/api/grade", response_model=GradeResponse)
async def grade(req: GradeRequest):
    if not req.final_email.strip():
        raise HTTPException(status_code=400, detail="Final email is empty.")

    transcript_lines = [f"{t.role.upper()}: {t.content}" for t in req.history]
    transcript = "\n\n".join(transcript_lines)

    grading_input = (
        f"TASK GIVEN TO EMPLOYEE:\n{SCENARIO['brief']}\n\n"
        f"FULL TRANSCRIPT WITH THE AI ASSISTANT:\n{transcript}\n\n"
        f"EMPLOYEE'S FINAL SUBMITTED EMAIL:\n{req.final_email}"
    )

    raw = await call_groq(
        GRADER_SYSTEM_PROMPT,
        [{"role": "user", "content": grading_input}],
        max_tokens=500,
        temperature=0.2,
    )

    # Be defensive about stray markdown fences even though we asked for none
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"Grader returned non-JSON: {raw[:300]}")

    scores = [
        parsed["specificity"],
        parsed["iteration_quality"],
        parsed["verification_habit"],
        parsed["efficiency"],
    ]
    overall = round(sum(scores) / len(scores), 1)

    return GradeResponse(
        specificity=parsed["specificity"],
        iteration_quality=parsed["iteration_quality"],
        verification_habit=parsed["verification_habit"],
        efficiency=parsed["efficiency"],
        overall=overall,
        one_line_verdict=parsed["one_line_verdict"],
        strength=parsed["strength"],
        improve=parsed["improve"],
    )


@app.get("/health")
def health():
    return {"status": "ok", "time": time.time(), "model_key_configured": bool(GROQ_API_KEY)}


# Serve frontend last so /api/* routes above take priority
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
