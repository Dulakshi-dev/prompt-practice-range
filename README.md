# Prompt Practice Range

A prototype for Tai Labs: a graded sandbox where employees practice working
with an AI assistant on a realistic task, and get scored on **how they
prompted** — specificity, iteration quality, verification habits, efficiency —
not just on whether the final output looks fine.

Built for the Tai Labs final assessment by Dulakshi Gammanpila.

## Live demo

https://prompt-practice-range.mangoforest-74886e44.southeastasia.azurecontainerapps.io/

## What works today

- One scripted task scenario (client apology email for a delayed shipment)
- Live chat with an AI assistant to draft the email, capped at 6 turns
- Final-submission grading: the full transcript + final email is sent to an
  LLM-as-judge with a structured rubric, returning per-dimension scores (0-10),
  an overall score, a one-line verdict, and one strength / one improvement
- Single deployable service: FastAPI serves both the API and the static
  frontend, so there's exactly one thing to host

## What was cut for time

- Only one scenario (a real product needs a bank of scenarios per role)
- No accounts/persistence — each visit is a fresh attempt, nothing is saved
- No admin/manager view aggregating scores across a team
- Grading is single-pass (no self-consistency / multiple grading calls to
  reduce judge variance)

## What's next

- Scenario bank + role-based assignment (support, sales, eng, HR)
- Persist attempts (Postgres) so a manager can see a team's trend over time —
  this is the seed of the "Adoption Proof Dashboard" idea from the written
  answers
- Replace single LLM-judge grading with a rubric + 2-pass grading for
  consistency, and add a few worked "gold" transcripts to calibrate against

## Architecture

Browser (static HTML/CSS/JS)
|
v
FastAPI service (main.py)
├── GET /api/scenario -> task brief + turn limit
├── POST /api/chat -> proxies one turn to the assistant model (Groq)
├── POST /api/grade -> sends transcript + final email to Groq,
│ parses structured JSON rubric score
└── / -> serves static/ (index.html, app.js, style.css)


Model: `openai/gpt-oss-120b` via the Groq API (OpenAI-compatible chat
completions endpoint) — fast and capable enough for both the in-scenario
assistant and the grading pass. No database; state lives in the browser tab
for the duration of one attempt.

## Run locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...   # get one free at console.groq.com/keys
uvicorn main:app --reload
```

Then open http://localhost:8000

## Deploy (Azure Container Apps — how the live demo above is running)

1. Push this repo to GitHub (public).
2. In the Azure portal, create a Container App pointed at this repo, using
   the included `Dockerfile`.
3. Enable ingress: accepting traffic from anywhere, target port `8000`.
4. Connect Deployment Center to this GitHub repo (branch `main`) so it
   builds and deploys automatically via GitHub Actions on every push.
5. Add an environment variable on the container: `GROQ_API_KEY` = your key.
6. Azure gives you a public `.azurecontainerapps.io` URL — that's the live
   link.

### Alternative: Render (free tier, no login wall for visitors)

1. Push this repo to GitHub (public).
2. Go to https://render.com → New → Web Service → connect the repo.
3. Environment: **Docker** (it will pick up the included `Dockerfile`
   automatically) — or if you'd rather skip Docker, choose Python, with
   Build Command `pip install -r requirements.txt` and Start Command
   `uvicorn main:app --host 0.0.0.0 --port $PORT`.
4. Add an environment variable: `GROQ_API_KEY` = your key.
5. Deploy. Render gives you a public URL like
   `https://prompt-practice-range.onrender.com`.

Free-tier note (Render): the service spins down after inactivity and takes
~30-50s to wake on the next visit.

## How to know it's working

- `GET /health` returns `{"status": "ok", "model_key_configured": true}` —
  confirms the service is up and the API key is present without exposing it.
- Manual smoke test: load the page, send 1-2 chat turns, submit a final
  email, confirm a score renders. This is the fixed test path used to verify
  every deploy.
