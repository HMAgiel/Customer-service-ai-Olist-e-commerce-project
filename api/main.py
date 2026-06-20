"""
api/main.py
FastAPI wrapper — eksposes agent sebagai REST API
Endpoints: POST /chat, GET /health, DELETE /session/{session_id}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

from agents.orchestrator import run, delete_session

app = FastAPI(
    title="Olist E-commerce AI Assistant",
    description="Multi-agent AI untuk eksplorasi data Olist Brazilian E-commerce",
    version="1.0.0",
)

# CORS — supaya Streamlit bisa hit API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None   # kalau None, server generate UUID baru

class ChatResponse(BaseModel):
    answer: str
    session_id: str                 # dikembalikan ke frontend untuk dipakai di request berikutnya


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Cek apakah API jalan — dipakai Cloud Run health check."""
    return {"status": "ok", "service": "Olist AI Assistant"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    - Kalau session_id tidak dikirim, server buat UUID baru (sesi baru)
    - session_id yang sama = lanjut sesi yang sama (history preserved)
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message tidak boleh kosong")

    # Generate session_id baru kalau frontend tidak kirim
    session_id = request.session_id or str(uuid.uuid4())

    answer = run(query=request.message, session_id=session_id)

    return ChatResponse(answer=answer, session_id=session_id)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """
    Hapus history sesi tertentu dari memory.
    Dipanggil Streamlit saat user klik 'New Chat' / 'Clear History'.
    """
    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# ── Run lokal ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)