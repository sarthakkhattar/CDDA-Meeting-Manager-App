"""
Microsoft Graph access layer for the CDDA Meeting Manager.

Backs the four SharePoint data sources the Power App used:

    CDDAMeetings      forums          Title, MeetingDescription, MeetingDuration
    MeetingInstances  meeting dates   Title, MeetingDate, DisplayText, MeetingName (lookup -> CDDAMeetings)
    AgendaItems       agenda rows     Title, TopicDescription, Speakers (person),
                                      TimeRequired, MeetingText, MeetingDateCol, Status
    Documents         doc library     Title, AgendaID (number), DocumentType (lookup)

Design notes
------------
* Reads are fetched whole and filtered in Python. Graph $filter on lookup ids and
  on unindexed columns needs the HonorNonIndexedQueries preference and fails
  intermittently; these lists are small enough that client-side filtering is the
  more reliable choice.
* Every write goes through _require_write(), which raises ReadOnlyError when
  SP_WRITE_ENABLED is false. That keeps the known Sites.Selected read-only 403
  out of the UI as a clear message rather than a 500.
* Field shapes for person/lookup columns are read defensively - Graph returns
  either an expanded object or a *LookupId depending on how the column is
  configured. Verify against live data before trusting the display names.
"""

from __future__ import annotations

import base64
import datetime as _dt
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests

import config

log = logging.getLogger(__name__)

TIMEOUT = 45


class GraphError(RuntimeError):
    """Any non-2xx response from Microsoft Graph."""


class ReadOnlyError(RuntimeError):
    """Raised when a write is attempted while the app is in read-only mode."""


# ---------------------------------------------------------------------------
# Token handling
# ---------------------------------------------------------------------------
_token_lock = threading.Lock()
_token: Dict[str, Any] = {"value": None, "expires_at": 0.0}


def graph_token() -> str:
    """Client-credentials token for Graph, cached until shortly before expiry."""
    with _token_lock:
        if _token["value"] and time.time() < _token["expires_at"]:
            return _token["value"]

        url = f"https://login.microsoftonline.com/{config.TENANT_ID}/oauth2/v2.0/token"
        resp = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
                "scope": config.GRAPH_SCOPE,
            },
            timeout=TIMEOUT,
        )
        payload = resp.json()
        if resp.status_code != 200 or "access_token" not in payload:
            # AADSTS7000215 here almost always means the secret ID was pasted
            # into FABRIC_CLIENT_SECRET instead of the secret VALUE.
            raise GraphError(f"Token request failed ({resp.status_code}): {payload}")

        _token["value"] = payload["access_token"]
        _token["expires_at"] = time.time() + int(payload.get("expires_in", 3600)) - 120
        return _token["value"]


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {graph_token()}",
        "Accept": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _request(method: str, url: str, **kwargs) -> requests.Response:
    resp = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    if resp.status_code >= 400:
        raise GraphError(f"{method} {url} -> {resp.status_code}: {resp.text[:600]}")
    return resp


# ---------------------------------------------------------------------------
# Site resolution
# ---------------------------------------------------------------------------
_site_id_cache: Dict[str, str] = {}


def site_id() -> str:
    if config.SP_SITE_ID:
        return config.SP_SITE_ID
    if "id" in _site_id_cache:
        return _site_id_cache["id"]

    url = f"{config.GRAPH_ROOT}/sites/{config.SP_HOSTNAME}:{config.SP_SITE_PATH}"
    data = _request("GET", url, headers=_headers()).json()
    _site_id_cache["id"] = data["id"]
    log.info("Resolved site id %s", data["id"])
    return data["id"]


# ---------------------------------------------------------------------------
# Small TTL cache so a page render does not re-pull every list
# ---------------------------------------------------------------------------
_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()


def _cached(key: str, producer):
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now < hit["expires_at"]:
            return hit["value"]
    value = producer()
    with _cache_lock:
        _cache[key] = {"value": value, "expires_at": now + config.CACHE_TTL_SECONDS}
    return value


def invalidate_cache() -> None:
    """Call after any write so the next read reflects it."""
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# Generic list access
# ---------------------------------------------------------------------------
def list_items(list_id: str, top: int = 200) -> List[Dict[str, Any]]:
    """All items of a list, following @odata.nextLink. Returns the fields dicts
    with the item id merged in as '_id'."""
    url = (
        f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/{list_id}/items"
        f"?expand=fields&$top={top}"
    )
    out: List[Dict[str, Any]] = []
    while url:
        data = _request("GET", url, headers=_headers()).json()
        for item in data.get("value", []):
            fields = dict(item.get("fields") or {})
            fields["_id"] = item.get("id")
            out.append(fields)
        url = data.get("@odata.nextLink")
    return out


def create_item(list_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    _require_write()
    url = f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/{list_id}/items"
    resp = _request(
        "POST",
        url,
        headers=_headers({"Content-Type": "application/json"}),
        json={"fields": fields},
    )
    invalidate_cache()
    return resp.json()


def update_item(list_id: str, item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    _require_write()
    url = f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/{list_id}/items/{item_id}/fields"
    resp = _request(
        "PATCH",
        url,
        headers=_headers({"Content-Type": "application/json"}),
        json=fields,
    )
    invalidate_cache()
    return resp.json()


def delete_item(list_id: str, item_id: str) -> None:
    _require_write()
    url = f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/{list_id}/items/{item_id}"
    _request("DELETE", url, headers=_headers())
    invalidate_cache()


def _require_write() -> None:
    if not config.SP_WRITE_ENABLED:
        raise ReadOnlyError(
            "The app is running read-only. The service principal holds "
            "Sites.Selected read access on this site, so creates, edits and "
            "deletes are blocked. Ask the SharePoint owner to grant write, then "
            "set SP_WRITE_ENABLED=true in Posit Vars."
        )


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------
def field(fields: Dict[str, Any], *names: str, default: Any = "") -> Any:
    """First non-empty value among several candidate internal field names.
    SharePoint internal names do not change when a column is renamed in the UI,
    so read defensively."""
    for name in names:
        value = fields.get(name)
        if value not in (None, "", "nan"):
            return value
    return default


def person_name(fields: Dict[str, Any], base: str) -> str:
    """Display name from a person column, whichever shape Graph returns."""
    value = fields.get(base)
    if isinstance(value, dict):
        return value.get("DisplayName") or value.get("displayName") or value.get("Title") or ""
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first.get("DisplayName") or first.get("Title") or ""
        return str(first)
    if isinstance(value, str):
        return value
    return ""


def lookup_id(fields: Dict[str, Any], base: str) -> Optional[int]:
    """Id from a lookup column, whichever shape Graph returns."""
    for key in (f"{base}LookupId", f"{base}Id", f"{base}_x003a_Id"):
        raw = fields.get(key)
        if raw not in (None, ""):
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    value = fields.get(base)
    if isinstance(value, dict):
        raw = value.get("LookupId") or value.get("Id")
        if raw not in (None, ""):
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
    return None


def as_date(value: Any) -> Optional[_dt.date]:
    """Normalise a SharePoint date (ISO string or date) to a date object.
    The Power App joined AgendaItems to MeetingInstances on the *date value*
    (MeetingDateCol = 'Meeting Date'), so both sides must normalise identically."""
    if value in (None, ""):
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return _dt.datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d%b%Y"):
        try:
            return _dt.datetime.strptime(str(value)[:10], fmt).date()
        except ValueError:
            continue
    log.warning("Unparsed date value: %r", value)
    return None


def format_date(value: Any) -> str:
    date = as_date(value)
    return date.strftime("%d %b %Y") if date else ""


# ---------------------------------------------------------------------------
# Domain reads
# ---------------------------------------------------------------------------
def get_forums() -> List[Dict[str, Any]]:
    """CDDAMeetings - the forums shown on the home screen."""

    def load():
        forums = []
        for row in list_items(config.LIST_MEETINGS):
            forums.append(
                {
                    "id": str(row.get("_id") or row.get("id") or ""),
                    "title": field(row, "Title"),
                    "description": field(row, "MeetingDescription", "Meeting_x0020_Description"),
                    "duration": int(field(row, "MeetingDuration", default=0) or 0)
                    or config.DEFAULT_MEETING_MINUTES,
                    "owner": person_name(row, "MeetingOwner"),
                    "admin": person_name(row, "MeetingAdmin"),
                }
            )
        forums.sort(key=lambda f: f["title"].lower())
        return forums

    return _cached("forums", load)


def get_instances(forum_id: str) -> List[Dict[str, Any]]:
    """MeetingInstances for one forum, mirroring
    Filter(MeetingInstances, MeetingName.Id = varMeeting.ID)."""

    def load():
        rows = list_items(config.LIST_INSTANCES)
        out = []
        for row in rows:
            parent = lookup_id(row, "MeetingName") or lookup_id(row, "Meeting")
            if parent is None or str(parent) != str(forum_id):
                continue
            date = as_date(field(row, "MeetingDate", "Meeting_x0020_Date"))
            out.append(
                {
                    "id": str(row.get("_id") or ""),
                    "title": field(row, "Title"),
                    "date": date,
                    "date_label": date.strftime("%d %b %Y") if date else "(no date)",
                    "display_text": field(row, "DisplayText"),
                    "is_available": bool(field(row, "IsAvailable", default=True)),
                }
            )
        out.sort(key=lambda i: (i["date"] is None, i["date"] or _dt.date.min))
        return out

    return _cached(f"instances:{forum_id}", load)


def get_agenda_items(meeting_date: Optional[_dt.date]) -> List[Dict[str, Any]]:
    """AgendaItems joined on the date, mirroring
    Filter(AgendaItems, MeetingDateCol = varMeetingDate.'Meeting Date')."""
    if meeting_date is None:
        return []

    def load():
        out = []
        for row in list_items(config.LIST_AGENDA):
            if as_date(field(row, "MeetingDateCol")) != meeting_date:
                continue
            out.append(
                {
                    "id": str(row.get("_id") or ""),
                    "title": field(row, "Title"),
                    "description": field(row, "TopicDescription"),
                    "speaker": person_name(row, "Speakers"),
                    "minutes": int(field(row, "TimeRequired", default=0) or 0),
                    "status": field(row, "Status", default="Pending"),
                    "meeting_text": field(row, "MeetingText"),
                }
            )
        out.sort(key=lambda a: int(a["id"] or 0))
        return out

    return _cached(f"agenda:{meeting_date.isoformat()}", load)


def get_documents(agenda_item_id: str) -> List[Dict[str, Any]]:
    """Documents library rows for one agenda item (Filter(Documents, AgendaID = ThisItem.ID))."""

    def load():
        out = []
        for row in list_items(config.LIST_DOCUMENTS):
            raw = field(row, "AgendaID", default=None)
            if raw in (None, ""):
                continue
            try:
                if int(float(raw)) != int(agenda_item_id):
                    continue
            except (TypeError, ValueError):
                continue
            out.append(
                {
                    "id": str(row.get("_id") or ""),
                    "title": field(row, "Title", "FileLeafRef", "LinkFilename"),
                    "doc_type": person_name(row, "DocumentType") or field(row, "DocumentType"),
                }
            )
        return out

    return _cached(f"docs:{agenda_item_id}", load)


def minutes_used(meeting_date: Optional[_dt.date]) -> int:
    return sum(item["minutes"] for item in get_agenda_items(meeting_date))


# ---------------------------------------------------------------------------
# Domain writes
# ---------------------------------------------------------------------------
def add_agenda_item(
    *,
    title: str,
    description: str,
    minutes: int,
    meeting_date: _dt.date,
    meeting_text: str,
    speaker_lookup_id: Optional[int] = None,
    status: str = "Pending",
) -> Dict[str, Any]:
    fields: Dict[str, Any] = {
        "Title": title,
        "TopicDescription": description,
        "TimeRequired": minutes,
        "MeetingDateCol": meeting_date.isoformat(),
        "MeetingText": meeting_text,
        "Status": status,
    }
    if speaker_lookup_id is not None:
        # Person columns are written by site-user id, not by email.
        fields["SpeakersLookupId"] = speaker_lookup_id
    return create_item(config.LIST_AGENDA, fields)


def update_agenda_item(item_id: str, **fields: Any) -> Dict[str, Any]:
    return update_item(config.LIST_AGENDA, item_id, fields)


def approve_agenda_item(item_id: str) -> Dict[str, Any]:
    """Patch(AgendaItems, ..., {Status:"Approved"})."""
    return update_item(config.LIST_AGENDA, item_id, {"Status": "Approved"})


def delete_agenda_item(item_id: str) -> None:
    """Deletes the item's documents first, then the item - same order as the
    Power App's delete button."""
    for doc in get_documents(item_id):
        try:
            delete_item(config.LIST_DOCUMENTS, doc["id"])
        except GraphError as exc:
            log.warning("Could not delete document %s: %s", doc["id"], exc)
    delete_item(config.LIST_AGENDA, item_id)


def resolve_site_user_id(email: str) -> Optional[int]:
    """Site-user id for a person column write. Queries the hidden User
    Information List; returns None if it cannot be resolved, in which case the
    caller should save the item without a speaker rather than fail.

    Verify this against the live site - if the site's user list is not indexed
    on EMail this query can be refused, and an admin-configured alternative is
    needed."""
    if not email:
        return None
    url = (
        f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/User Information List/items"
        f"?expand=fields&$filter=fields/EMail eq '{email}'&$top=1"
    )
    try:
        data = _request(
            "GET",
            url,
            headers=_headers({"Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"}),
        ).json()
    except GraphError as exc:
        log.warning("Site user lookup failed for %s: %s", email, exc)
        return None
    values = data.get("value") or []
    if not values:
        return None
    try:
        return int(values[0].get("id"))
    except (TypeError, ValueError):
        return None


def upload_document(
    *,
    agenda_item_id: str,
    filename: str,
    content: bytes,
    doc_type: str = "",
) -> Dict[str, Any]:
    """Upload a file to the Documents library and stamp it with AgendaID.

    Two routes:
      1. Direct Graph upload (needs write on the site).
      2. The existing Power Automate flow, if UPLOAD_FLOW_URL is set - this is
         the same flow the Power App called ('CDDAMeetingManager-UploadDocuments')
         and it runs under the flow owner's connection, so it works even while
         the service principal is read-only.
    """
    stamped_name = f"{_dt.datetime.now():%Y%m%d_%H%M%S}_{filename}"

    if config.UPLOAD_FLOW_URL:
        resp = _request(
            "POST",
            config.UPLOAD_FLOW_URL,
            headers={"Content-Type": "application/json"},
            json={
                "name": stamped_name,
                "contentBytes": base64.b64encode(content).decode("ascii"),
                "agendaId": agenda_item_id,
                "documentName": filename,
                "documentType": doc_type,
            },
        )
        invalidate_cache()
        return {"route": "flow", "status": resp.status_code, "name": stamped_name}

    _require_write()
    drive_url = (
        f"{config.GRAPH_ROOT}/sites/{site_id()}/lists/{config.LIST_DOCUMENTS}/drive"
        f"/root:/{stamped_name}:/content"
    )
    created = _request(
        "PUT",
        drive_url,
        headers=_headers({"Content-Type": "application/octet-stream"}),
        data=content,
    ).json()

    # Stamp AgendaID (and DocumentType when the column is plain text) on the
    # matching list item so the app can find the file again.
    item_id = (created.get("listItem") or {}).get("id")
    if not item_id:
        lookup = _request(
            "GET",
            f"{config.GRAPH_ROOT}/sites/{site_id()}/drive/root:/{stamped_name}:/listItem",
            headers=_headers(),
        ).json()
        item_id = lookup.get("id")
    if item_id:
        patch: Dict[str, Any] = {"AgendaID": int(agenda_item_id), "Title": filename}
        try:
            update_item(config.LIST_DOCUMENTS, item_id, patch)
        except GraphError as exc:
            log.warning("Uploaded %s but could not stamp AgendaID: %s", stamped_name, exc)

    invalidate_cache()
    return {"route": "graph", "name": stamped_name, "item_id": item_id}


def health() -> Dict[str, Any]:
    """Cheap connectivity probe used by the startup banner."""
    try:
        forums = get_forums()
        return {"ok": True, "forums": len(forums), "site": site_id()}
    except Exception as exc:  # surfaced in the UI, full traceback in the Logs tab
        log.exception("SharePoint health check failed")
        return {"ok": False, "error": str(exc)}
