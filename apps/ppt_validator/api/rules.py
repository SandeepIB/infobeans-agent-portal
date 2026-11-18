"""Rules API — manage rule library entries."""
from fastapi import APIRouter
from pydantic import BaseModel
from services.rule_service import RuleService

router = APIRouter(prefix="/api/v2/rules", tags=["rules"])
_svc = RuleService()


class RuleUpsert(BaseModel):
    rule_id: str
    rule_json: dict
    created_by: str = "admin"


@router.get("/{domain}")
def get_rules(domain: str):
    return _svc.get_rules(domain)


@router.put("/{domain}")
def upsert_rule(domain: str, body: RuleUpsert):
    _svc.upsert_rule(domain, body.rule_id, body.rule_json, body.created_by)
    return {"upserted": True, "domain": domain, "rule_id": body.rule_id}
