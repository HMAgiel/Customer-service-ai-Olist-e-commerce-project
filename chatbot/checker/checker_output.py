from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from chatbot.config import llm_strict, llm

class ChekerOutput(BaseModel):
    validation: bool = Field(
        description="output for user query whthere it relevant or not and checker for prompt injection"
    )

llm_checker = llm_strict.with_structured_output(ChekerOutput)

def query_checker(question, prompt):
    response =  llm_checker.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=question)
        ]
    )
    return response.validation

def basic_agent(question, prompt):
    response =  llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=question)
        ]
    )
    return response.content