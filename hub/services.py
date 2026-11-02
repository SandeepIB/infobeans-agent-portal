from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import AccessRequest, App, AppGrant

PENDING = AccessRequest.Status.PENDING


class AccessRequestError(Exception):
    pass


def requestable_apps(user):
    """Active apps the user can't see yet and hasn't already asked for."""
    visible = App.objects.accessible_by(user).values("pk")
    pending = AccessRequest.objects.filter(user=user, status=PENDING).values("app_id")
    return App.objects.active().exclude(pk__in=visible).exclude(pk__in=pending)


def create_request(user, app, reason=""):
    if not requestable_apps(user).filter(pk=app.pk).exists():
        raise AccessRequestError("You already have access to this agent or a request is pending.")
    try:
        with transaction.atomic():
            return AccessRequest.objects.create(user=user, app=app, reason=reason.strip())
    except IntegrityError:  # lost a race with a duplicate submit
        raise AccessRequestError("A request for this agent is already pending.")


def approve_request(access_request, by, expires_at=None, note=""):
    """Grant access and close the request. Returns False if it wasn't pending."""
    with transaction.atomic():
        req = AccessRequest.objects.select_for_update().get(pk=access_request.pk)
        if req.status != PENDING:
            return False
        # Creates the grant, or renews an expired one
        AppGrant.objects.update_or_create(
            app=req.app, user=req.user,
            defaults={
                "granted_by": by,
                "granted_at": timezone.now(),
                "expires_at": expires_at,
                "note": f"Approved request #{req.pk}",
            },
        )
        req.status = AccessRequest.Status.APPROVED
        req.decided_by, req.decided_at, req.decision_note = by, timezone.now(), note
        req.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
        return True


def reject_request(access_request, by, note=""):
    updated = AccessRequest.objects.filter(pk=access_request.pk, status=PENDING).update(
        status=AccessRequest.Status.REJECTED,
        decided_by=by, decided_at=timezone.now(), decision_note=note,
    )
    return bool(updated)


def cancel_request(user, request_id):
    """Users can withdraw their own pending requests."""
    return bool(
        AccessRequest.objects.filter(pk=request_id, user=user, status=PENDING).update(
            status=AccessRequest.Status.CANCELLED, decided_at=timezone.now(),
        )
    )