"""
streamlit_app/app.py
Olist E-commerce AI Assistant — Chat Interface
"""

import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist AI Assistant",
    page_icon="🛒",
    layout="centered",
)

# ── CSS — minimal, clean ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { max-width: 780px; }
    .stChatMessage { border-radius: 12px; }
    .tag {
        display: inline-block;
        background: #f0f2f6;
        border-radius: 16px;
        padding: 4px 12px;
        margin: 4px;
        font-size: 13px;
        cursor: pointer;
        border: 1px solid #e0e0e0;
    }
    .tag:hover { background: #e8eaf6; }
    .status-ok  { color: #2e7d32; font-size: 13px; }
    .status-err { color: #c62828; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────────────────
if "messages"   not in st.session_state:
    st.session_state.messages   = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None     # akan diisi dari response API pertama
if "api_ok"     not in st.session_state:
    st.session_state.api_ok     = None


# ── Helper: health check ───────────────────────────────────────────────────────
def check_api_health() -> bool:
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ── Helper: send message to API ────────────────────────────────────────────────
def send_message(user_input: str) -> str:
    payload = {
        "message":    user_input,
        "session_id": st.session_state.session_id,   # None = sesi baru
    }
    try:
        r = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # Simpan session_id dari response pertama
        st.session_state.session_id = data["session_id"]
        return data["answer"]
    except requests.exceptions.Timeout:
        return "⚠️ Request timeout. Agent sedang memproses — coba lagi."
    except requests.exceptions.ConnectionError:
        return "⚠️ Tidak bisa terhubung ke API. Pastikan server FastAPI berjalan."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ── Helper: clear chat ─────────────────────────────────────────────────────────
def clear_chat():
    # Hapus sesi di server
    if st.session_state.session_id:
        try:
            requests.delete(
                f"{API_URL}/session/{st.session_state.session_id}",
                timeout=5,
            )
        except Exception:
            pass
    st.session_state.messages   = []
    st.session_state.session_id = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Olist AI Assistant")
    st.markdown("Multi-agent AI untuk eksplorasi data **Olist Brazilian E-commerce**")
    st.divider()

    # API status
    if st.button("🔄 Check API Status", use_container_width=True):
        st.session_state.api_ok = check_api_health()

    if st.session_state.api_ok is True:
        st.markdown('<p class="status-ok">● API Connected</p>', unsafe_allow_html=True)
    elif st.session_state.api_ok is False:
        st.markdown('<p class="status-err">● API Disconnected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:gray;font-size:13px">● Status unknown</p>', unsafe_allow_html=True)

    st.divider()

    # New chat button
    if st.button("🗑️ New Chat", use_container_width=True):
        clear_chat()
        st.rerun()

    st.divider()

    # Info
    st.markdown("#### Tentang Dataset")
    st.markdown("""
    - 📦 ~100K orders (2016–2018)
    - 🏪 Sellers di seluruh Brasil
    - ⭐ Review & rating pelanggan
    - 💰 Data harga & pembayaran
    """)

    st.markdown("#### Kemampuan Agent")
    st.markdown("""
    - 🔍 **RAG**: pencarian semantik produk
    - 🗄️ **SQL**: analisis data terstruktur
    - 🔗 **Hybrid**: kombinasi keduanya
    """)

    st.caption(f"API: `{API_URL}`")


# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("## 🛒 Olist E-commerce AI Assistant")
st.markdown("Tanyakan apa saja tentang produk, seller, atau data transaksi Olist.")

# Suggested questions
st.markdown("**Contoh pertanyaan:**")
suggestions = [
    "Kategori produk apa yang paling banyak ordernya?",
    "Rekomendasi kategori produk peralatan dapur",
    "Seller mana yang punya revenue tertinggi?",
    "Produk apa yang reviewnya paling bagus?",
    "Berapa rata-rata harga produk elektronik?",
    "Ada produk dari seller di São Paulo?",
]

# Render suggestion pills — klik langsung jadi input
cols = st.columns(3)
for i, suggestion in enumerate(suggestions):
    with cols[i % 3]:
        if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
            st.session_state["_pending_input"] = suggestion

st.divider()

# ── Chat history display ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Handle suggestion click ────────────────────────────────────────────────────
pending = st.session_state.pop("_pending_input", None)

# ── Chat input ─────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ketik pertanyaan Anda di sini...") or pending

if user_input:
    # Tampilkan pesan user
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Kirim ke API dan tampilkan response
    with st.chat_message("assistant"):
        with st.spinner("Agent sedang memproses..."):
            answer = send_message(user_input)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})