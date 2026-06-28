import pandas as pd
from uuid import uuid4
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
import logging
from dotenv import load_dotenv
import os
load_dotenv()

url = os.getenv("QDRANT_URL")
qdrant_api = os.getenv("QDRANT_API")
qdrant_client = QdrantClient(
        url=url,
        api_key=qdrant_api,
    )

embedding = OpenAIEmbeddings(
    model='text-embedding-3-small',
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log/vector_database_create.log", mode='a'),
        logging.StreamHandler()
    ]
)

def qdrant_input(collection):
    data_review = pd.read_csv('/data/final/olist_review_dataset_final.csv')
    data_order_item = pd.read_csv('/data/final/olist_order_items_dataset_final.csv')
    data_product = pd.read_csv('/data/final/olist_product_dataset_final.csv')

    gabungan = data_review.merge(data_order_item, on='order_id', how='left')
    gabungan2 = gabungan.merge(data_product, on='product_id', how='left')

    gabungan2 = gabungan2.dropna(subset=['product_category_name'])

    gabungan2 = gabungan2.drop_duplicates(subset=["review_id"]).reset_index(drop=True)

    panjang_data = len(gabungan2)
    
    docum = []
    for i in range(panjang_data):
        review_id = gabungan2['review_id'][i]
        order_id = gabungan2['order_id'][i]
        product_id = gabungan2['product_id'][i]
        review = gabungan2['review_translate'][i]
        bintang = int(gabungan2['review_score'][i])
        product = gabungan2['product_category_name_english'][i]
        
        if pd.isna(review):
          pass
      
        else:
            content = f"[product category: {product.strip()}] [review: {review.strip()}]"
        
            doc = Document(
                page_content=content,
                metadata={
                    "review_id": review_id,
                    "order_id": order_id,
                    "product_id": product_id,
                    "Product_category": product,
                    "review_score": bintang,
                },
            )
            docum.append(doc)
    logging.info("Dokumen berhasil dibuat")
            
        
    uuids = [str(uuid4()) for _ in range(len(docum))]
    logging.info("Memulai pembuatan dokumen vectore database dan memasukan ke qdrant")
    try:

        qdrant = QdrantVectorStore.from_documents(
            docum,
            embedding,
            url=url,
            api_key=qdrant_api,
            collection_name=collection,
            timeout=180
        )

        logging.info("Proses pembuatan vectore databse ke qrant telah selesai")
        
    except Exception as e:
        logging.error(f"ada error saat upload ke qdrant: {e}")
        raise e