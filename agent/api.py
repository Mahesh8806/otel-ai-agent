"""
FastAPI backend — serves the UI and streams agent responses.

Endpoints:
  GET  /           — serve the chat UI
  POST /login      — validate username + password, return a token
  POST /chat       — send a message, get a streaming SSE response
  GET  /health     — health check

Run:
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import secrets
from pathlib import Path
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from agent.agent import build_agent

app = FastAPI(title="Revenue Manager Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UI_FILE = Path(__file__).parent.parent / "ui" / "index.html"
PORT = int(os.getenv("PORT", 8000))

# Credentials loaded from .env
VALID_USERNAME = os.getenv("LOGIN_USERNAME", "admin")
VALID_PASSWORD = os.getenv("LOGIN_PASSWORD", "hotel2026")

# Simple in-memory token store: {token: username}
# In production you'd use a real session store / JWT
active_tokens: dict[str, str] = {}

security = HTTPBearer()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Check that the request carries a valid token."""
    token = credentials.credentials
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token. Please log in.")
    return active_tokens[token]  # returns the username


# ── Serve UI ──────────────────────────────────────────────────────────────────

@app.get("/")
def serve_ui():
    """Serve the chat UI at http://localhost:8000"""
    return FileResponse(UI_FILE)


# ── Auth endpoints ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(req: LoginRequest):
    """
    Validate username + password.
    Returns a token the UI stores in sessionStorage and sends with every request.
    """
    if req.username != VALID_USERNAME or req.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    token = secrets.token_hex(32)  # random secure token
    active_tokens[token] = req.username
    return {"token": token, "username": req.username}


@app.post("/logout")
def logout(username: str = Depends(verify_token), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Remove the token so the user is logged out."""
    token = credentials.credentials
    active_tokens.pop(token, None)
    return {"message": "Logged out"}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Agent ─────────────────────────────────────────────────────────────────────

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.post("/chat")
async def chat(req: ChatRequest, username: str = Depends(verify_token)):
    """
    Streams the agent's response as Server-Sent Events (SSE).
    Requires a valid Bearer token from /login.
    """
    agent = get_agent()

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": req.message}]},
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    data = {
                        "type": "tool_start",
                        "tool": event.get("name", ""),
                        "input": event.get("data", {}).get("input", {}),
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                elif kind == "on_tool_end":
                    output = event.get("data", {}).get("output", "")
                    data = {
                        "type": "tool_end",
                        "tool": event.get("name", ""),
                        "output": str(output)[:2000],
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        data = {"type": "token", "content": chunk.content}
                        yield f"data: {json.dumps(data)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
