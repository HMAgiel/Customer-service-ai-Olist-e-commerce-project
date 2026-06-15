import pandas as pd
from uuid import uuid4
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
import os
load_dotenv()

data = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_order_reviews_dataset_clean.csv")
url = os.getenv("QDRANT_URL")
qdrant_api = os.getenv("QDRANT_API")

qdrant_client = QdrantClient(
    url=url,
    api_key=qdrant_api,
)

embedding = OpenAIEmbeddings(
    model='text-embedding-3-small',
)

documents=[]
for i in range(len(data)):
    review_id = data['review_id'][i]
    order_id = data['order_id'][i]
    review_score = data['review_score'][i]
    review_title = data['review_comment_title'][i]
    review = data['review_comment_message'][i]
    if pd.isna(review):
        pass
    else:
        doc = Document(
            page_content=review,
            metadata={
                "review_id": review_id,
                "order_id": order_id,
                "review_score": int(review_score),
                "review_title": review_title
            },
        )
        documents.append(doc)
        
uuids = [str(uuid4()) for _ in range(len(documents))]

qdrant = QdrantVectorStore.from_documents(
    documents,
    embedding,
    url=url,
    api_key=qdrant_api,
    collection_name="olist_data_first_try",
    timeout=120
)

print("Qdrant sukses simpan data")