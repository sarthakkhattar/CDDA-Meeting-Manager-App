"""
Email notification service using Microsoft Graph API.
Uses the same Service Principal credentials as Fabric Lakehouse.
Requires Mail.Send application permission on the SP in Azure AD.
"""

import requests
import logging
from html import escape as _esc
import config

logger = logging.getLogger(__name__)


def _get_graph_token():
    """Get an access token for Microsoft Graph using the Service Principal."""
    url = f"https://login.microsoftonline.com/{config.FABRIC_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": config.FABRIC_CLIENT_ID,
        "client_secret": config.FABRIC_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_approval_email(to_email, to_name, item_title, meeting_title, date_text, approved_by):
    """Send an approval notification email via Microsoft Graph.

    Returns True if sent successfully, False otherwise.
    Never raises — failures are logged but don't break the approval flow.
    """
    if not config.GRAPH_NOTIFICATIONS_ENABLED:
        logger.info("[email] Notifications disabled (GRAPH_NOTIFICATIONS_ENABLED=0)")
        return False

    if not config.NOTIFICATION_FROM_EMAIL:
        logger.warning("[email] NOTIFICATION_FROM_EMAIL not set — skipping")
        return False

    if not to_email:
        logger.warning("[email] No recipient email — skipping")
        return False

    try:
        token = _get_graph_token()

        subject = f"Agenda Item Approved: {item_title}"

        # HTML-escape all user-supplied values to prevent XSS injection
        safe_item = _esc(item_title)
        safe_meeting = _esc(meeting_title)
        safe_date = _esc(date_text)
        safe_approver = _esc(approved_by)

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0B1D3A, #1E4EBC); padding: 24px 32px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0; font-size: 20px;">CDDA Meeting Manager</h2>
            </div>
            <div style="background: white; padding: 24px 32px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                <p style="color: #198754; font-size: 16px; font-weight: 600; margin-top: 0;">
                    ✓ Your agenda item has been approved
                </p>
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <tr>
                        <td style="padding: 8px 0; color: #666; width: 120px;">Item:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #0B1D3A;">{safe_item}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;">Meeting:</td>
                        <td style="padding: 8px 0;">{safe_meeting}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;">Date:</td>
                        <td style="padding: 8px 0;">{safe_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;">Approved by:</td>
                        <td style="padding: 8px 0;">{safe_approver}</td>
                    </tr>
                </table>
                <p style="color: #666; font-size: 13px; margin-bottom: 0;">
                    This is an automated notification from the CDDA Meeting Manager.
                </p>
            </div>
        </div>
        """

        # Microsoft Graph sendMail endpoint
        url = f"https://graph.microsoft.com/v1.0/users/{config.NOTIFICATION_FROM_EMAIL}/sendMail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body,
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email,
                            "name": to_name,
                        }
                    }
                ],
            },
            "saveToSentItems": False,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)

        if resp.status_code == 202:
            logger.info(f"[email] Approval notification sent to {to_email}")
            print(f"[email] Approval notification sent to {to_email}", flush=True)
            return True
        else:
            logger.warning(f"[email] Graph API returned {resp.status_code}: {resp.text}")
            print(f"[email] Graph API returned {resp.status_code}: {resp.text}", flush=True)
            return False

    except Exception as exc:
        logger.warning(f"[email] Failed to send notification: {exc}")
        print(f"[email] Failed to send notification: {exc}", flush=True)
        return False
