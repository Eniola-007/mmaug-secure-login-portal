import html
import logging
from urllib.parse import urlencode

from azure.communication.email import EmailClient
from azure.identity import ManagedIdentityCredential

from app.config import get_settings

logger = logging.getLogger(__name__)


def _client() -> EmailClient:
    settings = get_settings()
    credential = ManagedIdentityCredential(client_id=settings.azure_client_id or None)
    return EmailClient(settings.acs_email_endpoint, credential)


def _send(*, recipient: str, display_name: str, subject: str, html_body: str) -> bool:
    settings = get_settings()
    if not settings.email_delivery_enabled:
        logger.info("Email delivery is disabled; no message was sent")
        return False
    if not settings.acs_email_endpoint or not settings.acs_email_sender:
        logger.error("Email delivery is enabled but Azure Communication Services is incomplete")
        return False

    message = {
        "senderAddress": settings.acs_email_sender,
        "recipients": {
            "to": [{"address": recipient, "displayName": display_name}],
        },
        "content": {
            "subject": subject,
            "plainText": "Use the secure MMAUG portal link in this email. The link expires soon.",
            "html": html_body,
        },
    }
    try:
        # The initial 202 response confirms that ACS accepted the message. Do not
        # hold an interactive authentication request open while ACS polls for the
        # final mailbox-delivery status, which can take several minutes.
        _client().begin_send(message, polling=False).result()
    except Exception:  # Azure SDK exceptions vary by transport and service response.
        logger.exception("Azure Communication Services email delivery failed")
        return False
    return True


def send_verification_email(recipient: str, display_name: str, token: str) -> bool:
    settings = get_settings()
    link = f"{settings.public_frontend_url.rstrip('/')}?{urlencode({'verify_email': token})}"
    safe_name = html.escape(display_name)
    safe_link = html.escape(link, quote=True)
    return _send(
        recipient=recipient,
        display_name=display_name,
        subject="Verify your MMAUG portal email",
        html_body=f"""
        <div style="font-family:Arial,sans-serif;color:#18352c;line-height:1.6">
          <h1 style="color:#0d382d">Verify your email</h1>
          <p>Hello {safe_name},</p>
          <p>Confirm that you own this email address. School approval is a separate step.</p>
          <p><a href="{safe_link}" style="background:#cf963c;color:#fff;padding:12px 18px;
          border-radius:8px;text-decoration:none;font-weight:bold">Verify email</a></p>
          <p>This link expires in {settings.email_verification_minutes} minutes. If you did
          not request this account, you can ignore this message.</p>
        </div>
        """,
    )


def send_password_reset_email(recipient: str, display_name: str, token: str) -> bool:
    settings = get_settings()
    link = f"{settings.public_frontend_url.rstrip('/')}?{urlencode({'reset_password': token})}"
    safe_name = html.escape(display_name)
    safe_link = html.escape(link, quote=True)
    return _send(
        recipient=recipient,
        display_name=display_name,
        subject="Reset your MMAUG portal password",
        html_body=f"""
        <div style="font-family:Arial,sans-serif;color:#18352c;line-height:1.6">
          <h1 style="color:#0d382d">Reset your password</h1>
          <p>Hello {safe_name},</p>
          <p>Use this one-time link to choose a new password.</p>
          <p><a href="{safe_link}" style="background:#cf963c;color:#fff;padding:12px 18px;
          border-radius:8px;text-decoration:none;font-weight:bold">Reset password</a></p>
          <p>This link expires in {settings.password_reset_minutes} minutes. If you did not
          request a reset, you can ignore this message.</p>
        </div>
        """,
    )


def send_password_setup_email(recipient: str, display_name: str, token: str) -> bool:
    settings = get_settings()
    link = f"{settings.public_frontend_url.rstrip('/')}?{urlencode({'reset_password': token})}"
    safe_name = html.escape(display_name)
    safe_link = html.escape(link, quote=True)
    return _send(
        recipient=recipient,
        display_name=display_name,
        subject="Set up your MMAUG portal password",
        html_body=f"""
        <div style="font-family:Arial,sans-serif;color:#18352c;line-height:1.6">
          <h1 style="color:#0d382d">Set up your portal password</h1>
          <p>Hello {safe_name},</p>
          <p>Your school account is already enrolled. Use this one-time link to verify your
          email address and choose your local portal password.</p>
          <p><a href="{safe_link}" style="background:#cf963c;color:#fff;padding:12px 18px;
          border-radius:8px;text-decoration:none;font-weight:bold">Set up password</a></p>
          <p>This link expires in {settings.password_reset_minutes} minutes. If you did not
          request local access, you can ignore this message.</p>
        </div>
        """,
    )


def send_microsoft_registration_email(recipient: str, display_name: str) -> bool:
    settings = get_settings()
    safe_name = html.escape(display_name)
    safe_portal_url = html.escape(settings.public_frontend_url.rstrip("/"), quote=True)
    return _send(
        recipient=recipient,
        display_name=display_name,
        subject="Your MMAUG portal request was received",
        html_body=f"""
        <div style="font-family:Arial,sans-serif;color:#18352c;line-height:1.6">
          <h1 style="color:#0d382d">Microsoft identity confirmed</h1>
          <p>Hello {safe_name},</p>
          <p>Your Microsoft identity is verified and your MMAUG portal request was received.
          A school administrator must still approve and assign your database role.</p>
          <p><a href="{safe_portal_url}" style="background:#cf963c;color:#fff;padding:12px 18px;
          border-radius:8px;text-decoration:none;font-weight:bold">Return to the portal</a></p>
          <p>If you did not request this account, contact an authorized school administrator.</p>
        </div>
        """,
    )


def send_admin_verification_alert(
    recipient: str,
    admin_name: str,
    verified_name: str,
    verified_email: str,
) -> bool:
    settings = get_settings()
    safe_admin_name = html.escape(admin_name)
    safe_verified_name = html.escape(verified_name)
    safe_verified_email = html.escape(verified_email)
    safe_portal_url = html.escape(settings.public_frontend_url.rstrip("/"), quote=True)
    return _send(
        recipient=recipient,
        display_name=admin_name,
        subject="MMAUG account verified and ready for review",
        html_body=f"""
        <div style="font-family:Arial,sans-serif;color:#18352c;line-height:1.6">
          <h1 style="color:#0d382d">Account ready for administrator review</h1>
          <p>Hello {safe_admin_name},</p>
          <p>{safe_verified_name} ({safe_verified_email}) has completed identity verification.
          The account is ready for a database-role decision in
          <strong>People &amp; access</strong>.</p>
          <p><a href="{safe_portal_url}" style="background:#cf963c;color:#fff;padding:12px 18px;
          border-radius:8px;text-decoration:none;font-weight:bold">Review account</a></p>
          <p>Approve only recognized school users and assign the minimum required role.</p>
        </div>
        """,
    )
