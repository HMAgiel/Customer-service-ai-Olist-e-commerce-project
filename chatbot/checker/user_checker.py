import re
from langchain_core.messages import HumanMessage, SystemMessage
from chatbot.prompt.guard_prompt import guard_prompt
from chatbot.config import llm

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

    response = llm.invoke([
        SystemMessage(content=guard_prompt),
        HumanMessage(content=query),
    ])
    return "IRRELEVANT" not in response.content.upper()

