"""
Fabric Lakehouse data layer for CDDA Meeting Manager.
Uses the deltalake library for Delta Lake table operations on OneLake.
"""

from typing import List, Dict, Optional
from datetime import datetime

import config

# ============================================================================
# OneLake path helpers
# ============================================================================

ONELAKE_BASE = (
    f"abfss://{config.FABRIC_WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com"
    f"/{config.FABRIC_LAKEHOUSE_ID}/Tables"
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
            from deltalake import DeltaTable
            DeltaTable(_table_path("cdda_meetings"), storage_options=self._opts)
            return True
        except Exception as exc:
            print(f"[fabric] connection check failed: {exc}")
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
            updates = {k: f"'{v}'" for k, v in kwargs.items()}
            dt.update(predicate=f"id = '{meeting_id}'", updates=updates)
            return True
        except Exception as exc:
            print(f"[fabric] update_meeting error: {exc}")
            return False

    def delete_meeting(self, meeting_id: str) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            # cascade: agenda items first
            try:
                dt_items = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
                dt_items.delete(f"meeting_id = '{meeting_id}'")
            except Exception:
                pass
            dt = DeltaTable(_table_path("cdda_meetings"), storage_options=self._opts)
            dt.delete(f"id = '{meeting_id}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_meeting error: {exc}")
            return False

    # ==================================================================
    # Agenda Items
    # ==================================================================

    def get_agenda_items(self, meeting_id: str) -> List[Dict]:
        if config.DEMO_MODE:
            return self._demo_agenda_items(meeting_id)
        try:
            from deltalake import DeltaTable
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            rows = dt.to_pyarrow_table().to_pylist()
            return [r for r in rows if r.get("meeting_id") == meeting_id]
        except Exception as exc:
            print(f"[fabric] get_agenda_items error: {exc}")
            return []

    def create_agenda_item(self, meeting_id: str, title: str, topic: str,
                           duration: int, presenter: str) -> Optional[str]:
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
            updates = {k: f"'{v}'" for k, v in kwargs.items()}
            dt.update(predicate=f"id = '{item_id}'", updates=updates)
            return True
        except Exception as exc:
            print(f"[fabric] update_agenda_item error: {exc}")
            return False

    def delete_agenda_item(self, item_id: str) -> bool:
        if config.DEMO_MODE:
            return True
        try:
            from deltalake import DeltaTable
            # cascade: documents first
            try:
                dt_docs = DeltaTable(_table_path("documents"), storage_options=self._opts)
                dt_docs.delete(f"item_id = '{item_id}'")
            except Exception:
                pass
            dt = DeltaTable(_table_path("agenda_items"), storage_options=self._opts)
            dt.delete(f"id = '{item_id}'")
            return True
        except Exception as exc:
            print(f"[fabric] delete_agenda_item error: {exc}")
            return False

    # ==================================================================
    # Documents
    # ==================================================================

    def get_documents(self, item_id: str) -> List[Dict]:
        if config.DEMO_MODE:
            return []
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
            dt.delete(f"id = '{doc_id}'")
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
             "description": "Regular forum for open discussions",
             "forum": "ooh", "duration": 60,
             "created_at": "2024-09-01T10:00:00"},
            {"id": "mtg_2", "title": "Clinical Design & Statistics Review",
             "description": "Review forum for clinical design topics",
             "forum": "cdsr", "duration": 90,
             "created_at": "2024-09-03T14:00:00"},
        ]

    def _demo_agenda_items(self, meeting_id: str) -> List[Dict]:
        if meeting_id == "mtg_1":
            return [
                {"id": "itm_1", "meeting_id": "mtg_1", "title": "Project Updates",
                 "topic": "Current project status", "duration": 15,
                 "presenter": "John Smith", "status": "Pending", "item_order": 1,
                 "created_at": "2024-09-01T09:30:00"},
                {"id": "itm_2", "meeting_id": "mtg_1", "title": "Q&A Session",
                 "topic": "Open questions and discussion", "duration": 30,
                 "presenter": "Team", "status": "Pending", "item_order": 2,
                 "created_at": "2024-09-01T09:45:00"},
            ]
        return []


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
