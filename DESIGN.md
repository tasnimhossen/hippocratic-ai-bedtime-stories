# DESIGN — Prompting + Agent Strategy

## Goals
- Produce a bedtime-safe story for ages **5–10**
- Use prompting techniques for consistent quality
- Add an **LLM judge** that improves the story
- Keep the system explainable and lightweight

## Components

### 1) Spec Builder (Planner Prompt)
The first prompt asks the model for a compact **JSON** plan (`StorySpec`) including:
- age band (5–7 vs 8–10)
- tone (cozy/silly/adventurous/calm)
- characters, setting, theme
- length (short/medium)
- constraints (bedtime safety, calming ending)

Why: creates a stable target for later steps and makes behavior more consistent.

### 2) Storyteller Prompt
The storyteller prompt uses the spec and enforces:
- age appropriateness
- clear arc (beginning/middle/end)
- calm bedtime ending
- simple language and short paragraphs

### 3) LLM Judge Prompt
The judge returns **strict, structured JSON** with:
- rubric scores (1–10)
- `must_fix` safety/clarity issues
- `rewrite_instructions` (actionable bullets)

The judge is run with low temperature to be deterministic.

### 4) Revision Loop
We rewrite the full story using judge instructions, repeating up to 2 times. This mirrors an editor workflow and improves:
- coherence
- clarity
- bedtime-appropriateness
- narrative arc

## Safety / Age Appropriateness
We bake in constraints (no violence/gore/scary imagery; no adult topics; calm ending) regardless of user request.

## Surprise Factor
- The system includes an **offline mock mode** (`USE_MOCK=true`) so reviewers can run without a key.
- The judge outputs transparent rubric scores and specific instructions.
