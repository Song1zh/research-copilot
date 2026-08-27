import chromadb
from core.config import CHROMA_DB_PATH

client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

print("=== collections ===")
for c in client.list_collections():
    try:
        collection = client.get_collection(c.name)
        print(f"{c.name} | count={collection.count()}")
    except Exception as e:
        print(f"{c.name} | error={e}")