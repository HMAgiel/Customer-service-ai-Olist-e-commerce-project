# Tambah ini di test_agent.py
from agents.tools import search_products, query_database

result = search_products.invoke({"query": "peralatan dapur kitchen cooking"})
print(result)