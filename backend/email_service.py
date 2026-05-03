"""Brevo transactional email service."""
import os
import logging
import requests

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email: str, to_name: str, subject: str, html_content: str, reply_to: str | None = None, cc_emails: list[str] | None = None) -> bool:
    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "noreply@scale.india")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "SCALE India")

    if not api_key:
        logger.warning("BREVO_API_KEY not set. Skipping email send.")
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    if cc_emails:
        payload["cc"] = [{"email": e} for e in cc_emails if e]

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    try:
        resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code >= 400:
            logger.error(f"Brevo send failed [{resp.status_code}]: {resp.text}")
            return False
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Brevo exception: {e}")
        return False


def notify_admin(subject: str, html_content: str, reply_to: str | None = None) -> bool:
    admin_email = os.environ.get("ADMIN_EMAIL", "scalesupportteam2@gmail.com")
    return send_email(admin_email, "SCALE Admin", subject, html_content, reply_to=reply_to)
