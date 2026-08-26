"""
Central configuration for the CDDA Meeting Manager Dash app.

Every secret and every environment-specific value is read from an environment
variable. On Posit Connect these are set in Settings -> Vars. Locally they come
from a .env file which MUST NOT be committed (see .gitignore).

The SharePoint list GUIDs below were read out of the source Power App package
(CDDA_Meeting_Manager_V2_DEV.msapp -> References/DataSources.json), so they are
authoritative for the DEV site. They can still be overridden by env vars if the
app is pointed at another environment.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Entra ID / service principal  (SVC-DPA-DataPlatform)
# ---------------------------------------------------------------------------
TENANT_ID = os.getenv("FABRIC_TENANT_ID", "")
CLIENT_ID = os.getenv("FABRIC_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("FABRIC_CLIENT_SECRET", "")  # the secret VALUE, not the ID

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# ---------------------------------------------------------------------------
# SharePoint site that backs the app
# ---------------------------------------------------------------------------
# Site: https://collab.lilly.com/sites/CDDAMeetingMgt  (from the .msapp DataSources)
SP_HOSTNAME = os.getenv("SP_HOSTNAME", "collab.lilly.com")
SP_SITE_PATH = os.getenv("SP_SITE_PATH", "/sites/CDDAMeetingMgt")

# Optional: skip the hostname:/path lookup by supplying the composite site id
# ("collab.lilly.com,<siteGuid>,<webGuid>"). Leave blank to resolve at runtime.
SP_SITE_ID = os.getenv("SP_SITE_ID", "")

# List ids straight from the Power App package.
LIST_MEETINGS = os.getenv("LIST_MEETINGS", "2ee6fcec-2099-40fc-b3cf-7dce2c7d1c42")
LIST_INSTANCES = os.getenv("LIST_INSTANCES", "50508c5a-cd4a-4bb4-8797-cf0f16130827")
LIST_AGENDA = os.getenv("LIST_AGENDA", "a73eddc5-6de1-4662-a869-9d2b2f823b08")
LIST_DOCUMENTS = os.getenv("LIST_DOCUMENTS", "d68822c3-0d9c-436e-97c5-c0d8419a1343")

# ---------------------------------------------------------------------------
# Write access
# ---------------------------------------------------------------------------
# SVC-DPA-DataPlatform currently holds Sites.Selected READ-ONLY, so any POST /
# PATCH / DELETE against SharePoint returns 403. Leave this false until an admin
# grants write on the CDDAMeetingMgt site; the UI then runs in read-only mode
# with the mutating controls disabled instead of throwing 500s.
SP_WRITE_ENABLED = _flag("SP_WRITE_ENABLED", False)

# Optional fallback for uploads: the existing Power Automate flow
# 'CDDAMeetingManager-UploadDocuments' exposed as an HTTP-triggered flow.
UPLOAD_FLOW_URL = os.getenv("UPLOAD_FLOW_URL", "")

# ---------------------------------------------------------------------------
# App behaviour
# ---------------------------------------------------------------------------
# Users allowed to approve agenda items. In the Power App this was hard-coded to
# overstreet_kevin@lilly.com and meganfarrell@lilly.com.
APPROVER_EMAILS = [
    e.strip().lower()
    for e in os.getenv("APPROVER_EMAILS", "").split(",")
    if e.strip()
]

# Durations offered when adding an agenda item (colTimes in the Power App).
TIME_OPTIONS = [15, 30, 45, 60]

# Default meeting length used when a forum has no MeetingDuration value.
DEFAULT_MEETING_MINUTES = int(os.getenv("DEFAULT_MEETING_MINUTES", "60"))

# Seconds to cache SharePoint reads in-process. Keep small; each gunicorn worker
# holds its own cache.
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

ENVIRONMENT_LABEL = os.getenv("ENVIRONMENT_LABEL", "Development")

DEBUG_LOGGING = _flag("DEBUG_LOGGING", False)


def missing_settings() -> list:
    """Names of settings the app needs but does not have. Shown in the UI banner."""
    missing = []
    for name, value in (
        ("FABRIC_TENANT_ID", TENANT_ID),
        ("FABRIC_CLIENT_ID", CLIENT_ID),
        ("FABRIC_CLIENT_SECRET", CLIENT_SECRET),
    ):
        if not value:
            missing.append(name)
    return missing
