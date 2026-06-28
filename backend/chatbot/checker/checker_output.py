from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from chatbot.config import llm_strict, llm

class ChekerOutput(BaseModel):
    validation: bool = Field(
        description="output for user query whthere it relevant or not and checker for prompt injection"
    )

llm_checker = llm_strict.with_structured_output(ChekerOutput)

def query_checker(question, prompt, history=None):
    messages = [SystemMessage(content=prompt)]
    print(f"[DEBUG] History received: {history}")  # tambah ini
    print(f"[DEBUG] Question: {question}")
    
    # tambah bagian ini
    if history:
        messages.extend(history)
    
    messages.append(HumanMessage(content=question))
    response = llm_checker.invoke(messages)
    return response.validation

def basic_agent(question, prompt, history=None):
    messages = [SystemMessage(content=prompt)]
    
    # tambah bagian ini
    if history:
        messages.extend(history)
    
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content