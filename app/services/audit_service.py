from __future__ import annotations
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    event_type: str,
    *,
    actor_user_id: int | None = None,
    actor_email: str | None = None,
    target_user_id: int | None = None,
    target_app_id: int | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    try:
        event = AuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_user_id=target_user_id,
            target_app_id=target_app_id,
            ip_address=ip_address,
            details=json.dumps(details) if details else None,
        )
        db.add(event)
        db.flush()
    except Exception:
        logger.exception("Failed to write audit event: %s", event_type)
