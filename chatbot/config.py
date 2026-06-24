from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text
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

if __name__ == "__main__":
    print("--- Memulai Tes Koneksi Turso ---")
    print(f"URL yang digunakan: {turso_url}")
    # Jangan cetak full token demi keamanan, cetak 5 karakter pertama saja untuk verifikasi ada nilainya
    print(f"Token (5 char pertama): {turso_key[:5] if turso_key else 'Tidak Ditemukan'}...")
    
    # 3. Jalankan Query Testing (Ambil 1 data dari table customers)
    query_test = "SELECT * FROM customers LIMIT 1;"

    try:
        print("\nMencoba menghubungkan ke database dan menjalankan query...")
        with engine.connect() as conn:
            result = conn.execute(text(query_test))
            
            # Ambil nama-nama kolom
            columns = list(result.keys())
            # Ambil satu baris data pertama
            row = result.fetchone()
            
            if row:
                # Gabungkan kolom dan baris menjadi dictionary agar mudah dibaca
                data_customer = dict(zip(columns, row))
                print("\n✅ KONEKSI BERHASIL!")
                print("Hasil data customer (Limit 1):")
                print(data_customer)
            else:
                print("\n✅ KONEKSI BERHASIL! Namun tabel 'customers' kosong (tidak ada data).")

    except Exception as e:
        print("\n❌ KONEKSI GAGAL ATAU ERROR TERJADI:")
        print(str(e))
        print("\nCatatan Analisis:")
        if "502 Bad Gateway" in str(e) or "no route configured" in str(e):
            print("- Masalah ini fiks dari sisi Turso. Silakan jalankan perintah `turso db show <nama_db> --url` di terminal Anda untuk memastikan format URL-nya sudah yang paling update.")
