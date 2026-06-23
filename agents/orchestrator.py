"""
agents/orchestrator.py
ReAct loop manual + Langfuse tracing via @observe (Langfuse 4.x compatible)

Security features:
- Prompt injection pattern detection
- Generic error messages (no internal detail leak)
- check_relevance guard sebelum ReAct loop
"""

import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langfuse import observe
from agents.prompts import SYSTEM_PROMPT

from agents.tools import search_products, query_database, hybrid_search

load_dotenv()

# ── LLM + Tools ───────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
)

tools          = [search_products, query_database, hybrid_search]
llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

tool_map = {
    "search_products": search_products,
    "query_database":  query_database,
    "hybrid_search":   hybrid_search,
}


# ── Prompt Injection Detector ─────────────────────────────────────────────────
# Pattern yang sering dipakai untuk prompt injection / jailbreak
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|rules?)",
    r"forget\s+(everything|all|your\s+instructions?)",
    r"you\s+are\s+now\s+(a\s+)?(?!helpful)",   # "you are now a [something else]"
    r"act\s+as\s+(if\s+you\s+are\s+)?(?!an?\s+assistant)",
    r"(reveal|show|print|display|return|give\s+me)\s+(your\s+)?(system\s+prompt|api\s+key|secret|password|token|env)",
    r"(drop|delete|truncate|alter|insert|update)\s+\w+",  # SQL DDL/DML keywords
    r"\\n\\n(human|user|assistant)\s*:",        # role injection via newlines
    r"<\s*(script|iframe|object|embed)",        # HTML injection
    r"jailbreak",
    r"DAN\s+mode",                              # "Do Anything Now" jailbreak
    r"pretend\s+(you\s+)?(have\s+no\s+restrictions?|are\s+unrestricted)",
]

_INJECTION_REGEX = re.compile(
    "|".join(_INJECTION_PATTERNS),
    flags=re.IGNORECASE,
)

def detect_injection(query: str) -> bool:
    """Return True kalau query mengandung pola prompt injection."""
    return bool(_INJECTION_REGEX.search(query))


# ── Relevance Checker ─────────────────────────────────────────────────────────
def check_relevance(query: str) -> bool:
    """Return True kalau query relevan dengan konteks Olist e-commerce."""
    guard_prompt = """You are a relevance checker for an Olist e-commerce assistant.

    Determine if this query is relevant to:
    - Olist Brazilian e-commerce data
    - Product recommendations, categories, reviews  
    - Seller information, revenue, location
    - Order statistics, payment data
    - General greetings or questions about the assistant itself
    - Greetings, small talk, or opening messages (e.g. "halo", "hi", "saya bingung mau tanya apa", "apa yang bisa kamu bantu?")

    Reply ONLY with "RELEVANT" or "IRRELEVANT"."""

    response = llm.invoke([
        SystemMessage(content=guard_prompt),
        HumanMessage(content=query),
    ])
    return "IRRELEVANT" not in response.content.upper()


# ── Session Manager ───────────────────────────────────────────────────────────
_sessions: dict[str, list] = {}
WINDOW_K = 10

def _get_history(session_id: str) -> list:
    return _sessions.setdefault(session_id, [])

def _save_turn(session_id: str, human_msg: str, ai_msg: str):
    history = _get_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))
    if len(history) > WINDOW_K:
        _sessions[session_id] = history[-WINDOW_K:]

def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


# ── Tool executor ─────────────────────────────────────────────────────────────
@observe(name="tool-execution")
def execute_tool(tool_name: str, tool_args: dict) -> str:
    print(f"[TOOL CALLED] {tool_name} | args: {tool_args}")
    tool_fn = tool_map.get(tool_name)
    if not tool_fn:
        return f"Tool '{tool_name}' tidak ditemukan."
    result = tool_fn.invoke(tool_args)
    print(f"[TOOL RESULT] {str(result)[:200]}")
    return str(result)


# ── Main run ──────────────────────────────────────────────────────────────────
@observe(name="olist-chat")
def run(query: str, session_id: str = "default") -> str:
    try:
        # ── Security Layer 1: Prompt Injection Detection ──────────────────────
        if detect_injection(query):
            print(f"[SECURITY] Prompt injection detected: {query[:100]}")
            return (
                "Maaf, permintaan ini tidak dapat diproses. "
                "Silakan ajukan pertanyaan seputar data Olist E-commerce."
            )

        # ── Security Layer 2: Relevance Guard ────────────────────────────────
        if not check_relevance(query):
            print(f"[GUARD] Irrelevant query rejected: {query[:100]}")
            return (
                "Maaf, pertanyaan ini di luar konteks dataset Olist. "
                "Saya hanya bisa membantu analisis data e-commerce Brazil seperti "
                "produk, pesanan, seller, review, dan pembayaran."
            )

        # ── ReAct Loop ────────────────────────────────────────────────────────
        history  = _get_history(session_id)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=query)]

        for _ in range(5):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                print(f"\n[FINAL ANSWER] No tool calls, returning answer directly")
                ai_reply = response.content
                _save_turn(session_id, query, ai_reply)
                return ai_reply

            # Log + execute tool calls
            print(f"\n[TOOL CALLS DETECTED] {len(response.tool_calls)} tool(s):")
            for tc in response.tool_calls:
                print(f"  → Tool: {tc['name']} | Args: {tc['args']}")
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    result = tool_fn.invoke(tc["args"])
                    print(f"  ← Result preview: {str(result)[:150]}")
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tc["id"],
                    ))

        return "Maaf, tidak bisa menyelesaikan permintaan dalam batas iterasi."

    except Exception as e:
        # Jangan leak detail error ke user — log saja di server
        print(f"[ERROR] run() exception for session {session_id}: {e}")
        return "Maaf, terjadi kesalahan saat memproses permintaan. Silakan coba lagi."