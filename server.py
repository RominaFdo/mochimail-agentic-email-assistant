"""Web UI for the email agent.

Run:  venv\\Scripts\\python server.py   then open http://127.0.0.1:8000
"""
import threading
from pathlib import Path

import truststore
from dotenv import load_dotenv

# read .env even if it was saved with a BOM.
truststore.inject_into_ssl()
load_dotenv(encoding="utf-8-sig")

import uvicorn  
from fastapi import FastAPI, HTTPException  
from fastapi.responses import FileResponse  
from fastapi.staticfiles import StaticFiles  
from pydantic import BaseModel  

import email_tools  
from agent import DEFAULT_MODEL, ask_agent  
from display_functions import extract_steps  

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Mochimail")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# The mock inbox is a module-level list, so serialiZe anything that touches it.
_lock = threading.Lock()


class AgentRequest(BaseModel):
    message: str


def _inbox_payload():
    return {
        "emails": email_tools._newest_first(email_tools._inbox),
        "me": email_tools.MY_ADDRESS,
        "model": DEFAULT_MODEL.split(":", 1)[1],
    }


def _check(result):
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(404, result["error"])
    return _inbox_payload()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/emails")
def list_emails():
    with _lock:
        return _inbox_payload()


@app.post("/api/emails/{email_id}/read")
def mark_read(email_id: int):
    with _lock:
        return _check(email_tools.mark_email_as_read(email_id))


@app.post("/api/emails/{email_id}/unread")
def mark_unread(email_id: int):
    with _lock:
        return _check(email_tools.mark_email_as_unread(email_id))


@app.delete("/api/emails/{email_id}")
def delete(email_id: int):
    with _lock:
        return _check(email_tools.delete_email(email_id))


@app.post("/api/reset")
def reset():
    with _lock:
        email_tools.reset_inbox()
        return _inbox_payload()


@app.post("/api/agent")
def run(req: AgentRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(400, "Message is empty.")
    with _lock:
        try:
            response = ask_agent(text)
        except Exception as e:  # surface API problems to the UI instead of a 500
            return {"reply": None, "steps": [], "error": str(e), **_inbox_payload()}
        return {
            "reply": response.choices[0].message.content or "",
            "steps": extract_steps(response),
            "error": None,
            **_inbox_payload(),
        }


if __name__ == "__main__":
    print("🌸 Mochimail running at http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
