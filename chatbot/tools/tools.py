"""
agents/tools.py
RAG tool (Qdrant semantic search) + SQL tool (GPT generate → SQLite execute)
"""

import os
import sqlite3
import json
from dotenv import load_dotenv
from openai import OpenAI

from chatbot.config import qdrant_client, engine, llm_strict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain.tools import tool
from qdrant_client.models import Filter, FieldCondition, MatchAny

from chatbot.prompt.rag_prompt import RAG_PROMPT, TRANSLATE_PROMPT
from chatbot.prompt.sql_prompt import SQL_PROMPT, DB_SCHEMA, SQL_EXAMPLE
from chatbot.prompt.hybrid_prompt import HYBRID_SQL_PROMPT, HYBRID_RAG_PROMPT

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "olist_data_3")
EMBED_MODEL     = "text-embedding-3-small"

def llm_call(query, prompt):
    response = llm_strict.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=query)
    ]
)
    messages = response.content
    return messages

def _translate_output(text: str, prompt: str) -> str:
    translate = llm_call(query=text, prompt=prompt)
    return translate

# ── Tool 1: RAG — Semantic Search ─────────────────────────────────────────────
@tool
def search_products(query: str) -> str:
    """Cari produk Olist menggunakan semantic search."""
    try:
        clarified = llm_call(query=query, prompt=RAG_PROMPT)
        print(f"[DEBUG] clarified query: {clarified}")
        
        # 1. Embed query
        embed_response = openai_client.embeddings.create(
            input=[clarified],
            model=EMBED_MODEL,
        )
        query_vector = embed_response.data[0].embedding

        # 2. Search Qdrant
        results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=5,
            with_payload=True,
        ).points

        if not results:
            return "Tidak ditemukan produk yang relevan dengan pencarian tersebut."

        # 3. Format hasil
        output_lines = [f"Ditemukan {len(results)} produk relevan:\n"]
        for i, hit in enumerate(results, 1):
            p = hit.payload
            metadata = p.get('metadata', {})
            category = metadata.get('Product_category') or metadata.get('product_category', 'unknown')
            review_score = metadata.get('review_score', 'N/A')
    
            output_lines.append(
                f"{i}. Kategori: {category}\n"
                f"   Review score: {review_score}/5\n"
                f"   Info: {p.get('page_content', '')[:300]}...\n"
            )
            
        texts = "\n".join(output_lines)
        translate_review = _translate_output(text=texts, prompt=TRANSLATE_PROMPT)
        return translate_review

    except Exception as e:
        return f"Error saat melakukan pencarian produk: {str(e)}"


# ── Tool 2: SQL — Structured Query ────────────────────────────────────────────
@tool
def query_database(question: str) -> str:
    """Jawab pertanyaan yang membutuhkan data terstruktur dari database transaksi Olist."""
    try:
        # 1. LLM generate SQL dari pertanyaan natural language
        sql_prompt = f"SQL prompt: {SQL_PROMPT}\nDATABASE SCHEMA: {DB_SCHEMA}\nQUERY EXAMPLE: {SQL_EXAMPLE}"

        sql_response = llm_call(query=question, prompt=sql_prompt)
        sql_query = sql_response.strip()

        # Hapus markdown code block kalau LLM tetap menambahkannya
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        try:
            # 2. Execute SQL ke Turso cloud
            with engine.connect() as koneksi:
                result = koneksi.execute(text(sql_query))
                rows = result.fetchall()
                
                if not rows:
                    return "The query ran successfully, but no data was found"
                
                # 3. Format hasil sebagai teks readable
                result_lines = [f"query result ({len(rows)} rows):\n"]
                
                for row in rows[:10]:
                    row_dict = dict(row._mapping)
                    line = " | ".join(f"{k}: {v}" for k, v in row_dict.items())
                    result_lines.append(f"  • {line}")
                    
                result_lines.append(f"\nSQL query that run: {sql_query}")
                return "\n".join(result_lines)
            
        except SQLAlchemyError as sql_error:
            return f"SQL error: {sql_error}\nQuery tried: {sql_query}"
        
    except Exception as e:
        return f"Error when run query to database: {str(e)}"
    

# ── Tool 3: Hybrid — SQL filter + RAG search ──────────────────────────────────
@tool
def hybrid_search(question: str) -> str:
    """Jawab pertanyaan yang butuh kombinasi filter data terstruktur (SQL)"""
    try:
        # Step 1: SQL untuk dapat filter context
        sql_prompt = HYBRID_SQL_PROMPT.format(DB_SCHEMA=DB_SCHEMA)

        sql_response = llm_call(query=question, prompt=sql_prompt)
        sql_query = sql_response.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        try:
            with engine.connect() as koneksi:
                result = koneksi.execute(text(sql_query))
                rows = result.fetchall()
        
        except SQLAlchemyError as sql_error:
            print(f"Error sql: {sql_error}")
            return search_products.invoke({"query": question})
        
        categories = set()
        for row in rows:
            row_dict = dict(row._mapping)
            if "product_category_name" in row_dict and row_dict["product_category_name"]:
                categories.add(row_dict["product_category_name"])

        clarified = llm_call(query=question, prompt=HYBRID_RAG_PROMPT)
        # Step 3: RAG search dengan atau tanpa metadata filter
        embed_response = openai_client.embeddings.create(
            input=[clarified],
            model=EMBED_MODEL,
        )
        query_vector = embed_response.data[0].embedding


        if categories:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.Product_category",
                        match=MatchAny(any=list(categories)),
                    )
                ]
            )
            results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=search_filter,
                limit=5,
                with_payload=True,
            ).points
        else:
            # Fallback tanpa filter kalau tidak ada kategori
            results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=5,
                with_payload=True,
            ).points

        if not results:
            return "Tidak ditemukan produk yang relevan dengan kriteria tersebut."

        # Step 4: Format + translate
        output_lines = [f"Found {len(results)} relevant products (filtered):\n"]
        for i, hit in enumerate(results, 1):
            p = hit.payload
            metadata = p.get("metadata", {})
            category = metadata.get("Product_category") or metadata.get("product_category", "unknown")
            review_score = metadata.get("review_score", "N/A")
            output_lines.append(
                f"{i}. Kategori: {category}\n"
                f"   Review score: {review_score}/5\n"
                f"   Info: {p.get('page_content', '')[:300]}...\n"
            )
            
        texts = "\n".join(output_lines)
        translate = _translate_output(text=texts, prompt=TRANSLATE_PROMPT)
        return translate

    except Exception as e:
        return f"Error hybrid search: {str(e)}"