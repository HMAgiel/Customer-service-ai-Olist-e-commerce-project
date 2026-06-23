from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

turso_key = os.getenv("TURSO_DATABASE_TOKEN")
turso_url = os.getenv("TURSO_DATABASE_URL")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
)

llm_strict = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60,
)

engine = create_engine(
    f"sqlite+{turso_url}?secure=true",
    connect_args={
        "auth_token": turso_key,
    },
)

