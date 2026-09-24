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
