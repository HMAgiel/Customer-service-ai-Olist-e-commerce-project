"""
agents/orchestrator.py
ReAct loop manual + Langfuse tracing via @observe (Langfuse 4.x compatible)

Security features:
- Prompt injection pattern detection
- Generic error messages (no internal detail leak)
- check_relevance guard sebelum ReAct loop
"""

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langfuse.langchain import CallbackHandler
from langfuse import observe, get_client, propagate_attributes
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from chatbot.config import llm, llm_strict

from chatbot.prompt.orchestrator_prompt import ORCHESTRATOR_PROMPT
from chatbot.prompt.guard_prompt import query_chekcer_prompt, basic_prompt
from chatbot.checker.checker_output import query_checker, basic_agent

from chatbot.tools.tools import search_products, query_database, hybrid_search

LangchainInstrumentor().instrument()
langfuse = get_client()
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

# ── Main run ──────────────────────────────────────────────────────────────────
def run(query: str, session_id: str = "default") -> str:
    try:
        with propagate_attributes(session_id=session_id):
            with langfuse.start_as_current_observation(
                name="olist-chat",
                as_type="span",
                input={"query": query, "session_id": session_id}
            ) as trace:
                history  = _get_history(session_id)
                # ── Security Layer 1: Prompt Injection Detection ──────────────────────
                prompt_checker = query_chekcer_prompt.format(history=history)
                query_check = query_checker(question=query, prompt=prompt_checker)
                
                if query_check:
                    # ── ReAct Loop ────────────────────────────────────────────────────────
                    messages = [SystemMessage(content=ORCHESTRATOR_PROMPT)] + history + [HumanMessage(content=query)]

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
                    trace.update(output="MAX_ITER", level="WARNING")
                    return "Maaf, tidak bisa menyelesaikan permintaan dalam batas iterasi."
                
                else:
                    prompt_basic_agent = basic_prompt.format(history=history)
                    basic_response = basic_agent(question=query, prompt=prompt_basic_agent)
                    _save_turn(session_id, query, basic_response)
                    return basic_response

    except Exception as e:
        # Jangan leak detail error ke user — log saja di server
        print(f"[ERROR] run() exception for session {session_id}: {e}")
        return "Maaf, terjadi kesalahan saat memproses permintaan. Silakan coba lagi."
    finally:
        langfuse.flush()