"""
agents/tools.py
RAG tool (Qdrant semantic search) + SQL tool (GPT generate → SQLite execute)
"""

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

from chatbot.config import qdrant_client, engine, llm_strict, llm_sql
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from langchain_core.messages import SystemMessage, HumanMessage
from langchain.tools import tool
from qdrant_client.models import Filter, FieldCondition, MatchAny

from chatbot.prompt.rag_prompt import RAG_PROMPT, TRANSLATE_PROMPT
from chatbot.prompt.sql_prompt import SQL_PROMPT, DB_SCHEMA, SQL_EXAMPLE
from chatbot.prompt.hybrid_prompt import HYBRID_SQL_PROMPT, HYBRID_RAG_PROMPT

load_dotenv()

# ── Logging ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "olist_data_3")
EMBED_MODEL     = "text-embedding-3-small"

def llm_call(model, query, prompt):
    response = model.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=query)
    ]
)
    messages = response.content
    return messages

def _translate_output(text: str, prompt: str) -> str:
    translate = llm_call(model=llm_strict, query=text, prompt=prompt)
    return translate

# ── Tool 1: RAG — Semantic Search ─────────────────────────────────────────────
@tool
def search_products(query: str) -> str:
    """Cari produk Olist menggunakan semantic search."""
    try:
        logging.info("Run RAG clarified")
        
        clarified = llm_call(model=llm_strict, query=query, prompt=RAG_PROMPT)
        
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
            limit=20,
            with_payload=True,
        ).points
            
        if not results:
            logging.info("RAG not found result")
            return "Tidak ditemukan produk yang relevan dengan pencarian tersebut."

        # 3. Format hasil
        logging.info("RAG found result from documents")
        output_lines = [f"Found {len(results)} relevant products (filtered):\n"]
        for i, hit in enumerate(results, 1):
            p = hit.payload
            metadata = p.get("metadata", {})
            category = metadata.get("Product_category") or metadata.get("product_category", "unknown")
            review_score = metadata.get("review_score", "N/A")
            review_text = p.get("page_content", "") or p.get("text", "") or p.get("content", "")
            review_text = review_text[:200] if review_text else "Tidak ada review"

            output_lines.append(
                f"{i}. Kategori: {category}\n"
                f"   Review score: {review_score}/5\n"
                f"   Review: {review_text}\n"
            )
            
        texts = "\n".join(output_lines)
        translate_review = _translate_output(text=texts, prompt=TRANSLATE_PROMPT)
        logging.info("Successfully run RAG tools")
        return translate_review

    except Exception as e:
        logging.error(f"Error in rag: {e}")
        return f"Error saat melakukan pencarian produk: {str(e)}"


# ── Tool 2: SQL — Structured Query ────────────────────────────────────────────
@tool
def query_database(question: str) -> str:
    """Jawab pertanyaan yang membutuhkan data terstruktur dari database transaksi Olist."""
    try:
        logging.info("Run Query databse tools for SQL")
        # 1. LLM generate SQL dari pertanyaan natural language
        sql_prompt = f"SQL prompt: {SQL_PROMPT}\nDATABASE SCHEMA: {DB_SCHEMA}\nQUERY EXAMPLE: {SQL_EXAMPLE}"

        sql_response = llm_call(model=llm_sql, query=question, prompt=sql_prompt)
        sql_query = sql_response.strip()

        # Hapus markdown code block kalau LLM tetap menambahkannya
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        logging.info(f"Query Result:\n {sql_query}")

        try:
            # 2. Execute SQL ke Turso cloud
            with engine.connect() as koneksi:
                result = koneksi.execute(text(sql_query))
                rows = result.fetchall()
                
                if not rows:
                    logging.info("Query Sucessfully run but data not found")
                    return "The query ran successfully, but no data was found"
                
                # 3. Format hasil sebagai teks readable
                result_lines = [f"query result ({len(rows)} rows):\n"]
                
                for row in rows[:10]:
                    row_dict = dict(row._mapping)
                    line = " | ".join(f"{k}: {v}" for k, v in row_dict.items())
                    result_lines.append(f"  • {line}")
                    
                result_lines.append(f"\nSQL query that run: {sql_query}")
                logging.info("Query sucessfully run and data founded")
                return "\n".join(result_lines)
            
        except SQLAlchemyError as sql_error:
            logging.error(f"Error from databse found {sql_error}")
            return f"SQL error: {sql_error}\nQuery tried: {sql_query}"
        
    except Exception as e:
        logging.error(f"Error when run qeury tools: {e}")
        return f"Error when run query to database: {str(e)}"
    

# ── Tool 3: Hybrid — SQL filter + RAG search ──────────────────────────────────
@tool
def hybrid_search(question: str) -> str:
    """Jawab pertanyaan yang butuh kombinasi filter data terstruktur (SQL)"""
    try:
        logging.info("Start run Hybrid agent")
        # Step 1: SQL untuk dapat filter context
        sql_prompt = HYBRID_SQL_PROMPT.format(DB_SCHEMA=DB_SCHEMA)

        sql_response = llm_call(model=llm_sql, query=question, prompt=sql_prompt)
        sql_query = sql_response.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        logging.info(f"SQL query for hybrid agnet: {sql_query}")

        try:
            with engine.connect() as koneksi:
                result = koneksi.execute(text(sql_query))
                rows = result.fetchall()
        
        except SQLAlchemyError as sql_error:
            logging.error(f"Error sql: {sql_error}")
            print(f"Error sql: {sql_error}")
            return search_products.invoke({"query": question})
        
        categories = set()
        for row in rows:
            row_dict = dict(row._mapping)
            if "product_category_name" in row_dict and row_dict["product_category_name"]:
                categories.add(row_dict["product_category_name"])

        logging.info("Start run RAG for hybrid tools")
        
        rag_prompt = HYBRID_RAG_PROMPT.format(categories)
        clarified = llm_call(model=llm_strict, query=question, prompt=rag_prompt)
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
            
            seen_categories = set()
            unique_results = []
            for hit in results:
                metadata = hit.payload.get('metadata', {})
                category = metadata.get('Product_category') or metadata.get('product_category', '')
                if category not in seen_categories:
                    seen_categories.add(category)
                    unique_results.append(hit)
            results = unique_results
            
        else:
            # Fallback tanpa filter kalau tidak ada kategori
            results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=5,
                with_payload=True,
            ).points
            
            seen_categories = set()
            unique_results = []
            for hit in results:
                metadata = hit.payload.get('metadata', {})
                category = metadata.get('Product_category') or metadata.get('product_category', '')
                if category not in seen_categories:
                    seen_categories.add(category)
                    unique_results.append(hit)
            results = unique_results

        if not results:
            logging.info("RAG for hybrid tools finis run but no releval criteria founded")
            return "Tidak ditemukan produk yang relevan dengan kriteria tersebut."

        # Step 4: Format + translate
        output_lines = [f"Found {len(results)} relevant products (filtered):\n"]
        for i, hit in enumerate(results, 1):
            p = hit.payload
            metadata = p.get("metadata", {})
            category = metadata.get("Product_category") or metadata.get("product_category", "unknown")
            review_score = metadata.get("review_score", "N/A")
            review_text = p.get("page_content", "") or p.get("text", "") or p.get("content", "")
            review_text = review_text[:200] if review_text else "Tidak ada review"

            output_lines.append(
                f"{i}. Kategori: {category}\n"
                f"   Review score: {review_score}/5\n"
                f"   Review: {review_text}\n"
            )
            
        texts = "\n".join(output_lines)
        translate = _translate_output(text=texts, prompt=TRANSLATE_PROMPT)
        logging.info("RAG for hybird tools successfully run")
        return translate

    except Exception as e:
        logging.info(f"Hybrid tools error: {e}")
        return f"Error hybrid search: {str(e)}"