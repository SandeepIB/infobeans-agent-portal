from __future__ import annotations
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.user import User
from app.security.dependencies import require_user
from app.services import permission_service
from app.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ppt-validator"])

PPT_SLUG = "ppt-validator"
_PREFIX = "/ppt-validator"

_SKIP_HEADERS = frozenset(
    h.lower() for h in (
        "host", "connection", "transfer-encoding", "te",
        "trailers", "upgrade", "keep-alive",
    )
)


def _build_upstream_headers(request: Request, user: User) -> dict[str, str]:
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _SKIP_HEADERS
    }
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    headers["X-Hub-User"] = user.email
    return headers


@router.api_route(
    _PREFIX + "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def ppt_validator_proxy(
    request: Request,
    path: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    if not permission_service.has_app_permission(db, user, PPT_SLUG):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access the PowerPoint Validator",
        )

    target_url = f"{settings.ppt_validator_internal_url}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = _build_upstream_headers(request, user)
    body = await request.body()

    timeout = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="PowerPoint Validator service is unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="PowerPoint Validator service timed out")

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _SKIP_HEADERS | {"content-encoding", "content-length"}
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


@router.get(_PREFIX, include_in_schema=False)
async def ppt_validator_root(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    if not permission_service.has_app_permission(db, user, PPT_SLUG):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access the PowerPoint Validator",
        )
    target_url = f"{settings.ppt_validator_internal_url}/"
    headers = _build_upstream_headers(request, user)
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.get(target_url, headers=headers)
    except (httpx.ConnectError, httpx.TimeoutException):
        raise HTTPException(status_code=502, detail="PowerPoint Validator service is unavailable")
    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _SKIP_HEADERS | {"content-encoding", "content-length"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
