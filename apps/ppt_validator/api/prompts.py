"""Prompts API — manage prompt versions and activations."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.prompt_service import PromptService

router = APIRouter(prefix="/api/v2/prompts", tags=["prompts"])
_svc = PromptService()


class PromptVersionCreate(BaseModel):
    agent_id: str
    version_tag: str
    system: str
    user_template: str
    created_by: str = "admin"


class PromptActivate(BaseModel):
    activated_by: str = "admin"


@router.get("/{agent_id}")
def list_versions(agent_id: str):
    return _svc.list_versions(agent_id)


@router.get("/{agent_id}/active")
def get_active(agent_id: str):
    return _svc.get_active(agent_id)


@router.post("")
def create_version(body: PromptVersionCreate):
    version_id = _svc.create_version(
        body.agent_id, body.system, body.user_template, body.version_tag, body.created_by
    )
    return {"version_id": version_id}


@router.post("/{agent_id}/activate/{version_id}")
def activate(agent_id: str, version_id: int, body: PromptActivate):
    _svc.activate(agent_id, version_id, body.activated_by)
    return {"activated": True, "agent_id": agent_id, "version_id": version_id}
