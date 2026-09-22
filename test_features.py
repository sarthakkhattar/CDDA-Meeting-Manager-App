"""
CDDA Meeting Manager — Test Script (standalone, no venv required)
Run: python test_features.py

Tests all new features in demo mode.
Patches imports to avoid needing dotenv/dash installed.
"""

import os
import sys
import types

# ── Patch: create a stub 'dotenv' so config.py can import it ─────────
stub_dotenv = types.ModuleType("dotenv")
stub_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = stub_dotenv

# ── Set env vars BEFORE importing config ─────────────────────────────
os.environ["DEMO_MODE"] = "1"
os.environ["DEV_USER_EMAIL"] = "test.admin@lilly.com"
os.environ["RLS_ADMINS"] = "test.admin@lilly.com, another.admin@lilly.com"
os.environ["APPROVER_EMAILS"] = "test.approver@lilly.com, test.admin@lilly.com"
os.environ["FABRIC_WORKSPACE_ID"] = "fake"
os.environ["FABRIC_LAKEHOUSE_ID"] = "fake"
os.environ["FABRIC_CLIENT_ID"] = "fake"
os.environ["FABRIC_CLIENT_SECRET"] = "fake"
os.environ["FABRIC_TENANT_ID"] = "fake"
os.environ["APP_ENVIRONMENT"] = "Development"

# Now safe to import
import config
from fabric_graph import get_data_layer, generate_recurring_dates, _safe_id

PASS = 0
FAIL = 0

# Force UTF-8 output on Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def check(desc, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {desc}")
    else:
        FAIL += 1
        print(f"  [FAIL] {desc}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ================================================================
# 1. CONFIG
# ================================================================
section("1. Config — env vars loaded correctly")

check("DEMO_MODE is True", config.DEMO_MODE is True)
check("DEV_USER_EMAIL loaded", config.DEV_USER_EMAIL == "test.admin@lilly.com")
check("RLS_ADMINS is a list", isinstance(config.RLS_ADMINS, list))
check("RLS_ADMINS has 2 entries", len(config.RLS_ADMINS) == 2)
check("RLS_ADMINS normalized (lowercase, stripped)",
      "test.admin@lilly.com" in config.RLS_ADMINS
      and "another.admin@lilly.com" in config.RLS_ADMINS)
check("APPROVER_EMAILS normalized",
      "test.approver@lilly.com" in config.APPROVER_EMAILS)


# ================================================================
# 2. INPUT SANITIZATION
# ================================================================
section("2. Input sanitization — _safe_id()")

check("Normal ID: mtg_123", _safe_id("mtg_123") == "mtg_123")
check("ID with dots: v1.2.3", _safe_id("v1.2.3") == "v1.2.3")
check("ID with dashes: item-abc", _safe_id("item-abc") == "item-abc")
check("Long ID: inst_1726000000_0", _safe_id("inst_1726000000_0") == "inst_1726000000_0")

for bad_input, label in [
    ("'; DROP TABLE --", "SQL injection"),
    ("test' OR '1'='1", "quote injection"),
    ("", "empty string"),
    ("hello world", "spaces"),
    ("test;delete", "semicolon"),
]:
    try:
        _safe_id(bad_input)
        check(f"Blocks {label}: {bad_input!r}", False)
    except ValueError:
        check(f"Blocks {label}: {bad_input!r}", True)


# ================================================================
# 3. DATA LAYER BASICS
# ================================================================
section("3. Data layer — demo mode CRUD")

dl = get_data_layer()

meetings = dl.get_meetings()
check("2 forums returned", len(meetings) == 2)
check("Forum 1: CDDA OOH", meetings[0]["title"] == "CDDA Open Office Hours")
check("Forum 2: CDSR", "CDSR" in meetings[1]["title"])

ooh_instances = dl.get_meeting_instances("mtg_1")
check("OOH has 4 date instances", len(ooh_instances) == 4)

cdsr_instances = dl.get_meeting_instances("mtg_2")
check("CDSR has 3 date instances", len(cdsr_instances) == 3)


# ================================================================
# 4. ARCHIVE FILTERING
# ================================================================
section("4. Agenda items — archive filtering")

# inst_1 has 2 active + 1 archived in demo data
all_items = dl.get_agenda_items("mtg_1", instance_id="inst_1", include_archived=True)
check("inst_1 total items (incl. archived) = 3", len(all_items) == 3)

active_items = dl.get_agenda_items("mtg_1", instance_id="inst_1")
check("inst_1 active items (default) = 2", len(active_items) == 2)
check("Default excludes Archived status",
      all(i.get("status") != "Archived" for i in active_items))

archived = dl.get_archived_items("mtg_1", instance_id="inst_1")
check("inst_1 archived items = 1", len(archived) == 1)
check("Archived item is correct",
      archived[0]["title"] == "Legacy Process Review (Archived)" if archived else False)
check("Archived status = 'Archived'",
      archived[0].get("status") == "Archived" if archived else False)

# Other instances unaffected
inst3_items = dl.get_agenda_items("mtg_1", instance_id="inst_3")
check("inst_3 has 1 active item", len(inst3_items) == 1)

inst5_items = dl.get_agenda_items("mtg_2", instance_id="inst_5")
check("inst_5 (CDSR) has 2 active items", len(inst5_items) == 2)


# ================================================================
# 5. ARCHIVE + RESTORE
# ================================================================
section("5. Archive / Restore (demo mode returns True)")

check("archive_agenda_item succeeds", dl.archive_agenda_item("itm_1") is True)
check("restore_agenda_item succeeds", dl.restore_agenda_item("itm_archived_1") is True)


# ================================================================
# 6. RECURRING DATE GENERATION
# ================================================================
section("6. Recurring date generation")

# Mondays in Jan 2026 (Jan 5, 12, 19, 26)
mondays = generate_recurring_dates(0, "2026-01-05", "2026-01-26")
check("4 Mondays in Jan 5–26", len(mondays) == 4)
check("First = 2026-01-05", mondays[0]["date"] == "2026-01-05")
check("Last  = 2026-01-26", mondays[-1]["date"] == "2026-01-26")
check("display_text = '05 Jan 2026'", mondays[0]["display_text"] == "05 Jan 2026")

# Start on a non-target day → skips to first occurrence
tues = generate_recurring_dates(1, "2026-01-05", "2026-01-14")  # Mon start, looking for Tue
check("Finds Tue from Mon start (Jan 6, 13)", len(tues) == 2)
check("First Tue = 2026-01-06", tues[0]["date"] == "2026-01-06" if tues else False)

# Start IS the target day
wed = generate_recurring_dates(2, "2026-01-07", "2026-01-07")  # Jan 7 is a Wed
check("Single Wed on exact day", len(wed) == 1)

# Edge: start > end
check("start > end → empty", len(generate_recurring_dates(0, "2026-12-31", "2026-01-01")) == 0)

# Edge: no matching day in narrow range
check("No Sun in Mon–Fri → empty", len(generate_recurring_dates(6, "2026-01-05", "2026-01-09")) == 0)

# Fridays in March 2026
fridays = generate_recurring_dates(4, "2026-03-01", "2026-03-31")
check(f"Fridays in March 2026 = {len(fridays)}", len(fridays) >= 4)
check("First Friday = 2026-03-06", fridays[0]["date"] == "2026-03-06")


# ================================================================
# 7. DATE MANAGEMENT CRUD
# ================================================================
section("7. Date management CRUD (demo mode)")

new_id = dl.create_meeting_instance("mtg_1", "2026-06-15", "15 Jun 2026")
check("create_meeting_instance returns ID", new_id is not None and new_id.startswith("inst_"))

bulk = dl.create_meeting_instances_bulk("mtg_1", [
    {"date": "2026-07-06", "display_text": "06 Jul 2026"},
    {"date": "2026-07-13", "display_text": "13 Jul 2026"},
    {"date": "2026-07-20", "display_text": "20 Jul 2026"},
])
check("Bulk create returns 3 IDs", len(bulk) == 3)
check("Bulk IDs are unique", len(set(bulk)) == 3)
check("Bulk IDs prefixed with inst_", all(i.startswith("inst_") for i in bulk))

check("Delete instance succeeds", dl.delete_meeting_instance("inst_1") is True)
check("Delete with cascade succeeds", dl.delete_meeting_instance("inst_2", cascade=True) is True)


# ================================================================
# 8. USER ROLE HELPERS
# ================================================================
section("8. User role helpers (_is_admin, _is_approver)")

# Inline check (avoid importing dash/flask)
def is_admin(email):
    return bool(email and email != "anonymous" and email in config.RLS_ADMINS)

def is_approver(email):
    return bool(email and email != "anonymous" and email in config.APPROVER_EMAILS)

check("Admin: test.admin@lilly.com", is_admin("test.admin@lilly.com"))
check("Admin: another.admin@lilly.com", is_admin("another.admin@lilly.com"))
check("Not admin: random@lilly.com", not is_admin("random@lilly.com"))
check("Not admin: anonymous", not is_admin("anonymous"))
check("Not admin: empty", not is_admin(""))

check("Approver: test.approver@lilly.com", is_approver("test.approver@lilly.com"))
check("Approver: test.admin (also approver)", is_approver("test.admin@lilly.com"))
check("Not approver: random@lilly.com", not is_approver("random@lilly.com"))
check("Not approver: anonymous", not is_approver("anonymous"))


# ================================================================
# SUMMARY
# ================================================================
total = PASS + FAIL
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {total} total")
print(f"{'='*60}")

if FAIL > 0:
    print("\n  ⚠  Some tests failed! Review output above.\n")
    sys.exit(1)
else:
    print("\n  ✅ All tests passed!\n")
    sys.exit(0)
