import httpx
from email.utils import getaddresses, parseaddr
from typing import Optional
import os
from .email_breaker import email_breaker as breaker
# Configuration
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _extract_recipients(message, fallback_name: Optional[str]) -> list[dict]:

    to_list = []
    for display_name, email in getaddresses(message.get_all("To", [])):
        if not email:
            continue
        to_list.append({
            "email": email,
            "name": fallback_name or display_name or "User",
        })
    return to_list


def _extract_sender(message) -> dict:

    sender_name, sender_email = parseaddr(message.get("From", ""))
    return {
        "name":  sender_name or "Sender",
        "email": sender_email or "",
    }


def _extract_body(message) -> tuple[Optional[str], Optional[str]]:

    html_content: Optional[str] = None
    text_content: Optional[str] = None

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            decoded = payload.decode(errors="ignore")

            if content_type == "text/html" and html_content is None:
                html_content = decoded
            elif content_type == "text/plain" and text_content is None:
                text_content = decoded
    else:
        payload = message.get_payload(decode=True)
        if payload:
            decoded = payload.decode(errors="ignore")
            if message.get_content_type() == "text/html":
                html_content = decoded
            else:
                text_content = decoded

    return html_content, text_content


def sync_brevo_send(message, name: Optional[str] = None):

    if not BREVO_API_KEY:
        raise ValueError("BREVO_API_KEY is not configured")

    def brevo_operation():
        headers = {
            "api-key":      BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }

        to_list = _extract_recipients(message, name)
        if not to_list:
            raise ValueError("No valid recipients found in the To header")

        sender = _extract_sender(message)
        if not sender["email"]:
            raise ValueError("No valid sender email found in the From header")

        
        html_content, text_content = _extract_body(message)

        if not html_content and not text_content:
            raise ValueError(
                "Email has no text/html or text/plain body content")

        payload: dict = {
            "sender":  sender,
            "to":      to_list,
            "subject": message.get("Subject") or "No Subject",
        }
        if html_content:
            payload["htmlContent"] = html_content
        if text_content:
            payload["textContent"] = text_content

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(
                    BREVO_URL, json=payload, headers=headers)
        except httpx.TimeoutException:
            print("[Brevo] Timeout – request took longer than 15 s")
            raise
        except httpx.RequestError as exc:
            print(f"[Brevo] Network error: {exc}")
            raise

        if 200 <= response.status_code < 300:
            return response.json()

        if 400 <= response.status_code < 500:

            print(
                f"[Brevo] Client error {response.status_code}: {response.text}")
            return None

        print(f"[Brevo] Server error {response.status_code}: {response.text}")
        response.raise_for_status()

    return breaker.sync_call(brevo_operation)


if __name__ == "__main__":
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["From"] = "Alice <alice@example.com>"
    msg["To"] = "Bob <bob@example.com>"
    msg["Subject"] = "Hello from Brevo"
    msg.set_content("This is a plain-text test email.")
    msg.add_alternative(
        "<h1>Hello!</h1><p>This is an HTML test.</p>", subtype="html")

    try:
        result = sync_brevo_send(msg, name="Bob")
        print("Sent:", result)
    except Exception as e:
        print("Failed:", e)
