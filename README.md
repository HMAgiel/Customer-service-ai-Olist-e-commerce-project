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

### 2. Buat env di foler frontend dan backend
1. pada backend isinya meliputi
```bash
OPENAI_API_KEY=sk
QDRANT_API=ey
QDRANT_URL=ht

LANGFUSE_SECRET_KEY=sk
LANGFUSE_PUBLIC_KEY=pk
LANGFUSE_BASE_URL=https

TURSO_DATABASE_TOKEN=ey
TURSO_DATABASE_URL=li
```

2. pada front end isinya adalah
```bash
API_URL=http
```

### 3. Cara menjalankan docker compose
- Docper di dekstop atau terminal perlu dijalankan terlebih dahulu
- jika docker tidak bekerja berarti ada masalah pada docker anda
- berikut langkah menjalankan docker compose:
```bash
docker compose up --build
```
