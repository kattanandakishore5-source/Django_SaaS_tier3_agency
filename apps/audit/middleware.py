import json
import re
from django.utils.deprecation import MiddlewareMixin
from django.db import transaction
from django.conf import settings

REDACT_KEYS = ('password', 'token', 'secret', 'signature', 'csrf')


def _redact_value(v):
    return "[REDACTED]"


def _redact_dict(d):
    # Recursively redact keys that match sensitive tokens
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        try:
            key_lower = k.lower()
        except Exception:
            key_lower = str(k)
        if any(term in key_lower for term in REDACT_KEYS):
            out[k] = _redact_value(v)
        else:
            if isinstance(v, dict):
                out[k] = _redact_dict(v)
            elif isinstance(v, list):
                out[k] = [_redact_dict(x) if isinstance(x, dict) else x for x in v]
            else:
                out[k] = v
    return out


class AuditLoggingMiddleware(MiddlewareMixin):
    """Middleware to capture audit events and redact sensitive fields."""

    def process_response(self, request, response):
        try:
            # Avoid interfering with normal responses
            path = getattr(request, 'path', None)
            method = getattr(request, 'method', None)
            user = None
            try:
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user = request.user
            except Exception:
                user = None

            # Determine IP address (prefer X-Forwarded-For if present)
            ip = None
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            if xff:
                ip = xff.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

            # Gather payload safely
            payload = None
            if method in ('POST', 'PUT', 'PATCH'):
                # Prefer request.POST for form data
                try:
                    if hasattr(request, 'POST') and request.POST:
                        payload = dict(request.POST)
                    else:
                        body = request.body
                        if body:
                            try:
                                payload = json.loads(body.decode('utf-8'))
                            except Exception:
                                payload = {'raw_body': body.decode('utf-8', errors='ignore')}
                except Exception:
                    payload = None

            # Redact sensitive keys
            if isinstance(payload, dict):
                try:
                    payload = _redact_dict(payload)
                except Exception:
                    # Fall back to minimal redaction
                    for k in list(payload.keys()):
                        if any(term in k.lower() for term in REDACT_KEYS):
                            payload[k] = "[REDACTED]"

            # Prepare audit record creation (defer to on_commit in production)
            workspace = getattr(request, 'workspace', None)

            def _create_audit():
                try:
                    from apps.audit.models import AuditLog
                    AuditLog.objects.create(
                        user=user if user is not None else None,
                        workspace=workspace,
                        action=f"{method} {response.status_code}",
                        ip_address=ip,
                        path=path or '',
                        payload=payload,
                    )
                except Exception:
                    # Do not raise from middleware
                    pass

            if getattr(settings, 'TESTING', False):
                # Create immediately in testing to allow assertions
                _create_audit()
            else:
                try:
                    transaction.on_commit(_create_audit)
                except Exception:
                    # Fallback to immediate creation if transaction manager not available
                    _create_audit()
        except Exception:
            # Never fail a response due to audit logging
            pass
        return response
