"""
agents/tools.py
RAG tool (Qdrant semantic search) + SQL tool (GPT generate → SQLite execute)
"""

import os
import sqlite3
import json
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from langchain.tools import tool
from qdrant_client.models import Filter, FieldCondition, MatchAny
from agents.prompts import SEARCH_PRODUCTS_PROMPT, QUERY_DATABASE_PROMPT, HYBRID_SEARCH_PROMPT, TRANSLATE_PROMPT, DB_SCHEMA

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60,
)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "olist_data_3")
EMBED_MODEL     = "text-embedding-3-small"
DB_PATH         = os.getenv("DB_PATH", "./data/sql/olist.db")


def _translate_output(text: str, prompt: str) -> str:
    return openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    ).choices[0].message.content

# ── Tool 1: RAG — Semantic Search ─────────────────────────────────────────────
@tool
def search_products(query: str) -> str:
    """
    Cari dan rekomendasikan produk dari database Olist berdasarkan deskripsi,
    kategori, atau review pelanggan. SELALU gunakan tool ini untuk pertanyaan
    tentang rekomendasi produk, pencarian produk, atau eksplorasi kategori.
    """
    try:
        # 1. Embed query
        embed_response = openai_client.embeddings.create(
            input=[query],
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



    except Exception as e:
        return f"Error saat melakukan pencarian produk: {str(e)}"


# ── Tool 2: SQL — Structured Query ────────────────────────────────────────────
@tool
def query_database(question: str) -> str:
    """Jawab pertanyaan yang membutuhkan data terstruktur dari database transaksi Olist."""
    try:
        # 1. LLM generate SQL dari pertanyaan natural language
        sql_prompt = f"""You are a SQL expert. Generate a valid SQLite query to answer the question below.

Database schema:
{DB_SCHEMA}

Rules:
- Use only tables and columns listed in the schema above
- Always use LIMIT 10 unless the question asks for specific count/sum/avg
- For text comparisons, use LIKE with % wildcard and LOWER() for case-insensitive
- ALWAYS use product_category_name_english instead of product_category_name for category display
- Return ONLY the raw SQL query, no explanation, no markdown, no backticks

Question: {question}
SQL:"""

        sql_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sql_prompt}],
            temperature=0,      # deterministic untuk SQL generation
        )
        sql_query = sql_response.choices[0].message.content.strip()

        # Hapus markdown code block kalau LLM tetap menambahkannya
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # 2. Execute SQL ke SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
        except sqlite3.Error as sql_err:
            conn.close()
            return f"SQL error: {sql_err}\nQuery yang dicoba: {sql_query}"
        finally:
            conn.close()

        if not rows:
            return "Query berhasil dijalankan tapi tidak ada data yang ditemukan."

        # 3. Format hasil sebagai teks readable
        col_names = [description[0] for description in cursor.description]
        result_lines = [f"Hasil query ({len(rows)} baris):\n"]

        for row in rows[:10]:        # max 10 baris ke LLM
            row_dict = dict(zip(col_names, row))
            line = " | ".join(f"{k}: {v}" for k, v in row_dict.items())
            result_lines.append(f"  • {line}")

        result_lines.append(f"\nSQL yang dijalankan: {sql_query}")
        return "\n".join(result_lines)

    except Exception as e:
        return f"Error saat query database: {str(e)}"
    

# ── Tool 3: Hybrid — SQL filter + RAG search ──────────────────────────────────
@tool
def hybrid_search(question: str) -> str:
    """Jawab pertanyaan yang butuh kombinasi filter data terstruktur (SQL)"""
    try:
        # Step 1: SQL untuk dapat filter context
        sql_prompt = f"""You are a SQL expert. Generate a SQLite query to extract filter values.

{DB_SCHEMA}

Rules:
- Return ONLY distinct values needed as filters (seller_id, product_category_name_english, seller_city)
- Use LIMIT 20
- Return ONLY raw SQL, no markdown

Question: {question}
SQL:"""

        sql_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sql_prompt}],
            temperature=0,
        )
        sql_query = sql_response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            conn.close()
            # Fallback ke RAG biasa kalau SQL gagal
            return search_products.invoke({"query": question})
        conn.close()

        # Step 2: Extract kategori dari hasil SQL untuk filter Qdrant
        categories = set()
        for row in rows:
            row_dict = dict(zip([d[0] for d in cursor.description], row))
            if "product_category_name_english" in row_dict and row_dict["product_category_name_english"]:
                categories.add(row_dict["product_category_name_english"])

        # Step 3: RAG search dengan atau tanpa metadata filter
        embed_response = openai_client.embeddings.create(
            input=[question],
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


    except Exception as e:
        return f"Error hybrid search: {str(e)}"