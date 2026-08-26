"""
AD-group access control for a Posit Connect app.

Behaviour
---------
* The signed-in user is read from the header Posit Connect sets after SSO. That
  header is set by Connect itself, so it cannot be spoofed by the browser -
  never trust a client-supplied identity instead.
* Admins listed in RLS_ADMINS always pass.
* Everyone else must be a member of REQUIRED_AD_GROUP, checked with
  `adquery group -A <group>` (works for any AD group, no credentials needed,
  because it looks the group up in AD directly rather than in the Centrify zone).
* If REQUIRED_AD_GROUP is unset, the app is open to any authenticated Connect
  user - Connect's own "login required" access setting is then the only gate.
* No Posit header present (i.e. `python app.py` on a laptop) -> no check at all,
  so local development is unaffected.

Set the app's Posit Access to "All users - login required" so the identity
header is populated.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import List, Optional, Set

from flask import Response, request

log = logging.getLogger(__name__)

# Connect sets one of these depending on version/configuration.
USER_HEADERS = (
    "RStudio-Connect-Credentials",  # JSON blob, includes user + groups
    "X-RStudio-Connect-Credentials",
    "X-RSC-Username",
    "RStudio-Connect-Username",
)

# Paths that must stay reachable regardless of the group check, otherwise the
# denial page itself cannot load and Dash's own asset requests break.
OPEN_PATH_MARKERS = ("/_dash-component-suites/", "/assets/", "/favicon.ico", "/health")

_group_members_cache: Optional[Set[str]] = None


def _raw_identity() -> Optional[str]:
    for header in USER_HEADERS:
        value = request.headers.get(header)
        if value:
            return value
    return None


def get_current_user() -> Optional[str]:
    """Login id of the signed-in user, or None when running locally."""
    raw = _raw_identity()
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            import json

            data = json.loads(raw)
            user = data.get("user") or data.get("username")
            if user:
                return str(user).strip().lower()
        except ValueError:
            log.warning("Could not parse Connect credentials header")
            return None
    return raw.lower()


def get_current_email() -> str:
    """Best-effort email for the signed-in user. Connect does not always supply
    one; falls back to <loginid>@lilly.com, which is only useful if login ids
    map that way in this tenant - verify before relying on it for approvals."""
    raw = _raw_identity()
    if raw and raw.strip().startswith("{"):
        try:
            import json

            data = json.loads(raw)
            email = data.get("email") or (data.get("user_attributes") or {}).get("email")
            if email:
                return str(email).strip().lower()
        except ValueError:
            pass
    user = get_current_user()
    return f"{user}@lilly.com" if user else ""


def get_user_display_name(user_id: str) -> str:
    """Display name via adquery. Returns the login id unchanged on failure."""
    if not user_id:
        return ""
    try:
        out = subprocess.run(
            ["adquery", "user", "-A", user_id],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return user_id
    for line in out.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() in {"displayname", "name", "gecos"} and value.strip():
            return value.strip()
    return user_id


def _group_members(group: str) -> Set[str]:
    """sAMAccountNames of an AD group, parsed from `adquery group -A <group>`.
    Members come back as DNs; the last '/' or 'CN=' segment is the account name."""
    global _group_members_cache
    if _group_members_cache is not None:
        return _group_members_cache

    members: Set[str] = set()
    try:
        out = subprocess.run(
            ["adquery", "group", "-A", group],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        log.error("adquery group lookup failed for %s: %s", group, exc)
        _group_members_cache = set()
        return _group_members_cache

    for line in out.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() != "members":
            continue
        for dn in value.split(","):
            dn = dn.strip()
            if not dn:
                continue
            tail = dn.split("/")[-1]
            if tail.upper().startswith("CN="):
                tail = tail[3:]
            members.add(tail.strip().lower())

    _group_members_cache = members
    log.info("AD group %s resolved to %d members", group, len(members))
    return members


def _admins() -> List[str]:
    return [a.strip().lower() for a in os.getenv("RLS_ADMINS", "").split(",") if a.strip()]


def is_authorized(user: str) -> bool:
    if not user:
        return True  # local development, no Connect header
    if user in _admins():
        return True
    group = os.getenv("REQUIRED_AD_GROUP", "").strip()
    if not group:
        return True  # no group configured - Connect login is the only gate
    return user in _group_members(group)


_DENIED_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Access denied</title></head>
<body style="font-family:'Aptos','Segoe UI',Arial,sans-serif;background:#E9ECF1;margin:0">
  <div style="max-width:560px;margin:14vh auto;background:#fff;border-radius:12px;
              border-left:3px solid #E4202D;padding:40px">
    <p style="margin:0 0 10px;font:700 11px/1 'Aptos',Arial,sans-serif;letter-spacing:.14em;
              text-transform:uppercase;color:#E4202D">Access denied</p>
    <h1 style="margin:0 0 12px;font:700 26px/1.2 'Aptos',Arial,sans-serif;color:#0B1D3A">
      You do not have access to CDDA Meeting Manager</h1>
    <p style="margin:0;font:400 15px/1.6 'Aptos',Arial,sans-serif;color:#3A4658">
      Signed in as <strong>{user}</strong>. Access is limited to members of
      <strong>{group}</strong>. Ask the meeting owner to request membership.</p>
  </div>
</body></html>"""


def enforce_access(server) -> None:
    """Attach the check to a Flask server (Dash: pass app.server)."""

    @server.before_request
    def _check_access():  # noqa: ANN202 - Flask hook
        path = request.path or ""
        if any(marker in path for marker in OPEN_PATH_MARKERS):
            return None
        user = get_current_user()
        if is_authorized(user):
            return None
        log.warning("Access denied for %s on %s", user, path)
        html = _DENIED_HTML.format(
            user=user or "unknown",
            group=os.getenv("REQUIRED_AD_GROUP", "the required group"),
        )
        return Response(html, status=403, mimetype="text/html")
