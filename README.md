# Hippocratic AI Take-Home Assignment

This project generates age-appropriate bedtime stories (ages 5–10) using a
storytelling LLM and an LLM-based judge that iteratively improves story quality.

---

## Architecture Overview

User Request
|
v
Story Generator (v1)
|
v
LLM Judge (scores + feedback)
|
v
Story Revision Loop
|
v
Final Bedtime Story

yaml
Copy code

---

## Key Features
- Structured prompting for story consistency
- LLM judge with rubric-based feedback
- Iterative refinement loop
- Safe API key handling
- Optional mock mode for offline runs

---

## Running the Project

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your_key_here"
python main.py

export USE_MOCK=true
python main.py

---

## 3️⃣ `DESIGN.md` (PROMPT + AGENT STRATEGY)

```md
# Design & Prompting Strategy

## Storytelling Prompt
The storyteller prompt enforces:
- Target age range (5–10)
- Emotional warmth
- Clear narrative arc
- Calm bedtime ending

## Judge Prompt
The judge evaluates:
- Age appropriateness
- Coherence
- Creativity
- Emotional warmth
- Ending quality

The judge returns structured, actionable feedback used for revision.

## Agent Loop
The system performs up to two judge-revision cycles to avoid over-generation
while still improving quality.

## Why This Works
Separating generation and evaluation mirrors human editorial workflows and
improves consistency and safety.
