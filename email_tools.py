from datetime import datetime
import json

# ── Mock in-memory inbox ──────────────────────────────────────────────────────
_inbox = [
    {
        "id": 1,
        "sender": "boss@company.com",
        "recipient": "user@example.com",
        "subject": "Happy Hour",
        "body": "We're planning drinks this Friday!",
        "timestamp": "2025-06-13T04:48:59",
        "read": True,
    },
    {
        "id": 2,
        "sender": "newsletter@tech.com",
        "recipient": "user@example.com",
        "subject": "Weekly Digest",
        "body": "Top stories this week in AI.",
        "timestamp": "2025-06-12T09:00:00",
        "read": True,
    },
    {
        "id": 3,
        "sender": "alice@example.com",
        "recipient": "user@example.com",
        "subject": "Project Update",
        "body": "Phase 1 is complete. Moving to phase 2.",
        "timestamp": "2025-06-11T14:30:00",
        "read": True,
    },
]
_next_id = 4


def list_unread_emails() -> str:
    """List all unread emails in the inbox."""
    unread = [e for e in _inbox if not e["read"]]
    return json.dumps(unread if unread else {"message": "No unread emails."})


def search_emails(query: str) -> str:
    """Search emails by keyword in subject or body.

    Args:
        query: The keyword to search for in subject or body.
    """
    results = [
        e for e in _inbox
        if query.lower() in e["subject"].lower() or query.lower() in e["body"].lower()
    ]
    return json.dumps(results if results else {"message": f"No emails found for '{query}'."})


def search_unread_from_sender(sender: str) -> str:
    """Search for unread emails from a specific sender.

    Args:
        sender: The sender's email address.
    """
    results = [e for e in _inbox if e["sender"] == sender and not e["read"]]
    return json.dumps(results if results else {"message": f"No unread emails from {sender}."})


def get_email(email_id: int) -> str:
    """Get a specific email by its ID.

    Args:
        email_id: The integer ID of the email.
    """
    email = next((e for e in _inbox if e["id"] == email_id), None)
    return json.dumps(email if email else {"error": f"Email {email_id} not found."})


def mark_email_as_read(email_id: int) -> str:
    """Mark an email as read.

    Args:
        email_id: The integer ID of the email to mark as read.
    """
    email = next((e for e in _inbox if e["id"] == email_id), None)
    if not email:
        return json.dumps({"error": f"Email {email_id} not found."})
    email["read"] = True
    return json.dumps({"success": True, "message": f"Email {email_id} marked as read."})


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email.

    Args:
        to: Recipient email address.
        subject: Subject line of the email.
        body: Body content of the email.
    """
    global _next_id
    new_email = {
        "id": _next_id,
        "sender": "user@example.com",
        "recipient": to,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat(),
        "read": True,
    }
    _inbox.append(new_email)
    _next_id += 1
    return json.dumps({"success": True, "message": f"Email sent to {to}.", "id": new_email["id"]})


def delete_email(email_id: int) -> str:
    """Delete an email by ID.

    Args:
        email_id: The integer ID of the email to delete.
    """
    global _inbox
    before = len(_inbox)
    _inbox = [e for e in _inbox if e["id"] != email_id]
    if len(_inbox) < before:
        return json.dumps({"success": True, "message": f"Email {email_id} deleted."})
    return json.dumps({"error": f"Email {email_id} not found."})


# Export all tools as a list for AISuite
ALL_TOOLS = [
    list_unread_emails,
    search_emails,
    search_unread_from_sender,
    get_email,
    mark_email_as_read,
    send_email,
    delete_email,
]