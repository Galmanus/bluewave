"""Transactional email service using Resend.

All functions are fire-and-forget: they log warnings on failure but never
raise exceptions, so callers (typically BackgroundTasks) are never blocked.
When RESEND_API_KEY is empty the functions silently skip sending (dev mode).
"""

import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("bluewave.email")


def _resend_configured() -> bool:
    """Return True if Resend is configured, else log a warning."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email send (dev mode)")
        return False
    return True


def _init_resend() -> None:
    """Lazily configure the resend SDK with the API key."""
    import resend
    resend.api_key = settings.RESEND_API_KEY


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

async def send_password_reset(email: str, reset_token: str, full_name: str) -> None:
    """Send a password-reset link to the user."""
    if not _resend_configured():
        return
    try:
        _init_resend()
        import resend

        reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"
        html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
  <h2 style="color: #1a1a2e; margin-bottom: 16px;">Password Reset</h2>
  <p style="color: #4a4a68; line-height: 1.6;">Hi {full_name},</p>
  <p style="color: #4a4a68; line-height: 1.6;">
    We received a request to reset your Bluewave password. Click the button below to choose a new one.
  </p>
  <a href="{reset_url}"
     style="display: inline-block; background: #2563eb; color: #ffffff; padding: 12px 24px;
            border-radius: 8px; text-decoration: none; font-weight: 600; margin: 24px 0;">
    Reset Password
  </a>
  <p style="color: #9ca3af; font-size: 13px; line-height: 1.5;">
    If you didn't request this, you can safely ignore this email. The link expires in 15 minutes.
  </p>
</div>"""

        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": "Reset your Bluewave password",
            "html": html,
        })
        logger.info("Password reset email sent to %s", email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", email)


# ---------------------------------------------------------------------------
# User invitation
# ---------------------------------------------------------------------------

async def send_user_invitation(
    email: str,
    full_name: str,
    inviter_name: str,
    tenant_name: str,
    temp_password: str,
) -> None:
    """Send an invitation email with temporary credentials."""
    if not _resend_configured():
        return
    try:
        _init_resend()
        import resend

        login_url = f"{settings.APP_URL}/login"
        html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
  <h2 style="color: #1a1a2e; margin-bottom: 16px;">You're Invited!</h2>
  <p style="color: #4a4a68; line-height: 1.6;">Hi {full_name},</p>
  <p style="color: #4a4a68; line-height: 1.6;">
    {inviter_name} has invited you to join <strong>{tenant_name}</strong> on Bluewave.
  </p>
  <div style="background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 24px 0;">
    <p style="margin: 0 0 8px 0; color: #4a4a68;"><strong>Email:</strong> {email}</p>
    <p style="margin: 0; color: #4a4a68;"><strong>Temporary password:</strong> {temp_password}</p>
  </div>
  <a href="{login_url}"
     style="display: inline-block; background: #2563eb; color: #ffffff; padding: 12px 24px;
            border-radius: 8px; text-decoration: none; font-weight: 600; margin: 0 0 24px 0;">
    Log In Now
  </a>
  <p style="color: #9ca3af; font-size: 13px; line-height: 1.5;">
    Please change your password after your first login.
  </p>
</div>"""

        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": f"You've been invited to {tenant_name} on Bluewave",
            "html": html,
        })
        logger.info("Invitation email sent to %s for tenant %s", email, tenant_name)
    except Exception:
        logger.exception("Failed to send invitation email to %s", email)


# ---------------------------------------------------------------------------
# Monthly report
# ---------------------------------------------------------------------------

async def send_monthly_report(
    email: str,
    full_name: str,
    tenant_name: str,
    report_pdf_path: str,
    summary: str,
) -> None:
    """Send a monthly performance report with a PDF attachment."""
    if not _resend_configured():
        return
    try:
        _init_resend()
        import resend

        html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
  <h2 style="color: #1a1a2e; margin-bottom: 16px;">Monthly Report</h2>
  <p style="color: #4a4a68; line-height: 1.6;">Hi {full_name},</p>
  <p style="color: #4a4a68; line-height: 1.6;">
    Here's the monthly performance report for <strong>{tenant_name}</strong>.
  </p>
  <div style="background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 24px 0;">
    <p style="color: #4a4a68; line-height: 1.6; margin: 0;">{summary}</p>
  </div>
  <p style="color: #9ca3af; font-size: 13px; line-height: 1.5;">
    The full report is attached as a PDF.
  </p>
</div>"""

        pdf_path = Path(report_pdf_path)
        pdf_content = pdf_path.read_bytes()

        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": f"Bluewave Monthly Report — {tenant_name}",
            "html": html,
            "attachments": [
                {
                    "filename": pdf_path.name,
                    "content": list(pdf_content),
                }
            ],
        })
        logger.info("Monthly report email sent to %s for tenant %s", email, tenant_name)
    except Exception:
        logger.exception("Failed to send monthly report email to %s", email)


# ---------------------------------------------------------------------------
# Asset workflow notification
# ---------------------------------------------------------------------------

async def send_asset_notification(
    email: str,
    event: str,
    asset_caption: str,
    actor_name: str,
    asset_id: str,
) -> None:
    """Notify a user about a workflow event (approved / rejected) on their asset."""
    if not _resend_configured():
        return
    try:
        _init_resend()
        import resend

        event_label = "approved" if "approve" in event.lower() else "rejected"
        color = "#16a34a" if event_label == "approved" else "#dc2626"
        asset_url = f"{settings.APP_URL}/assets/{asset_id}"

        html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
  <h2 style="color: #1a1a2e; margin-bottom: 16px;">Asset {event_label.capitalize()}</h2>
  <p style="color: #4a4a68; line-height: 1.6;">
    Your asset <strong>"{asset_caption or '(no caption)'}"</strong> has been
    <span style="color: {color}; font-weight: 600;">{event_label}</span>
    by {actor_name}.
  </p>
  <a href="{asset_url}"
     style="display: inline-block; background: #2563eb; color: #ffffff; padding: 12px 24px;
            border-radius: 8px; text-decoration: none; font-weight: 600; margin: 24px 0;">
    View Asset
  </a>
  <p style="color: #9ca3af; font-size: 13px; line-height: 1.5;">
    You're receiving this because you uploaded this asset on Bluewave.
  </p>
</div>"""

        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": f"Your asset was {event_label} — Bluewave",
            "html": html,
        })
        logger.info("Asset notification (%s) sent to %s for asset %s", event_label, email, asset_id)
    except Exception:
        logger.exception("Failed to send asset notification to %s for asset %s", email, asset_id)
