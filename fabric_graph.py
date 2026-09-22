"""
Fabric Lakehouse data layer for CDDA Meeting Manager.
Uses the deltalake library for Delta Lake table operations on OneLake.
"""

from typing import List, Dict, Optional
from datetime import datetime

import re
import config

# ============================================================================
# Input sanitization
# ============================================================================


def _safe_id(val: str) -> str:
    """Validate that a value is safe to interpolate into a Delta Lake predicate.

    Rejects any value containing characters that could alter predicate logic
    (single quotes, semicolons, dashes used for SQL comments, etc.).
    Only alphanumerics, underscores, hyphens, and dots are allowed.
    """
    if not isinstance(val, str) or not re.match(r'^[A-Za-z0-9_.\-]+$', val):
        raise ValueError(f"Invalid identifier: contains disallowed characters")
    return val


# ============================================================================
# OneLake path helpers
# ============================================================================

ONELAKE_BASE = (
    f"abfss://{config.FABRIC_WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com"
    f"/{config.FABRIC_LAKEHOUSE_ID}/Tables/dbo"
)


def _table_path(name: str) -> str:
    """Return the OneLake abfss:// path for a Delta table."""
    return f"{ONELAKE_BASE}/{name}"


def _storage_opts() -> dict:
    """Storage options for OneLake via Service Principal."""
    return {
        "use_fabric_endpoint": "true",
        "tenant_id": config.FABRIC_TENANT_ID,
        "client_id": config.FABRIC_CLIENT_ID,
        "client_secret": config.FABRIC_CLIENT_SECRET,
    }


# ============================================================================
# Date helpers
# ============================================================================

def generate_recurring_dates(day_of_week: int, start_date_str: str,
                             end_date_str: str) -> List[Dict]:
    """Generate recurring weekly dates.

    day_of_week: 0=Monday ... 6=Sunday
    start_date_str, end_date_str: 'YYYY-MM-DD'
    Returns: [{"date": "YYYY-MM-DD", "display_text": "DD Mon YYYY"}, ...]
    """
    from datetime import timedelta

    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    # Find first occurrence of day_of_week on or after start
    days_ahead = day_of_week - start.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start + timedelta(days=days_ahead)

    dates: List[Dict] = []
    while current <= end:
        dates.append({
            "date": current.strftime("%Y-%m-%d"),
            "display_text": current.strftime("%d %b %Y"),
        })
        current += timedelta(days=7)
    return dates


# ============================================================================
# Data layer
# ============================================================================

class FabricDataLayer:
    """CRUD interface to Fabric Lakehouse Delta tables."""

    def __init__(self):
        self._opts = _storage_opts()
        self._ok = False
        if not config.DEMO_MODE:
            self._ok = self._check_connection()

    # ------------------------------------------------------------------
    # Connection check
    # ------------------------------------------------------------------

    def _check_connection(self) -> bool:
        try:
            path = _table_path("cdda_meetings")
            print(f"[fabric] Trying path: {path}", flush=True)
            print(f"[fabric] Client ID: ...{config.FABRIC_CLIENT_ID[-4:]}", flush=True)
            from deltalake import DeltaTable
            dt = DeltaTable(path, storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            print(f"[fabric] ✅ Connection OK — {len(rows)} meetings found", flush=True)
            return True
        except Exception as exc:
            print(f"[fabric] connection check FAILED: {type(exc).__name__}: {exc}", flush=True)
            return False

    def health(self) -> str:
        if config.DEMO_MODE:
            return "Demo Mode — using sample data"
        return "✓ Connected to Fabric Lakehouse" if self._ok else "✗ Lakehouse not reachable"

    # ==================================================================
    # Meetings
    # ==================================================================

    def get_meetings(self) -> List[Dict]:
        if config.DEMO_MODE:
            return self._demo_meetings()
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("cdda_meetings"), storage_options=self._opts)
            return dt.to_pyarrow_table().to_pylist()
        except Exception as exc:
            print(f"[fabric] get_meetings error: {exc}")
            return []

    def get_meeting(self, meeting_id: str) -> Optional[Dict]:
        if config.DEMO_MODE:
            return next((m for m in self._demo_meetings() if m["id"] == meeting_id), None)
        try:
            for m in self.get_meetings():
                if m.get("id") == meeting_id:
                    return m
            return None
        except Exception as exc:
            print(f"[fabric] get_meeting error: {exc}")
            return None

    def create_meeting(self, title: str, description: str,
                       duration: int = 60, forum: str = "ooh") -> Optional[str]:
        mid = f"mtg_{int(datetime.now().timestamp())}"
        if config.DEMO_MODE:
            return mid
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            row = pa.table({
                "id": [mid],
                "title": [title],
                "description": [description],
                "forum": [forum],
                "duration": [duration],
                "created_at": [datetime.now().isoformat()],
            })
            write_deltalake(_table_path("cdda_meetings"), row,
                            mode="append", storage_options=self._opts)
            return mid
        except Exception as exc:
            print(f"[fabric] create_meeting error: {exc}")
            return None

    def update_meeting(self, meeting_id: str, **kwargs) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("cdda_meetings"), storage_options=self._opts)
            safe_mid = _safe_id(meeting_id)
            updates = {k: f"'{_safe_id(str(v))}'" for k, v in kwargs.items()}
            dt.update(predicate=f"id = '{safe_mid}'", updates=updates)
            return True
        except Exception as exc:
            print(f"[fabric] update_meeting error: {exc}")
            return False

    def delete_meeting(self, meeting_id: str) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            safe_mid = _safe_id(meeting_id)
            # cascade: agenda items first
            try:
                dt_items = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
                dt_items.delete(f"meeting_id = '{safe_mid}'")
            except Exception:
                pass
            dt = DeltaTable(_table_path("cdda_meetings"), storage_options=self._opts)
            dt.delete(f"id = '{safe_mid}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_meeting error: {exc}")
            return False

    # ==================================================================
    # Meeting Instances
    # ==================================================================

    def get_meeting_instances(self, meeting_id: str) -> List[Dict]:
        """Return date instances for a meeting forum."""
        if config.DEMO_MODE:
            return self._demo_meeting_instances(meeting_id)
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("meeting_instances"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            return [r for r in rows if r.get("meeting_id") == meeting_id]
        except Exception as exc:
            print(f"[fabric] get_meeting_instances error: {exc}")
            return []

    def create_meeting_instance(self, meeting_id: str, date_str: str,
                                display_text: str) -> Optional[str]:
        """Create a single meeting date instance."""
        iid = f"inst_{int(datetime.now().timestamp())}"
        if config.DEMO_MODE:
            return iid
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            row = pa.table({
                "id": [iid],
                "meeting_id": [meeting_id],
                "date": [date_str],
                "display_text": [display_text],
                "is_available": [True],
            })
            write_deltalake(_table_path("meeting_instances"), row,
                            mode="append", storage_options=self._opts)
            return iid
        except Exception as exc:
            print(f"[fabric] create_meeting_instance error: {exc}")
            return None

    def create_meeting_instances_bulk(self, meeting_id: str,
                                      date_list: List[Dict]) -> List[str]:
        """Create multiple meeting date instances in a single write.

        date_list: [{"date": "YYYY-MM-DD", "display_text": "DD Mon YYYY"}, ...]
        """
        ts = int(datetime.now().timestamp())
        ids = [f"inst_{ts}_{i}" for i in range(len(date_list))]
        if config.DEMO_MODE:
            return ids
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            rows = pa.table({
                "id": ids,
                "meeting_id": [meeting_id] * len(date_list),
                "date": [d["date"] for d in date_list],
                "display_text": [d["display_text"] for d in date_list],
                "is_available": [True] * len(date_list),
            })
            write_deltalake(_table_path("meeting_instances"), rows,
                            mode="append", storage_options=self._opts)
            return ids
        except Exception as exc:
            print(f"[fabric] create_meeting_instances_bulk error: {exc}")
            return []

    def delete_meeting_instance(self, instance_id: str, cascade: bool = False) -> bool:
        """Delete a meeting instance. If cascade, remove its agenda items and docs first."""
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            safe_iid = _safe_id(instance_id)
            if cascade:
                # delete documents for each agenda item in this instance
                try:
                    dt_items = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
                    items = [r for r in dt_items.to_pyarrow_table().to_pylist()
                             if r.get("instance_id") == instance_id]
                    for item in items:
                        try:
                            dt_docs = DeltaTable(_table_path("documents"), storage_options=self._opts)
                            dt_docs.delete(f"item_id = '{_safe_id(item['id'])}'")
                        except Exception:
                            pass
                    dt_items.delete(f"instance_id = '{safe_iid}'")
                except Exception:
                    pass
            dt = DeltaTable(_table_path("meeting_instances"), storage_options=self._opts)
            dt.delete(f"id = '{safe_iid}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_meeting_instance error: {exc}")
            return False

    # ==================================================================
    # Agenda Items
    # ==================================================================

    def get_agenda_items(self, meeting_id: str, instance_id: Optional[str] = None,
                         include_archived: bool = False) -> List[Dict]:
        if config.DEMO_MODE:
            items = self._demo_agenda_items(meeting_id, instance_id)
            if not include_archived:
                items = [r for r in items if r.get("status") != "Archived"]
            return items
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            filtered = [r for r in rows if r.get("meeting_id") == meeting_id]
            if instance_id:
                filtered = [r for r in filtered if r.get("instance_id") == instance_id]
            if not include_archived:
                filtered = [r for r in filtered if r.get("status") != "Archived"]
            return filtered
        except Exception as exc:
            print(f"[fabric] get_agenda_items error: {exc}")
            return []

    def get_archived_items(self, meeting_id: str, instance_id: Optional[str] = None) -> List[Dict]:
        """Return only archived agenda items for a meeting/instance."""
        if config.DEMO_MODE:
            items = self._demo_agenda_items(meeting_id, instance_id, include_all=True)
            return [r for r in items if r.get("status") == "Archived"]
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            filtered = [r for r in rows if r.get("meeting_id") == meeting_id]
            if instance_id:
                filtered = [r for r in filtered if r.get("instance_id") == instance_id]
            return [r for r in filtered if r.get("status") == "Archived"]
        except Exception as exc:
            print(f"[fabric] get_archived_items error: {exc}")
            return []

    def archive_agenda_item(self, item_id: str) -> bool:
        """Soft-delete an agenda item by setting status to Archived."""
        if config.DEMO_MODE:
            return True
        try:
            return self.update_agenda_item(item_id, status='Archived')
        except Exception as exc:
            print(f"[fabric] archive_agenda_item error: {exc}")
            return False

    def restore_agenda_item(self, item_id: str) -> bool:
        """Restore an archived agenda item back to Pending."""
        if config.DEMO_MODE:
            return True
        try:
            return self.update_agenda_item(item_id, status='Pending')
        except Exception as exc:
            print(f"[fabric] restore_agenda_item error: {exc}")
            return False

    def create_agenda_item(self, meeting_id: str, title: str, topic: str,
                           duration: int, presenter: str,
                           instance_id: Optional[str] = None) -> Optional[str]:
        iid = f"itm_{int(datetime.now().timestamp())}"
        if config.DEMO_MODE:
            return iid
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            # figure out next order
            existing = self.get_agenda_items(meeting_id)
            next_order = max((i.get("item_order", 0) for i in existing), default=0) + 1
            row = pa.table({
                "id": [iid],
                "meeting_id": [meeting_id],
                "instance_id": [instance_id or ""],
                "title": [title],
                "topic": [topic],
                "duration": [duration],
                "presenter": [presenter],
                "status": ["Pending"],
                "item_order": [next_order],
                "created_at": [datetime.now().isoformat()],
            })
            write_deltalake(_table_path("agenda_items"), row,
                            mode="append", storage_options=self._opts)
            return iid
        except Exception as exc:
            print(f"[fabric] create_agenda_item error: {exc}")
            return None

    def update_agenda_item(self, item_id: str, **kwargs) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            safe_iid = _safe_id(item_id)
            updates = {k: f"'{_safe_id(str(v))}'" for k, v in kwargs.items()}
            dt.update(predicate=f"id = '{safe_iid}'", updates=updates)
            return True
        except Exception as exc:
            print(f"[fabric] update_agenda_item error: {exc}")
            return False

    def delete_agenda_item(self, item_id: str) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            safe_iid = _safe_id(item_id)
            # cascade: documents first
            try:
                dt_docs = DeltaTable(_table_path("documents"), storage_options=self._opts)
                dt_docs.delete(f"item_id = '{safe_iid}'")
            except Exception:
                pass
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            dt.delete(f"id = '{safe_iid}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_agenda_item error: {exc}")
            return False

    # ==================================================================
    # Documents
    # ==================================================================

    def get_documents(self, item_id: str) -> List[Dict]:
        if config.DEMO_MODE:
            return self._demo_documents(item_id)
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("documents"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            return [r for r in rows if r.get("item_id") == item_id]
        except Exception as exc:
            print(f"[fabric] get_documents error: {exc}")
            return []

    def upload_document(self, item_id: str, filename: str, content: bytes) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            doc_id = f"doc_{int(datetime.now().timestamp())}"
            row = pa.table({
                "id": [doc_id],
                "item_id": [item_id],
                "filename": [filename],
                "doc_type": [filename.rsplit(".", 1)[-1] if "." in filename else "unknown"],
                "file_size": [len(content)],
                "uploaded_at": [datetime.now().isoformat()],
            })
            write_deltalake(_table_path("documents"), row,
                            mode="append", storage_options=self._opts)
            return True
        except Exception as exc:
            print(f"[fabric] upload_document error: {exc}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("documents"), storage_options=self._opts)
            dt.delete(f"id = '{_safe_id(doc_id)}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_document error: {exc}")
            return False

    # ==================================================================
    # Approvals
    # ==================================================================

    def get_approvals(self, item_id: str) -> List[Dict]:
        if config.DEMO_MODE:
            return []
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("approvals"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            return [r for r in rows if r.get("item_id") == item_id]
        except Exception as exc:
            print(f"[fabric] get_approvals error: {exc}")
            return []

    def set_approval(self, item_id: str, approver: str, approved: bool) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            import pyarrow as pa
            from deltalake import write_deltalake
            apv_id = f"apv_{int(datetime.now().timestamp())}"
            row = pa.table({
                "id": [apv_id],
                "item_id": [item_id],
                "approver": [approver],
                "approved": [approved],
                "approved_at": [datetime.now().isoformat()],
            })
            write_deltalake(_table_path("approvals"), row,
                            mode="append", storage_options=self._opts)
            # also update the agenda item status
            self.update_agenda_item(item_id, status="Approved" if approved else "Rejected")
            return True
        except Exception as exc:
            print(f"[fabric] set_approval error: {exc}")
            return False

    # ==================================================================
    # Demo data
    # ==================================================================

    def _demo_meetings(self) -> List[Dict]:
        return [
            {"id": "mtg_1", "title": "CDDA Open Office Hours",
             "description": (
                 "CDDA Open Office Hours is a standing, open-access forum run "
                 "within the Clinical Development & Design (CDDA) organization "
                 "to support knowledge sharing, Q&A, and informal problem-solving "
                 "across CDDA initiatives, tools, and ways of working. It is "
                 "designed to complement formal governance and project meetings "
                 "by providing a low-barrier, interactive space for discussion."
             ),
             "forum": "ooh", "duration": 60,
             "created_at": "2024-09-01T10:00:00"},
            {"id": "mtg_2", "title": "Clinical Design & Statistics Review (CDSR)",
             "description": (
                 "The Clinical Design & Statistics Review (CDSR) is a standing "
                 "review forum where clinical design and statistics leaders come "
                 "together to evaluate study designs for Phase 2 and later-phase "
                 "interventional trials. The group provides expert input early in "
                 "the process to help teams make informed design decisions, ensure "
                 "scientific rigor, and share learnings across therapeutic areas."
             ),
             "forum": "cdsr", "duration": 90,
             "created_at": "2024-09-03T14:00:00"},
        ]

    def _demo_meeting_instances(self, meeting_id: str) -> List[Dict]:
        instances = {
            "mtg_1": [
                {"id": "inst_1", "meeting_id": "mtg_1", "date": "2026-01-07",
                 "display_text": "07 Jan 2026", "is_available": True},
                {"id": "inst_2", "meeting_id": "mtg_1", "date": "2026-01-14",
                 "display_text": "14 Jan 2026", "is_available": True},
                {"id": "inst_3", "meeting_id": "mtg_1", "date": "2026-01-21",
                 "display_text": "21 Jan 2026", "is_available": True},
                {"id": "inst_4", "meeting_id": "mtg_1", "date": "2026-01-28",
                 "display_text": "28 Jan 2026", "is_available": True},
            ],
            "mtg_2": [
                {"id": "inst_5", "meeting_id": "mtg_2", "date": "2026-01-10",
                 "display_text": "10 Jan 2026", "is_available": True},
                {"id": "inst_6", "meeting_id": "mtg_2", "date": "2026-01-24",
                 "display_text": "24 Jan 2026", "is_available": True},
                {"id": "inst_7", "meeting_id": "mtg_2", "date": "2026-02-07",
                 "display_text": "07 Feb 2026", "is_available": True},
            ],
        }
        return instances.get(meeting_id, [])

    def _demo_agenda_items(self, meeting_id: str, instance_id: Optional[str] = None,
                           include_all: bool = False) -> List[Dict]:
        items_by_instance = {
            "inst_1": [
                {"id": "itm_1", "meeting_id": "mtg_1", "instance_id": "inst_1",
                 "title": "Request Intake Walkthrough", "duration": 15,
                 "presenter": "Jane Smith",
                 "topic": "Walk through recent request intake process",
                 "status": "Pending", "item_order": 1,
                 "created_at": "2026-01-05T09:00:00"},
                {"id": "itm_2", "meeting_id": "mtg_1", "instance_id": "inst_1",
                 "title": "Open Q&A: Tooling Refresh", "duration": 30,
                 "presenter": "John Doe",
                 "topic": "Discussion on new tooling updates",
                 "status": "Pending", "item_order": 2,
                 "created_at": "2026-01-05T09:15:00"},
                {"id": "itm_archived_1", "meeting_id": "mtg_1", "instance_id": "inst_1",
                 "title": "Legacy Process Review (Archived)", "duration": 15,
                 "presenter": "Bob Wilson",
                 "topic": "Old process review — archived",
                 "status": "Archived", "item_order": 99,
                 "created_at": "2025-12-20T10:00:00"},
            ],
            "inst_3": [
                {"id": "itm_3", "meeting_id": "mtg_1", "instance_id": "inst_3",
                 "title": "Process Improvements", "duration": 20,
                 "presenter": "Sarah Johnson",
                 "topic": "Review Q1 process improvements",
                 "status": "Pending", "item_order": 1,
                 "created_at": "2026-01-19T10:00:00"},
            ],
            "inst_5": [
                {"id": "itm_4", "meeting_id": "mtg_2", "instance_id": "inst_5",
                 "title": "Protocol Design Review", "duration": 45,
                 "presenter": "Dr. Chen",
                 "topic": "Review new protocol design approach",
                 "status": "Pending", "item_order": 1,
                 "created_at": "2026-01-08T14:00:00"},
                {"id": "itm_5", "meeting_id": "mtg_2", "instance_id": "inst_5",
                 "title": "Statistical Analysis Plan", "duration": 25,
                 "presenter": "Maria Garcia",
                 "topic": "Discussion of updated SAP",
                 "status": "Pending", "item_order": 2,
                 "created_at": "2026-01-08T14:30:00"},
            ],
            "inst_7": [
                {"id": "itm_6", "meeting_id": "mtg_2", "instance_id": "inst_7",
                 "title": "Statistical Interim Analysis", "duration": 30,
                 "presenter": "Dr. Chen",
                 "topic": "",
                 "status": "Pending", "item_order": 1,
                 "created_at": "2026-02-05T14:00:00"},
            ],
        }

        if instance_id is not None:
            return items_by_instance.get(instance_id, [])

        # Backward compatibility: no instance_id means return all items
        # for the given meeting_id.
        all_items: List[Dict] = []
        for items in items_by_instance.values():
            for item in items:
                if item["meeting_id"] == meeting_id:
                    all_items.append(item)
        return all_items

    def _demo_documents(self, item_id: str) -> List[Dict]:
        docs = {
            "itm_1": [
                {"id": "doc_1", "item_id": "itm_1",
                 "filename": "Site-Country MS Order.xlsx", "doc_type": "xlsx"},
                {"id": "doc_2", "item_id": "itm_1",
                 "filename": "Example recruitment projections.xlsx", "doc_type": "xlsx"},
            ],
            "itm_4": [
                {"id": "doc_3", "item_id": "itm_4",
                 "filename": "Protocol_v2_draft.pdf", "doc_type": "pdf"},
            ],
        }
        return docs.get(item_id, [])


# ============================================================================
# Singleton
# ============================================================================

_data_layer = None


def get_data_layer() -> FabricDataLayer:
    global _data_layer
    if _data_layer is None:
        _data_layer = FabricDataLayer()
    return _data_layer


def health():
    return get_data_layer().health()
