"""Review API — upload PPTX and run review."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

import agents  # noqa: F401 — registers all agents
from services.review_service import ReviewService
from db.session import db

from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/v2/review", tags=["review"])
_svc = ReviewService()

DEFAULT_PROFILE = {
    "review_profile": "customer_presentation",
    "agents": [],
}


@router.post("")
async def start_review(
    file: UploadFile = File(...),
    profile: str = Form(default="{}"),
    proposal_context: str = Form(default=""),
):
    profile_data = {**DEFAULT_PROFILE, **json.loads(profile)}
    suffix = Path(file.filename).suffix or ".pptx"
    file_bytes = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        result = await run_in_threadpool(
            _svc.run,
            tmp_path,
            profile_data,
            proposal_context or None,
            file.filename,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return JSONResponse(content=result)


@router.get("/{run_id}")
def get_run(run_id: str):
    with db() as conn:
        row = conn.execute(
            "SELECT id, status, score, result_json, started_at, completed_at FROM review_runs WHERE id=?",
            (run_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    result = json.loads(row["result_json"]) if row["result_json"] else {}
    def _str(v):
        return v.isoformat() if hasattr(v, 'isoformat') else v
    raw_status = row["status"]
    status = "completed" if raw_status in ("blocked", "review", "ready", "completed") else raw_status
    quality_gate = result.get("quality_gate") or (raw_status if raw_status in ("blocked", "review", "ready") else None)
    return {"run_id": row["id"], "status": status, "quality_gate": quality_gate, "score": row["score"],
            "started_at": _str(row["started_at"]), "completed_at": _str(row["completed_at"]), **result}


@router.get("/{run_id}/report.pdf")
def get_run_pdf(run_id: str):
    from services.report_service import generate_pdf
    with db() as conn:
        row = conn.execute(
            "SELECT id, status, score, result_json, started_at, completed_at FROM review_runs WHERE id=?",
            (run_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    result = json.loads(row["result_json"]) if row["result_json"] else {}
    def _str(v):
        return v.isoformat() if hasattr(v, 'isoformat') else v
    raw_status = row["status"]
    status = "completed" if raw_status in ("blocked", "review", "ready", "completed") else raw_status
    run_data = {
        "run_id": row["id"],
        "status": status,
        "score": row["score"],
        "started_at": _str(row["started_at"]),
        "completed_at": _str(row["completed_at"]),
        **result,
    }
    pdf_bytes = generate_pdf(run_data)
    safe_id = run_id.replace("/", "_")[:40]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="review-{safe_id}.pdf"'},
    )


@router.get("")
def list_runs(limit: int = 20, offset: int = 0):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, filename, status, score, result_json, started_at, completed_at FROM review_runs ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    def _str(v):
        return v.isoformat() if hasattr(v, 'isoformat') else v
    res = []
    for r in rows:
        raw_status = r["status"]
        status = "completed" if raw_status in ("blocked", "review", "ready", "completed") else raw_status
        q_gate = None
        if r["result_json"]:
            try:
                parsed = json.loads(r["result_json"])
                q_gate = parsed.get("quality_gate")
            except Exception:
                pass
        if not q_gate and raw_status in ("blocked", "review", "ready"):
            q_gate = raw_status

        res.append({
            "run_id": r["id"],
            "filename": r["filename"],
            "status": status,
            "quality_gate": q_gate,
            "score": r["score"],
            "started_at": _str(r["started_at"]),
            "completed_at": _str(r["completed_at"]),
        })
    return res
