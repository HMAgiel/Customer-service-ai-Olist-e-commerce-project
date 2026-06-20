# Olist E-commerce AI Assistant

Multi-agent RAG+SQL chatbot untuk eksplorasi data Olist Brazilian E-commerce.

## Prerequisites
- Python 3.10+
- Anaconda / virtualenv
- OpenAI API key
- Qdrant Cloud account

## Setup

### 1. Clone repo
```bash
git clone https://github.com/Purwadhika-AI-Engineering/Repo-Final-Project-Kelompok-3.git
cd Repo-Final-Project-Kelompok-3
git checkout Fajri/olist-chatbot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup environment variables
Buat file `.env` di root folder:
OPENAI_API_KEY=your_openai_api_key

QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=olist_data_3

DB_PATH=./data/sql/olist.db

### 4. Setup database
Download `olist.db` dari Google Drive (link minta ke tim), taruh di `data/sql/olist.db`

### 5. Jalanin FastAPI
```bash
uvicorn api.main:app --reload --port 8000
```

### 6. Jalanin Streamlit (terminal baru)
```bash
streamlit run streamlit_app/app.py
```

Streamlit akan buka otomatis di `http://localhost:8501`