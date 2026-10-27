"""Unit tests for parse_llm_json helper and LLM response parsing."""
import json
import pytest
from llm.provider import parse_llm_json, LLMStructuredOutputError
from llm.providers.claude_provider import ClaudeProvider


def test_parse_pure_json():
    raw = '{"score": 85, "summary": "Good deck", "findings": []}'
    res = parse_llm_json(raw)
    assert res["score"] == 85
    assert res["summary"] == "Good deck"


def test_parse_json_markdown_block():
    raw = """```json
{
  "score": 90,
  "summary": "Great deck",
  "findings": []
}
```"""
    res = parse_llm_json(raw)
    assert res["score"] == 90
    assert res["summary"] == "Great deck"


def test_parse_json_with_preamble_and_markdown():
    raw = """Here is the validation analysis in JSON format:

```json
{
  "score": 75,
  "summary": "Needs minor fixes",
  "findings": []
}
```

Hope this helps!"""
    res = parse_llm_json(raw)
    assert res["score"] == 75
    assert res["summary"] == "Needs minor fixes"


def test_parse_json_array():
    raw = """[{"id": 1}, {"id": 2}]"""
    res = parse_llm_json(raw)
    assert len(res) == 2
    assert res[0]["id"] == 1


def test_parse_single_quoted_dict():
    raw = "{'score': 85, 'summary': 'Good deck', 'findings': [{'slide': 1, 'applied': true}]}"
    res = parse_llm_json(raw)
    assert res["score"] == 85
    assert res["summary"] == "Good deck"
    assert res["findings"][0]["applied"] is True


def test_parse_trailing_comma():
    raw = '{"score": 85, "summary": "Good deck", "findings": [],}'
    res = parse_llm_json(raw)
    assert res["score"] == 85


def test_parse_invalid_json_raises():
    raw = "Not a JSON string at all"
    with pytest.raises(json.JSONDecodeError):
        parse_llm_json(raw)
