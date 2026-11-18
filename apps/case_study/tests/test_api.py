import pytest
from fastapi.testclient import TestClient

import main

HUB = {"X-Auth-User-Id": "1", "X-Auth-Email": "sonali@infobeans.com", "X-Auth-Name": "Sonali%20Yadav"}
VALID = {
    "project_name": "Claims Portal", "client_industry": "Insurance",
    "overview": "o", "challenges": "c", "solution": "s", "technologies": "t", "impact": "i",
}
CASE_STUDY = {
    "executive_summary": "Summary.",
    "business_challenges": ["Slow claims"],
    "solution": {"overview": "Rebuilt it.", "key_points": ["Automation"]},
    "technology_stack": ["FastAPI"],
    "results": {"headline": "40% faster", "metrics": ["40% faster claims"]},
}


@pytest.fixture
def client():
    return TestClient(main.app)


def test_without_hub_headers_is_401(client):
    assert client.get("/case-study/").status_code == 401
    assert client.post("/case-study/api/generate", json=VALID).status_code == 401


def test_page_renders_through_hub(client):
    assert client.get("/case-study/", headers=HUB).status_code == 200


def test_generate_parses_llm_json(client, monkeypatch):
    async def fake_llm(prompt):
        assert "Claims Portal" in prompt
        return '```json\n{"executive_summary": "ok"}\n```'
    monkeypatch.setattr(main, "call_llm", fake_llm)
    resp = client.post("/case-study/api/generate", json=VALID, headers=HUB)
    assert resp.status_code == 200 and resp.json() == {"executive_summary": "ok"}


def test_generate_rejects_missing_fields(client):
    resp = client.post("/case-study/api/generate", json={"project_name": "x"}, headers=HUB)
    assert resp.status_code == 422


def test_ppt_download(client):
    resp = client.post(
        "/case-study/api/generate-ppt",
        json={"project_name": "Claims Portal", "client_industry": "Insurance", "case_study": CASE_STUDY},
        headers=HUB,
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"  # .pptx files are zip archives