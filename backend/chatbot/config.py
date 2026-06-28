from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()


turso_key = os.getenv("TURSO_DATABASE_TOKEN")
turso_url = os.getenv("TURSO_DATABASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API")


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

llm_sql = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

qdrant_client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY,
    timeout=60,
)

engine = create_engine(
    f"sqlite+{turso_url}?secure=true",
    connect_args={
        "auth_token": turso_key,
    },
)