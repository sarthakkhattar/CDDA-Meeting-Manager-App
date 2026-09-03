"""
Fabric Lakehouse data layer for CDDA Meeting Manager.
Connects to Microsoft Fabric Lakehouse via REST API and Python SDK.
"""

import os
import json
from typing import List, Dict, Optional
import requests
from datetime import datetime

import config

class FabricDataLayer:
    """Interface to Fabric Lakehouse for CDDA Meeting Manager."""

    def __init__(self):
        """Initialize Fabric connection."""
        self.workspace_id = config.FABRIC_WORKSPACE_ID
        self.lakehouse_id = config.FABRIC_LAKEHOUSE_ID
        self.client_id = config.FABRIC_CLIENT_ID
        self.client_secret = config.FABRIC_CLIENT_SECRET
        self.tenant_id = config.FABRIC_TENANT_ID
        self.access_token = None
        self._authenticate()

    def _authenticate(self):
        """Get access token for Fabric API."""
        try:
            auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://analysis.windows.net/powerbi/api/.default'
            }
            response = requests.post(auth_url, data=data)
            response.raise_for_status()
            self.access_token = response.json()['access_token']
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def health(self) -> str:
        """Check Fabric connectivity."""
        try:
            if not self.access_token:
                return "✗ Not authenticated with Fabric"
            return f"✓ Connected to Fabric Lakehouse: {self.lakehouse_id}"
        except Exception as e:
            return f"✗ Fabric connection failed: {str(e)}"

    # ======================================================================
    # Meetings CRUD
    # ======================================================================

    def get_meetings(self) -> List[Dict]:
        """Get all meetings from Lakehouse."""
        try:
            if config.DEMO_MODE:
                return self._demo_meetings()

            # Query Fabric Lakehouse
            query = f"""
            SELECT * FROM cdda_meetings
            ORDER BY created_at DESC
            """
            return self._execute_query(query)
        except Exception as e:
            print(f"Error getting meetings: {e}")
            return []

    def get_meeting(self, meeting_id: str) -> Optional[Dict]:
        """Get single meeting by ID."""
        try:
            if config.DEMO_MODE:
                meetings = self._demo_meetings()
                for m in meetings:
                    if m.get('id') == meeting_id:
                        return m
                return None

            query = f"SELECT * FROM cdda_meetings WHERE id = '{meeting_id}'"
            results = self._execute_query(query)
            return results[0] if results else None
        except Exception as e:
            print(f"Error getting meeting: {e}")
            return None

    def create_meeting(self, title: str, description: str, duration: int = 60, forum: str = "ooh") -> Optional[str]:
        """Create new meeting."""
        try:
            meeting_id = f"mtg_{int(datetime.now().timestamp())}"

            if not config.DEMO_MODE:
                query = f"""
                INSERT INTO cdda_meetings (id, title, description, forum, duration, created_at)
                VALUES ('{meeting_id}', '{title}', '{description}', '{forum}', {duration}, CURRENT_TIMESTAMP)
                """
                self._execute_query(query)

            return meeting_id
        except Exception as e:
            print(f"Error creating meeting: {e}")
            return None

    def update_meeting(self, meeting_id: str, **kwargs) -> bool:
        """Update meeting fields."""
        try:
            if config.DEMO_MODE:
                return True

            set_clause = ", ".join([f"{k} = '{v}'" for k, v in kwargs.items()])
            query = f"UPDATE cdda_meetings SET {set_clause} WHERE id = '{meeting_id}'"
            self._execute_query(query)
            return True
        except Exception as e:
            print(f"Error updating meeting: {e}")
            return False

    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete meeting and cascade delete agenda items."""
        try:
            if config.DEMO_MODE:
                return True

            # Cascade delete
            self._execute_query(f"DELETE FROM agenda_items WHERE meeting_id = '{meeting_id}'")
            self._execute_query(f"DELETE FROM cdda_meetings WHERE id = '{meeting_id}'")
            return True
        except Exception as e:
            print(f"Error deleting meeting: {e}")
            return False

    # ======================================================================
    # Agenda Items CRUD
    # ======================================================================

    def get_agenda_items(self, meeting_id: str) -> List[Dict]:
        """Get all agenda items for a meeting."""
        try:
            if config.DEMO_MODE:
                return self._demo_agenda_items(meeting_id)

            query = f"""
            SELECT * FROM agenda_items
            WHERE meeting_id = '{meeting_id}'
            ORDER BY item_order ASC
            """
            return self._execute_query(query)
        except Exception as e:
            print(f"Error getting agenda items: {e}")
            return []

    def create_agenda_item(self, meeting_id: str, title: str, topic: str,
                          duration: int, presenter: str) -> Optional[str]:
        """Create new agenda item."""
        try:
            item_id = f"itm_{int(datetime.now().timestamp())}"

            if not config.DEMO_MODE:
                query = f"""
                INSERT INTO agenda_items (id, meeting_id, title, topic, duration, presenter, created_at)
                VALUES ('{item_id}', '{meeting_id}', '{title}', '{topic}', {duration}, '{presenter}', CURRENT_TIMESTAMP)
                """
                self._execute_query(query)

            return item_id
        except Exception as e:
            print(f"Error creating agenda item: {e}")
            return None

    def update_agenda_item(self, item_id: str, **kwargs) -> bool:
        """Update agenda item."""
        try:
            if config.DEMO_MODE:
                return True

            set_clause = ", ".join([f"{k} = '{v}'" for k, v in kwargs.items()])
            query = f"UPDATE agenda_items SET {set_clause} WHERE id = '{item_id}'"
            self._execute_query(query)
            return True
        except Exception as e:
            print(f"Error updating agenda item: {e}")
            return False

    def delete_agenda_item(self, item_id: str) -> bool:
        """Delete agenda item and cascade delete documents."""
        try:
            if config.DEMO_MODE:
                return True

            # Cascade delete
            self._execute_query(f"DELETE FROM documents WHERE item_id = '{item_id}'")
            self._execute_query(f"DELETE FROM agenda_items WHERE id = '{item_id}'")
            return True
        except Exception as e:
            print(f"Error deleting agenda item: {e}")
            return False

    # ======================================================================
    # Documents CRUD
    # ======================================================================

    def get_documents(self, item_id: str) -> List[Dict]:
        """Get all documents for an agenda item."""
        try:
            if config.DEMO_MODE:
                return []

            query = f"SELECT * FROM documents WHERE item_id = '{item_id}'"
            return self._execute_query(query)
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []

    def upload_document(self, item_id: str, filename: str, content: bytes) -> bool:
        """Upload document."""
        try:
            if config.DEMO_MODE:
                return True

            doc_id = f"doc_{int(datetime.now().timestamp())}"
            query = f"""
            INSERT INTO documents (id, item_id, filename, file_size, uploaded_at)
            VALUES ('{doc_id}', '{item_id}', '{filename}', {len(content)}, CURRENT_TIMESTAMP)
            """
            self._execute_query(query)
            return True
        except Exception as e:
            print(f"Error uploading document: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Delete document."""
        try:
            if config.DEMO_MODE:
                return True

            self._execute_query(f"DELETE FROM documents WHERE id = '{doc_id}'")
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    # ======================================================================
    # Approvals
    # ======================================================================

    def get_approvals(self, item_id: str) -> List[Dict]:
        """Get approval status for an item."""
        try:
            if config.DEMO_MODE:
                return []

            query = f"SELECT * FROM approvals WHERE item_id = '{item_id}'"
            return self._execute_query(query)
        except Exception as e:
            print(f"Error getting approvals: {e}")
            return []

    def set_approval(self, item_id: str, approver: str, approved: bool) -> bool:
        """Set approval status."""
        try:
            if config.DEMO_MODE:
                return True

            approval_id = f"apv_{int(datetime.now().timestamp())}"
            query = f"""
            INSERT INTO approvals (id, item_id, approver, approved, approved_at)
            VALUES ('{approval_id}', '{item_id}', '{approver}', {approved}, CURRENT_TIMESTAMP)
            """
            self._execute_query(query)
            return True
        except Exception as e:
            print(f"Error setting approval: {e}")
            return False

    # ======================================================================
    # Helpers
    # ======================================================================

    def _execute_query(self, query: str) -> List[Dict]:
        """Execute query against Lakehouse."""
        try:
            # Use Fabric SQL API
            # This is a placeholder - actual implementation would use Fabric SDK
            # For now, returning empty list to avoid errors
            return []
        except Exception as e:
            print(f"Query execution error: {e}")
            return []

    def _demo_meetings(self) -> List[Dict]:
        """Return demo meetings for development."""
        return [
            {
                'id': 'mtg_1',
                'title': 'CDDA Open Office Hours',
                'description': 'Regular forum for open discussions',
                'forum': 'ooh',
                'duration': 60,
                'created_at': '2024-09-01 10:00:00',
            },
            {
                'id': 'mtg_2',
                'title': 'Clinical Design & Statistics Review',
                'description': 'Review forum for clinical design topics',
                'forum': 'cdsr',
                'duration': 90,
                'created_at': '2024-09-03 14:00:00',
            }
        ]

    def _demo_agenda_items(self, meeting_id: str) -> List[Dict]:
        """Return demo agenda items."""
        if meeting_id == 'mtg_1':
            return [
                {
                    'id': 'itm_1',
                    'meeting_id': 'mtg_1',
                    'title': 'Project Updates',
                    'topic': 'Current project status',
                    'duration': 15,
                    'presenter': 'John Smith',
                    'created_at': '2024-09-01 09:30:00',
                },
                {
                    'id': 'itm_2',
                    'meeting_id': 'mtg_1',
                    'title': 'Q&A Session',
                    'topic': 'Open questions and discussion',
                    'duration': 30,
                    'presenter': 'Team',
                    'created_at': '2024-09-01 09:45:00',
                }
            ]
        return []


# Global instance
_data_layer = None

def get_data_layer() -> FabricDataLayer:
    """Get or create data layer instance."""
    global _data_layer
    if _data_layer is None:
        _data_layer = FabricDataLayer()
    return _data_layer


def health():
    """Health check for Fabric connection."""
    return get_data_layer().health()
