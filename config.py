import os
from dotenv import load_dotenv
load_dotenv()

FABRIC_WORKSPACE_ID = os.getenv('FABRIC_WORKSPACE_ID', '')
FABRIC_LAKEHOUSE_NAME = os.getenv('FABRIC_LAKEHOUSE_NAME', 'cdda_meeting_data')
FABRIC_CLIENT_ID = os.getenv('FABRIC_CLIENT_ID', '')
FABRIC_CLIENT_SECRET = os.getenv('FABRIC_CLIENT_SECRET', '')
FABRIC_TENANT_ID = os.getenv('FABRIC_TENANT_ID', '')
DEMO_MODE = os.getenv('DEMO_MODE', '1').lower() in ('1', 'true', 'yes')
