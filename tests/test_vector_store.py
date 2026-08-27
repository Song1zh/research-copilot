import argparse
import json

from core.document_loader import load_document
from core.text_splitter import split_document
from core.vector_store import ChromaVectorStore


def main():
    print(">>> test_vector_store main() started")

    parser = argparse.ArgumentParser(description="Test vector store retrieval")
    parser.add_argument("--path", type=str, required=True, help="文档路径")
    parser.add_argument("--query", type=str, required=True, help="检索问题")
    parser.add_argument("--chunk-size", type=int, default=500, help="chunk 大小")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="chunk 重叠")
    parser.add_argument("--top-k", type=int, default=3, help="返回结果数量")
    parser.add_argument("--db-path", type=str, default="./chroma_db", help="Chroma 持久化目录")
    parser.add_argument("--collection", type=str, default="demo_chunks", help="collection 名称")
    args = parser.parse_args()

    doc = load_document(args.path)
    chunks = split_document(
        doc,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    chunk_dicts = [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]

    store = ChromaVectorStore(
        db_path=args.db_path,
        collection_name=args.collection,
    )

    store.upsert_chunks(chunk_dicts)

    print("\n=== 索引信息 ===")
    print({
        "doc_path": args.path,
        "chunk_count": len(chunk_dicts),
        "collection_count": store.count(),
    })

    results = store.query(args.query, top_k=args.top_k)

    print("\n=== Query ===")
    print(args.query)

    print("\n=== Top-k Results ===")
    for i, item in enumerate(results, start=1):
        print(f"\n--- Rank {i} ---")
        print(json.dumps(
            {
                "id": item["id"],
                "distance": item["distance"],
                "metadata": item["metadata"],
                "text_preview": item["text"][:300],
            },
            ensure_ascii=False,
            indent=2,
        ))


if __name__ == "__main__":
    main()