"""Email tools exposed to the LLM.

The inbox is a simple in-memory mock (resets every time the program starts).
Each function's docstring and type hints are what AISuite turns into the tool
schema the model sees, so keep them short and precise.
"""
from datetime import datetime
import copy

from typing import Optional

MY_ADDRESS = "shinyfernando@email.com"

_INITIAL_INBOX = [
    {"id": 1, "sender": "eric@work.com", "recipient": MY_ADDRESS,
     "subject": "Days off", "body": "Can I get some days off the coming week?",
     "timestamp": "2025-06-13T09:00:00", "read": False},
    {"id": 2, "sender": "alice@work.com", "recipient": MY_ADDRESS,
     "subject": "Lunch?", "body": "Free for lunch today?",
     "timestamp": "2025-06-13T10:15:00", "read": False},
    {"id": 3, "sender": "boss@email.com", "recipient": MY_ADDRESS,
     "subject": "Quarterly Report", "body": "Please finalize the report ASAP.",
     "timestamp": "2025-06-13T11:30:00", "read": False},
    {"id": 4, "sender": "charlie@work.com", "recipient": MY_ADDRESS,
     "subject": "Meeting", "body": "Can we reschedule?",
     "timestamp": "2025-06-12T14:00:00", "read": True},
    {"id": 5, "sender": "eric@work.com", "recipient": MY_ADDRESS,
     "subject": "Happy Hour", "body": "We're planning drinks this Friday!",
     "timestamp": "2025-06-12T16:45:00", "read": False},
    {"id": 6, "sender": "bob@work.com", "recipient": MY_ADDRESS,
     "subject": "Code Review", "body": "I left some comments on your PR.",
     "timestamp": "2025-06-11T08:20:00", "read": True},
]

_inbox: list[dict] = []
_next_id = 0


def reset_inbox() -> None:
    """Restore the mock inbox to its initial state (not exposed to the LLM)."""
    global _inbox, _next_id
    _inbox = copy.deepcopy(_INITIAL_INBOX)
    _next_id = max(e["id"] for e in _inbox) + 1


reset_inbox()


def _find(email_id: int) -> Optional[dict]:
    return next((e for e in _inbox if e["id"] == email_id), None)


def _newest_first(emails: list[dict]) -> list[dict]:
    return sorted(emails, key=lambda e: e["timestamp"], reverse=True)


def list_all_emails() -> dict | list:
    """List all emails in the inbox, newest first."""
    return _newest_first(_inbox)


def list_unread_emails() -> dict | list:
    """List all unread emails in the inbox, newest first."""
    unread = [e for e in _inbox if not e["read"]]
    return _newest_first(unread) if unread else {"message": "No unread emails."}


def search_emails(query: str) -> dict | list:
    """Search emails by keyword in the subject, body, or sender address.

    Args:
        query: Keyword to search for (case-insensitive).
    """
    q = query.lower()
    results = [
        e for e in _inbox
        if q in e["subject"].lower() or q in e["body"].lower() or q in e["sender"].lower()
    ]
    return _newest_first(results) if results else {"message": f"No emails found for '{query}'."}


def filter_emails(recipient: str = "", date_from: str = "", date_to: str = "") -> dict | list:
    """Filter emails by recipient and/or a date range.

    Args:
        recipient: Recipient email address to match (optional).
        date_from: Earliest date, ISO format YYYY-MM-DD (optional).
        date_to: Latest date, ISO format YYYY-MM-DD (optional).
    """
    results = _inbox
    if recipient:
        results = [e for e in results if e["recipient"].lower() == recipient.lower()]
    if date_from:
        results = [e for e in results if e["timestamp"][:10] >= date_from]
    if date_to:
        results = [e for e in results if e["timestamp"][:10] <= date_to]
    return _newest_first(results) if results else {"message": "No emails match the filter."}


def search_unread_from_sender(sender: str) -> dict | list:
    """Return unread emails from a specific sender.

    Args:
        sender: The sender's email address.
    """
    results = [e for e in _inbox if e["sender"].lower() == sender.lower() and not e["read"]]
    return results if results else {"message": f"No unread emails from {sender}."}


def get_email(email_id: int) -> dict | list:
    """Get a specific email by its ID.

    Args:
        email_id: The integer ID of the email.
    """
    email = _find(email_id)
    return email if email else {"error": f"Email {email_id} not found."}


def mark_email_as_read(email_id: int) -> dict | list:
    """Mark an email as read.

    Args:
        email_id: The integer ID of the email to mark as read.
    """
    email = _find(email_id)
    if not email:
        return {"error": f"Email {email_id} not found."}
    email["read"] = True
    return email


def mark_email_as_unread(email_id: int) -> dict | list:
    """Mark an email as unread.

    Args:
        email_id: The integer ID of the email to mark as unread.
    """
    email = _find(email_id)
    if not email:
        return {"error": f"Email {email_id} not found."}
    email["read"] = False
    return email


def send_email(recipient: str, subject: str, body: str) -> dict | list:
    """Send a new email from the user's account.

    Args:
        recipient: Recipient email address.
        subject: Subject line of the email.
        body: Body content of the email.
    """
    global _next_id
    new_email = {
        "id": _next_id,
        "sender": MY_ADDRESS,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "read": True,
    }
    _inbox.append(new_email)
    _next_id += 1
    return new_email


def delete_email(email_id: int) -> dict | list:
    """Delete an email by its ID.

    Args:
        email_id: The integer ID of the email to delete.
    """
    email = _find(email_id)
    if not email:
        return {"error": f"Email {email_id} not found."}
    _inbox.remove(email)
    return {"message": f"Email {email_id} deleted."}


# Every tool the agent is allowed to use. Remove one to see the agent
# reason about a task it can no longer complete (e.g. delete_email).
ALL_TOOLS = [
    list_all_emails,
    list_unread_emails,
    search_emails,
    filter_emails,
    search_unread_from_sender,
    get_email,
    mark_email_as_read,
    mark_email_as_unread,
    send_email,
    delete_email,
]
