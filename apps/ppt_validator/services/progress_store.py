"""In-memory progress tracker for review runs. Thread-safe. No persistence needed."""
from __future__ import annotations
import threading

_lock = threading.Lock()
_store: dict[str, dict] = {}

AGENT_LABELS = {
    "branding":         "Branding check",
    "template":         "Template check",
    "content":          "Content Quality",
    "story":            "Story Arc",
    "customer_focus":   "Customer Focus",
    "proposal_context": "Proposal Context",
    "cio_lens":         "CIO Lens",
    "critic":           "Critic review",
}


def init(run_id: str, agent_ids: list[str]) -> None:
    steps = [{"id": "extraction", "label": "Extracting slides", "status": "pending"}]
    for aid in agent_ids:
        steps.append({"id": aid, "label": AGENT_LABELS.get(aid, aid), "status": "pending"})
    steps.append({"id": "_aggregate", "label": "Aggregating results", "status": "pending"})
    with _lock:
        _store[run_id] = {
            "status": "queued",
            "current_label": "Queued…",
            "steps": steps,
            "error": None,
            "result": None,
        }


def start_step(run_id: str, step_id: str) -> None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return
        d["status"] = "running"
        for s in d["steps"]:
            if s["id"] == step_id:
                s["status"] = "running"
                d["current_label"] = s["label"] + "…"
                break


def done_step(run_id: str, step_id: str) -> None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return
        for s in d["steps"]:
            if s["id"] == step_id:
                s["status"] = "done"
                break


def fail_step(run_id: str, step_id: str) -> None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return
        for s in d["steps"]:
            if s["id"] == step_id:
                s["status"] = "failed"
                break


def complete(run_id: str, result: dict) -> None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return
        for s in d["steps"]:
            if s["status"] not in ("done", "failed"):
                s["status"] = "done"
        d["status"] = "completed"
        d["current_label"] = "Complete!"
        d["result"] = result


def fail(run_id: str, error: str) -> None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return
        d["status"] = "failed"
        d["error"] = error
        d["current_label"] = "Failed"


def get_summary(run_id: str) -> dict | None:
    with _lock:
        d = _store.get(run_id)
        if not d:
            return None
        steps = d["steps"]
        done_n = sum(1 for s in steps if s["status"] in ("done", "failed"))
        return {
            "status": d["status"],
            "current_label": d["current_label"],
            "total_steps": len(steps),
            "completed_steps": done_n,
            "steps": [dict(s) for s in steps],
            "error": d["error"],
            "result": d["result"],
        }
