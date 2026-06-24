"""
agents/orchestrator.py
ReAct loop manual + Langfuse tracing via @observe (Langfuse 4.x compatible)

Security features:
- Prompt injection pattern detection
- Generic error messages (no internal detail leak)
- check_relevance guard sebelum ReAct loop
"""

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langfuse.decorators import observe

from chatbot.config import llm

from chatbot.prompt.prompts import SYSTEM_PROMPT

from chatbot.tools.tools import search_products, query_database, hybrid_search

from chatbot.checker.user_checker import detect_injection, check_relevance

load_dotenv()

# ── LLM + Tools ───────────────────────────────────────────────────────────────

tools          = [search_products, query_database, hybrid_search]
llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

tool_map = {
    "search_products": search_products,
    "query_database":  query_database,
    "hybrid_search":   hybrid_search,
}


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