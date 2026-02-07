import os
import pytest

# Import after setting USE_MOCK so tests never call the network
os.environ["USE_MOCK"] = "true"

import main  # noqa: E402


def test_extract_json_object_parses_embedded_json():
    txt = "hello\n{ \"a\": 1 }\nbye"
    assert main.extract_json_object(txt)["a"] == 1


def test_parse_story_spec_defaults_and_constraints():
    raw = '{"age_band":"5-7","tone":"cozy","characters":["A"],"setting":"home","theme":"friendship","length":"short","constraints":[] }'
    spec = main.parse_story_spec(raw)
    assert spec.age_band in ("5-7", "8-10")
    assert len(spec.constraints) >= 1  # safety defaults added


def test_pipeline_runs_in_mock_mode():
    story, spec, judges = main.generate_story_with_judge("A story about Alice and Bob the cat.", show_scores=False)
    assert isinstance(story, str) and len(story) > 0
    assert spec.theme in ("friendship", "bravery", "kindness", "curiosity")
    assert len(judges) >= 1
