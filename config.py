import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Fabric Lakehouse Configuration
# ============================================================================
FABRIC_WORKSPACE_ID = os.getenv('FABRIC_WORKSPACE_ID', '')
FABRIC_LAKEHOUSE_ID = os.getenv('FABRIC_LAKEHOUSE_ID', '')
FABRIC_LAKEHOUSE_NAME = os.getenv('FABRIC_LAKEHOUSE_NAME', 'CDDA_Meeting_Manager_Lakehouse')
FABRIC_CLIENT_ID = os.getenv('FABRIC_CLIENT_ID', '')
FABRIC_CLIENT_SECRET = os.getenv('FABRIC_CLIENT_SECRET', '')
FABRIC_TENANT_ID = os.getenv('FABRIC_TENANT_ID', '')

# ============================================================================
# Application Configuration
# ============================================================================
DEMO_MODE = os.getenv('DEMO_MODE', '0').lower() in ('1', 'true', 'yes')
DEV_USER_EMAIL = os.getenv('DEV_USER_EMAIL', '')
DEFAULT_MEETING_DURATION = 60
APP_ENVIRONMENT = os.getenv('APP_ENVIRONMENT', 'Development')

# ============================================================================
# Access Control
# ============================================================================
REQUIRED_AD_GROUP = os.getenv('REQUIRED_AD_GROUP', '')
APPROVER_EMAILS = [e.strip().lower() for e in os.getenv('APPROVER_EMAILS', '').split(',') if e.strip()] if os.getenv('APPROVER_EMAILS') else []
RLS_ADMINS = [e.strip().lower() for e in os.getenv('RLS_ADMINS', '').split(',') if e.strip()] if os.getenv('RLS_ADMINS') else []

# ============================================================================
# Application Settings
# ============================================================================
APP_NAME = 'CDDA Meeting Manager'
TIME_SLOTS = [15, 30, 45, 60]

