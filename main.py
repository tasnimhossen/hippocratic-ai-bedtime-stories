#!/usr/bin/env python3
"""
Hippocratic AI Take-Home
Storyteller + LLM Judge loop (gpt-3.5-turbo only)

Run:
  export OPENAI_API_KEY="..."
  python main.py

Offline:
  export USE_MOCK=true
  python main.py
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import openai

MODEL = "gpt-3.5-turbo"  # Do not change (per assignment)
DEFAULT_MAX_TOKENS_STORY = 900
DEFAULT_MAX_TOKENS_JUDGE = 500
MAX_REVISIONS = 2

USE_MOCK = os.getenv("USE_MOCK", "false").lower() in ("1", "true", "yes")


@dataclass
class StorySpec:
    age_band: str                 # "5-7" or "8-10"
    tone: str                     # cozy / silly / adventurous / calm
    characters: List[str]
    setting: str
    theme: str                    # friendship / bravery / kindness / curiosity
    length: str                   # short / medium
    constraints: List[str]        # safety, bedtime-appropriate constraints


@dataclass
class JudgeResult:
    scores: Dict[str, int]        # per rubric category, 1-10
    overall: int                  # 1-10
    must_fix: List[str]
    nice_to_fix: List[str]
    rewrite_instructions: List[str]
    raw: str                      # raw model response for transparency


# ----------------------------
# Prompt building
# ----------------------------

def build_spec_prompt(user_request: str) -> str:
    return f"""
You are a helpful assistant that turns a bedtime-story request into a compact story plan.
Audience: children ages 5–10.
Output MUST be valid JSON only (no markdown), matching this schema:

{{
  "age_band": "5-7" | "8-10",
  "tone": "cozy" | "silly" | "adventurous" | "calm",
  "characters": ["..."],
  "setting": "...",
  "theme": "friendship" | "bravery" | "kindness" | "curiosity",
  "length": "short" | "medium",
  "constraints": ["..."]
}}

Guidance:
- Choose "5-7" if request is very simple; otherwise "8-10".
- Keep bedtime-safe: no gore, no cruelty, no adult topics.
- Endings should feel calm and reassuring.

USER REQUEST:
{user_request}
""".strip()


def build_story_prompt(spec: StorySpec, user_request: str) -> str:
    chars = ", ".join(spec.characters) if spec.characters else "a kind main character"
    constraints = "\n- ".join([""] + spec.constraints) if spec.constraints else ""
    return f"""
You are a warm, imaginative storyteller writing a bedtime story for children ages {spec.age_band.replace('-', ' to ')}.

Hard requirements:
- Age-appropriate for ages 5–10 (no violence, gore, or scary imagery).
- Clear beginning, middle, and end.
- Gentle tone suitable for bedtime.
- Keep language simple and vivid; short paragraphs.
- End with a calming closing line that helps a child feel safe.

Story plan:
- Tone: {spec.tone}
- Characters: {chars}
- Setting: {spec.setting}
- Theme: {spec.theme}
- Length: {spec.length}
- Constraints:{constraints}

Write the full story now. Also include a short title on the first line.
USER REQUEST (for reference):
{user_request}
""".strip()


def build_judge_prompt(spec: StorySpec, story_text: str) -> str:
    return f"""
You are an expert children's editor judging a bedtime story for ages 5–10.
You must be strict, specific, and helpful.

Return ONLY valid JSON (no markdown), with this exact schema:
{{
  "scores": {{
    "age_appropriateness": 1-10,
    "coherence": 1-10,
    "creativity": 1-10,
    "warmth": 1-10,
    "bedtime_ending": 1-10,
    "language_clarity": 1-10
  }},
  "overall": 1-10,
  "must_fix": ["..."],
  "nice_to_fix": ["..."],
  "rewrite_instructions": ["..."]
}}

Rules:
- Be aligned to the plan: tone={spec.tone}, theme={spec.theme}, length={spec.length}.
- "must_fix" should list any safety/age issues, confusing parts, or missing arc.
- "rewrite_instructions" must be actionable bullets (5–10 items), referencing what to change.
- Do NOT rewrite the story here.

STORY:
{story_text}
""".strip()


def build_revision_prompt(spec: StorySpec, story_text: str, judge: JudgeResult) -> str:
    bullets = "\n".join([f"- {b}" for b in judge.rewrite_instructions])
    return f"""
You are revising a bedtime story for ages 5–10.
Apply ALL "must_fix" and as many "nice_to_fix" as possible.
Keep the same core characters and setting unless instructed otherwise.

Target plan:
- Tone: {spec.tone}
- Theme: {spec.theme}
- Length: {spec.length}
- Age band: {spec.age_band}

Rewrite instructions:
{bullets}

Rewrite the FULL story (with title on first line). Ensure a calm bedtime ending.
STORY TO REVISE:
{story_text}
""".strip()


# ----------------------------
# Model call + utilities
# ----------------------------

def _require_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it locally (recommended) or use USE_MOCK=true for offline mode."
        )
    return key


def call_model(prompt: str, *, max_tokens: int, temperature: float) -> str:
    """
    Calls gpt-3.5-turbo via the legacy openai==0.28.x SDK (ChatCompletion).
    """
    if USE_MOCK:
        return mock_model(prompt)

    openai.api_key = _require_api_key()
    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"]  # type: ignore


def extract_json_object(text: str) -> Dict[str, Any]:
    """
    Robustly extract a JSON object from a model response.
    Handles cases where the model accidentally adds extra text.
    """
    text = text.strip()
    # If it's already pure JSON, parse directly
    try:
        return json.loads(text)
    except Exception:
        pass

    # Otherwise, try to find the first {...} block
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON object in response:\n{text}")
    return json.loads(match.group(0))


def coerce_int_score(v: Any) -> int:
    try:
        iv = int(v)
    except Exception:
        iv = 0
    return max(1, min(10, iv))


def parse_story_spec(raw: str) -> StorySpec:
    obj = extract_json_object(raw)

    age_band = obj.get("age_band", "8-10")
    if age_band not in ("5-7", "8-10"):
        age_band = "8-10"

    tone = obj.get("tone", "cozy")
    if tone not in ("cozy", "silly", "adventurous", "calm"):
        tone = "cozy"

    theme = obj.get("theme", "kindness")
    if theme not in ("friendship", "bravery", "kindness", "curiosity"):
        theme = "kindness"

    length = obj.get("length", "medium")
    if length not in ("short", "medium"):
        length = "medium"

    characters = obj.get("characters", [])
    if not isinstance(characters, list):
        characters = []

    setting = obj.get("setting", "a cozy place")
    constraints = obj.get("constraints", [])
    if not isinstance(constraints, list):
        constraints = []

    # Always enforce bedtime-safe constraints even if model forgets
    safety_defaults = [
        "Keep it bedtime-safe: no gore, no cruelty, no frightening imagery.",
        "No adult topics; keep relationships child-appropriate.",
        "End on a calm, reassuring note."
    ]
    constraints = list(dict.fromkeys(constraints + safety_defaults))

    return StorySpec(
        age_band=age_band,
        tone=tone,
        characters=[str(c) for c in characters][:6],
        setting=str(setting)[:120],
        theme=theme,
        length=length,
        constraints=[str(c)[:200] for c in constraints][:8],
    )


def parse_judge_result(raw: str) -> JudgeResult:
    obj = extract_json_object(raw)
    scores = obj.get("scores", {}) if isinstance(obj.get("scores", {}), dict) else {}

    rubric = {
        "age_appropriateness": coerce_int_score(scores.get("age_appropriateness", 7)),
        "coherence": coerce_int_score(scores.get("coherence", 7)),
        "creativity": coerce_int_score(scores.get("creativity", 7)),
        "warmth": coerce_int_score(scores.get("warmth", 7)),
        "bedtime_ending": coerce_int_score(scores.get("bedtime_ending", 7)),
        "language_clarity": coerce_int_score(scores.get("language_clarity", 7)),
    }
    overall = coerce_int_score(obj.get("overall", round(sum(rubric.values()) / len(rubric))))

    must_fix = obj.get("must_fix", [])
    nice_to_fix = obj.get("nice_to_fix", [])
    rewrite_instructions = obj.get("rewrite_instructions", [])

    if not isinstance(must_fix, list):
        must_fix = []
    if not isinstance(nice_to_fix, list):
        nice_to_fix = []
    if not isinstance(rewrite_instructions, list):
        rewrite_instructions = []

    # Ensure we always have some rewrite guidance
    if len(rewrite_instructions) < 3:
        rewrite_instructions = [
            "Ensure the story has a clear beginning, middle, and end.",
            "Use short paragraphs and simple sentences for ages 5–10.",
            "End with a calm, reassuring bedtime closing line.",
        ] + rewrite_instructions

    return JudgeResult(
        scores=rubric,
        overall=overall,
        must_fix=[str(x) for x in must_fix][:10],
        nice_to_fix=[str(x) for x in nice_to_fix][:10],
        rewrite_instructions=[str(x) for x in rewrite_instructions][:12],
        raw=raw,
    )


# ----------------------------
# Main pipeline
# ----------------------------

def generate_story_with_judge(user_request: str, *, show_scores: bool = True) -> Tuple[str, StorySpec, List[JudgeResult]]:
    """
    1) Build spec
    2) Story v1
    3) Judge -> revise (up to MAX_REVISIONS)
    """
    spec_raw = call_model(build_spec_prompt(user_request), max_tokens=450, temperature=0.2)
    spec = parse_story_spec(spec_raw)

    story = call_model(build_story_prompt(spec, user_request), max_tokens=DEFAULT_MAX_TOKENS_STORY, temperature=0.7)
    judges: List[JudgeResult] = []

    for _ in range(MAX_REVISIONS):
        judge_raw = call_model(build_judge_prompt(spec, story), max_tokens=DEFAULT_MAX_TOKENS_JUDGE, temperature=0.0)
        judge = parse_judge_result(judge_raw)
        judges.append(judge)

        story = call_model(build_revision_prompt(spec, story, judge), max_tokens=DEFAULT_MAX_TOKENS_STORY, temperature=0.7)

    if show_scores and judges:
        last = judges[-1]
        print("\n[Judge scores] " + " | ".join([f"{k}:{v}" for k, v in last.scores.items()]) + f" | overall:{last.overall}")
        if last.must_fix:
            print("[Must fix] " + "; ".join(last.must_fix[:4]))

    return story.strip(), spec, judges


def ask_for_tweak() -> Optional[str]:
    print("\nOptional: Want any changes? (e.g., 'shorter', 'more silly', 'add a bunny friend')")
    tweak = input("Tweak (or press Enter to finish): ").strip()
    return tweak or None


def apply_user_tweak(original_request: str, tweak: str) -> str:
    return f"{original_request}\n\nUser requested changes: {tweak}"


# ----------------------------
# Mock mode
# ----------------------------

def mock_model(prompt: str) -> str:
    """
    Deterministic mock outputs so reviewers can run without a key.
    Very simple, but keeps the pipeline functioning.
    """
    if '"age_band"' in prompt and '"tone"' in prompt:
        return json.dumps({
            "age_band": "5-7",
            "tone": "cozy",
            "characters": ["Alice", "Bob the cat"],
            "setting": "a little cottage near a moonlit garden",
            "theme": "friendship",
            "length": "short",
            "constraints": ["No scary scenes", "Gentle bedtime tone"]
        })
    if "Return ONLY valid JSON" in prompt and "scores" in prompt:
        return json.dumps({
            "scores": {
                "age_appropriateness": 9,
                "coherence": 8,
                "creativity": 8,
                "warmth": 9,
                "bedtime_ending": 9,
                "language_clarity": 8
            },
            "overall": 9,
            "must_fix": [],
            "nice_to_fix": ["Add one sensory detail", "Give the cat a funny gentle habit"],
            "rewrite_instructions": [
                "Add one cozy sensory detail (sound/smell).",
                "Add a gentle funny habit for Bob the cat.",
                "Keep the ending calm and reassuring."
            ]
        })
    if "Rewrite the FULL story" in prompt:
        return "Moonlight Tea and the Purring Promise\n\nAlice and Bob the cat listened to the soft *whoosh* of the night breeze...\n\nThe end. Sweet dreams."
    return "A Cozy Little Story\n\nOnce upon a time...\n\nThe end."


def main() -> None:
    print("Bedtime Storyteller (ages 5–10) — with LLM Judge\n")
    if USE_MOCK:
        print("[Running in USE_MOCK=true mode — no API calls will be made]\n")

    user_request = input("What kind of story do you want to hear? ").strip()
    if not user_request:
        user_request = "A cozy bedtime story about a child and a friendly cat who find a lost star."

    story, spec, _judges = generate_story_with_judge(user_request, show_scores=True)

    print("\n" + "=" * 60)
    print(story)
    print("=" * 60)

    tweak = ask_for_tweak()
    if tweak:
        story2, _spec2, _ = generate_story_with_judge(apply_user_tweak(user_request, tweak), show_scores=True)
        print("\n" + "=" * 60)
        print(story2)
        print("=" * 60)


if __name__ == "__main__":
    main()
