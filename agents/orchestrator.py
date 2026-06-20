"""
agents/orchestrator.py
ReAct loop manual + Langfuse tracing via @observe (Langfuse 4.x compatible)
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langfuse import observe

from agents.tools import search_products, query_database

load_dotenv()

# ── LLM + Tools ───────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
)

tools          = [search_products, query_database]
llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

tool_map = {
    "search_products": search_products,
    "query_database":  query_database,
}

SYSTEM_PROMPT = """You are a helpful AI assistant for Olist, Brazil's largest e-commerce platform.
You help users explore products, understand market trends, and analyze seller/customer data.

You have access to two tools:
1. search_products — use this for ANY question about:
   - product recommendations or suggestions
   - product categories exploration
   - finding products by type, use case, or description
   - product reviews and ratings
   - sellers in specific cities
   
2. query_database — use this for ANY question about:
   - numbers, counts, totals, averages, rankings
   - prices, revenue, order statistics
   - comparing categories or sellers by metrics
   - "berapa", "siapa yang paling", "terbanyak", "tertinggi", "terendah"

CRITICAL RULES:
- NEVER answer from general knowledge alone — ALWAYS call at least one tool
- If question involves both recommendations AND statistics, call BOTH tools
- When in doubt, call search_products first, then query_database if needed
- Always respond in the same language the user uses (Indonesian or English)
- Currency is in Brazilian Real (R$)
- If a tool returns no results, say so honestly — do not make up data
"""

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
        history  = _get_history(session_id)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=query)]

        # Loop ReAct manual — lebih reliable dari create_react_agent
        import json
        import sqlite3
        from agents.tools import search_products, query_database

        tool_map = {
            "search_products": search_products,
            "query_database":  query_database,
        }

        for _ in range(5):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                print(f"\n[FINAL ANSWER] No tool calls, returning answer directly")
                ai_reply = response.content
                _save_turn(session_id, query, ai_reply)
                return ai_reply

            # Log tool calls
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
        return f"Maaf, terjadi error: {str(e)}"