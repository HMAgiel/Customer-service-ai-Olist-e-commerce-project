"""
api/main.py
FastAPI wrapper — eksposes agent sebagai REST API
Endpoints: POST /chat, GET /health, DELETE /session/{session_id}

Security features:
- Input length validation (max 500 chars)
- Rate limiting (20 req/min per session)
- Generic error handler (no stack trace leak)
- UUID session ID enforcement
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, field_validator
import uuid
import os
import time
import threading
from collections import defaultdict

from chatbot.agents.orchestrator import run, delete_session

app = FastAPI(
    title="Olist E-commerce AI Assistant",
    description="Multi-agent AI untuk eksplorasi data Olist Brazilian E-commerce",
    version="1.0.0",
)

frontend_url = os.getenv("FRONTEND_URL")
    
# CORS — restrict ke origin yang dikenal saja
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", 
                   "http://127.0.0.1:8501",
                   "http://frontend:8501",
                   frontend_url],  # Streamlit only
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Thread-safe in-memory rate limiter: max 20 request per menit per session
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock  = threading.Lock()   # cegah race condition di concurrent requests
RATE_LIMIT  = 20   # max requests
RATE_WINDOW = 60   # per detik (1 menit)

def check_rate_limit(session_id: str) -> bool:
    """Return True kalau masih dalam batas, False kalau sudah melewati limit."""
    now = time.time()
    window_start = now - RATE_WINDOW

    with _rate_lock:   # atomic: read + check + write tidak bisa diinterupsi thread lain
        # Buang timestamp yang sudah di luar window
        _rate_store[session_id] = [
            t for t in _rate_store[session_id] if t > window_start
        ]

        if len(_rate_store[session_id]) >= RATE_LIMIT:
            return False

        _rate_store[session_id].append(now)
        return True


# ── Request / Response schemas ────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 500

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message tidak boleh kosong")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message terlalu panjang. Maksimal {MAX_MESSAGE_LENGTH} karakter "
                f"(sekarang {len(v)} karakter)."
            )
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """Pastikan session_id yang dikirim frontend adalah UUID valid."""
        if v is None:
            return v
        try:
            uuid.UUID(str(v))
        except ValueError:
            raise ValueError("session_id harus berformat UUID yang valid.")
        return v

class ChatResponse(BaseModel):
    answer: str
    session_id: str


# ── Global Exception Handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch semua unhandled exception — jangan leak stack trace ke client.
    Error detail hanya di server log.
    """
    print(f"[ERROR] Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Terjadi kesalahan internal. Silakan coba lagi."},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Override default HTTPException agar format konsisten."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def redirect_docs():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    """Cek apakah API jalan."""
    return {"status": "ok", "service": "Olist AI Assistant"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    - Validasi panjang message (max 500 char)
    - Rate limit: 20 request/menit per session
    - Session ID harus UUID; generate baru kalau tidak dikirim
    """
    # Generate session_id baru kalau frontend tidak kirim
    session_id = request.session_id or str(uuid.uuid4())

    # Rate limiting check
    if not check_rate_limit(session_id):
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak request. Maksimal {RATE_LIMIT} pesan per menit.",
        )

    answer = run(query=request.message, session_id=session_id)

    return ChatResponse(answer=answer, session_id=session_id)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Hapus history sesi — dipanggil saat user klik 'New Chat'."""
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id tidak valid.")

    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}